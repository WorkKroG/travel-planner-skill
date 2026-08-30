import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from travel_planner.checks import run_checks
from travel_planner.cli import main
from travel_planner.state import TripState, write_state_file


@pytest.fixture
def state(japan_state: TripState) -> TripState:
    state = deepcopy(japan_state)
    state.itinerary.update(
        {
            "document_status": "draft",
            "finalization_basis": None,
            "accepted_blockers": [],
            "challenge_findings": [],
            "selected_route_id": None,
            "days": [],
            "budget_items": [],
            "budget_summary": None,
        }
    )
    state.readiness["items"] = []
    state.candidates["items"] = []
    return state


@pytest.mark.parametrize(
    "item",
    [
        {"id": "negative", "amount_type": "exact", "amount": -1, "currency": "USD", "basis": "per_group"},
        {"id": "boolean", "amount_type": "exact", "amount": True, "currency": "USD", "basis": "per_group"},
        {"id": "no-currency", "amount_type": "exact", "amount": 10, "basis": "per_group"},
        {"id": "no-basis", "amount_type": "exact", "amount": 10, "currency": "USD"},
        {"id": "unknown-with-value", "amount_type": "unknown", "amount": 10, "currency": "USD", "basis": "per_group"},
    ],
)
def test_incoherent_budget_item_is_a_structural_cli_error(
    minimal_trip: Path, capsys, item: dict[str, object]
) -> None:
    itinerary_path = minimal_trip / "itinerary.yaml"
    itinerary = yaml.safe_load(itinerary_path.read_text(encoding="utf-8"))
    itinerary["budget_items"] = [item]
    write_state_file(itinerary_path, itinerary)

    exit_code = main(["check", str(minimal_trip)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["structural_errors"][0]["path"].startswith(
        "itinerary.yaml.budget_items[0]"
    )


@pytest.mark.parametrize(
    "item",
    [
        {"id": "nan", "amount_type": "exact", "amount": float("nan"), "currency": "USD", "basis": "per_group"},
        {"id": "reversed", "amount_type": "range", "amount_min": 20, "amount_max": 10, "currency": "USD", "basis": "per_group"},
    ],
)
def test_nonfinite_or_reversed_budget_item_is_a_hard_finding(
    state: TripState, item: dict[str, object]
) -> None:
    state.itinerary["budget_items"] = [item]

    report = run_checks(state)

    assert [finding.code for finding in report.findings] == ["BUDGET_ITEM_INVALID"]


def test_per_person_item_requires_positive_known_traveler_count(state: TripState) -> None:
    state.brief["travelers"] = []
    state.itinerary["budget_items"] = [
        {"id": "rail-person", "amount_type": "exact", "amount": 100, "currency": "USD", "basis": "per_person"}
    ]

    missing = run_checks(state)
    state.brief["travelers"] = [{"id": "traveler-one"}, {"id": "traveler-two"}]
    known = run_checks(state)

    assert "BUDGET_TRAVELER_COUNT_REQUIRED" in [finding.code for finding in missing.findings]
    assert "BUDGET_TRAVELER_COUNT_REQUIRED" not in [finding.code for finding in known.findings]


@pytest.mark.parametrize("rate", [float("nan"), 0, -1, True])
def test_mixed_currencies_require_finite_positive_dated_fx(
    state: TripState, rate: object
) -> None:
    state.itinerary["budget_items"] = [
        {"id": "hotel", "amount_type": "exact", "amount": 10000, "currency": "JPY", "basis": "per_group"},
        {"id": "ticket", "amount_type": "exact", "amount": 50, "currency": "USD", "basis": "per_group"},
    ]
    state.itinerary["budget_summary"] = {
        "currency": "JPY",
        "basis": "per_group",
        "amount": 17500,
        "fx": {
            "base_currency": "JPY",
            "observed_at": "2026-08-30T09:00:00+00:00",
            "source_id": state.candidates["sources"][0]["id"],
            "rates": {"USD": rate},
        },
    }

    report = run_checks(state)

    assert "BUDGET_FX_REQUIRED" in [finding.code for finding in report.findings]


def test_budget_summary_range_matches_only_known_summable_items(state: TripState) -> None:
    state.itinerary["budget_items"] = [
        {"id": "rail", "amount_type": "exact", "amount": 100, "currency": "USD", "basis": "per_group"},
        {"id": "hotel", "amount_type": "range", "amount_min": 50, "amount_max": 70, "currency": "USD", "basis": "per_group"},
    ]
    state.itinerary["budget_summary"] = {
        "currency": "USD",
        "basis": "per_group",
        "amount_min": 140,
        "amount_max": 170,
    }

    mismatch = run_checks(state)
    state.itinerary["budget_summary"]["amount_min"] = 150
    consistent = run_checks(state)

    assert "BUDGET_TOTAL_MISMATCH" in [finding.code for finding in mismatch.findings]
    assert "BUDGET_TOTAL_MISMATCH" not in [finding.code for finding in consistent.findings]


def test_numeric_summary_is_blocked_while_any_budget_amount_is_unknown(
    state: TripState,
) -> None:
    state.itinerary["budget_items"] = [
        {"id": "known", "amount_type": "exact", "amount": 100, "currency": "USD", "basis": "per_group"},
        {"id": "unknown", "amount_type": "unknown", "currency": "USD", "basis": "per_group"},
    ]
    state.itinerary["budget_summary"] = {"currency": "USD", "basis": "per_group", "amount": 100}

    report = run_checks(state)

    unknown = next(finding for finding in report.findings if finding.code == "BUDGET_AMOUNT_UNKNOWN")
    assert unknown.severity == "note"
    assert unknown.affected_ids == ("unknown",)
    incomplete = next(
        finding
        for finding in report.findings
        if finding.code == "BUDGET_TOTAL_WITH_UNKNOWN"
    )
    assert incomplete.severity == "blocking"
    assert report.ok is False


def test_cli_returns_3_for_numeric_summary_with_unknown_amount(
    minimal_trip: Path, capsys
) -> None:
    itinerary_path = minimal_trip / "itinerary.yaml"
    itinerary = yaml.safe_load(itinerary_path.read_text(encoding="utf-8"))
    itinerary.update(
        {
            "document_status": "final",
            "verification_level": "codex_validated",
            "finalization_basis": "codex_validated",
            "budget_items": [
                {
                    "id": "known",
                    "amount_type": "exact",
                    "amount": 100,
                    "currency": "USD",
                    "basis": "per_group",
                },
                {
                    "id": "unknown",
                    "amount_type": "unknown",
                    "currency": "USD",
                    "basis": "per_group",
                },
            ],
            "budget_summary": {
                "currency": "USD",
                "basis": "per_group",
                "amount": 100,
            },
        }
    )
    write_state_file(itinerary_path, itinerary)

    exit_code = main(["check", str(minimal_trip)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 3
    assert "BUDGET_TOTAL_WITH_UNKNOWN" in {
        finding["code"] for finding in payload["unaccepted_blocking_findings"]
    }


@pytest.mark.parametrize(
    ("case", "fx"),
    [
        (
            "missing-source",
            {
                "base_currency": "USD",
                "observed_at": "2026-08-30T09:00:00+00:00",
                "source_id": "missing-source",
                "rates": {"EUR": 0.9},
            },
        ),
        (
            "wrong-base",
            {
                "base_currency": "EUR",
                "observed_at": "2026-08-30T09:00:00+00:00",
                "source_id": "source-rail",
                "rates": {"USD": 1.1},
            },
        ),
        (
            "nan-extra-rate",
            {
                "base_currency": "USD",
                "observed_at": "2026-08-30T09:00:00+00:00",
                "source_id": "source-rail",
                "rates": {"EUR": float("nan")},
            },
        ),
        (
            "infinite-extra-rate",
            {
                "base_currency": "USD",
                "observed_at": "2026-08-30T09:00:00+00:00",
                "source_id": "source-rail",
                "rates": {"EUR": float("inf")},
            },
        ),
        (
            "negative-extra-rate",
            {
                "base_currency": "USD",
                "observed_at": "2026-08-30T09:00:00+00:00",
                "source_id": "source-rail",
                "rates": {"EUR": -1},
            },
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_optional_single_currency_fx_is_fully_validated(
    state: TripState, case: str, fx: dict[str, object]
) -> None:
    state.itinerary["budget_items"] = [
        {
            "id": "known",
            "amount_type": "exact",
            "amount": 100,
            "currency": "USD",
            "basis": "per_group",
        }
    ]
    state.itinerary["budget_summary"] = {
        "currency": "USD",
        "basis": "per_group",
        "amount": 100,
        "fx": fx,
    }

    report = run_checks(state)

    assert "BUDGET_FX_INVALID" in [finding.code for finding in report.findings], case


def test_valid_optional_single_currency_fx_has_no_false_positive(
    state: TripState,
) -> None:
    state.itinerary["budget_items"] = [
        {
            "id": "known",
            "amount_type": "exact",
            "amount": 100,
            "currency": "USD",
            "basis": "per_group",
        }
    ]
    state.itinerary["budget_summary"] = {
        "currency": "USD",
        "basis": "per_group",
        "amount": 100,
        "fx": {
            "base_currency": "USD",
            "observed_at": "2026-08-30T09:00:00+00:00",
            "source_id": "source-rail",
            "rates": {"EUR": 0.9},
        },
    }

    assert "BUDGET_FX_INVALID" not in [
        finding.code for finding in run_checks(state).findings
    ]


def test_readiness_dependency_graph_rejects_cycles(state: TripState) -> None:
    state.readiness["items"] = [
        {"id": "ready-a", "category": "transport", "status": "action_needed", "dependencies": ["ready-b"]},
        {"id": "ready-b", "category": "lodging", "status": "action_needed", "dependencies": ["ready-c"]},
        {"id": "ready-c", "category": "activities", "status": "action_needed", "dependencies": ["ready-a"]},
    ]

    cycle = next(
        finding for finding in run_checks(state).findings if finding.code == "READINESS_CYCLE"
    )
    assert cycle.affected_ids == ("ready-a", "ready-b", "ready-c", "ready-a")


def test_duplicate_source_order_never_changes_official_source_result(state: TripState) -> None:
    official = {
        "id": "source-entry",
        "url": "https://official.example/entry",
        "source_type": "official",
        "publisher": "Border agency",
        "retrieved_at": "2026-08-20T12:00:00+00:00",
    }
    editorial = {**official, "url": "https://example.com/entry", "source_type": "editorial"}
    state.candidates["claims"] = [
        {"id": "claim-entry", "topic": "entry", "status": "verified", "source_ids": ["source-entry"]}
    ]

    state.candidates["sources"] = [official, editorial]
    first = run_checks(state)
    state.candidates["sources"] = [editorial, official]
    second = run_checks(state)

    for report in (first, second):
        assert "ID_DUPLICATE" in [finding.code for finding in report.findings]
        assert "SOURCE_OFFICIAL_REQUIRED" in [finding.code for finding in report.findings]


def test_candidate_local_claim_finding_keeps_its_canonical_path(state: TripState) -> None:
    state.candidates["sources"] = [
        {"id": "editorial-health", "url": "https://example.com/health", "source_type": "editorial", "publisher": "Travel Blog", "retrieved_at": "2026-08-20T12:00:00+00:00"}
    ]
    state.candidates["claims"] = []
    state.candidates["items"] = [
        {"id": "candidate-clinic", "claims": [{"id": "claim-health", "topic": "health", "status": "verified", "source_ids": ["editorial-health"]}]}
    ]

    finding = next(
        finding for finding in run_checks(state).findings if finding.code == "SOURCE_OFFICIAL_REQUIRED"
    )
    assert finding.path == "candidates.yaml.items[0].claims[0]"

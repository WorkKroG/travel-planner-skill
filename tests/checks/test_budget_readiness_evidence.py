from copy import deepcopy

import pytest
from travel_planner.checks import run_checks
from travel_planner.state import TripState


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
        }
    )
    state.readiness["items"] = []
    state.candidates["items"] = []
    return state


def test_mixed_currencies_require_explicit_dated_fx_metadata(state: TripState) -> None:
    state.itinerary["budget_items"] = [
        {
            "id": "hotel-jpy",
            "amount_type": "exact",
            "amount": 10000,
            "currency": "JPY",
            "basis": "per_group",
        },
        {
            "id": "ticket-usd",
            "amount_type": "exact",
            "amount": 50,
            "currency": "USD",
            "basis": "per_group",
        },
    ]

    blocked = run_checks(state)
    state.itinerary["budget_fx"] = {
        "base_currency": "JPY",
        "observed_at": "2026-08-30T09:00:00+00:00",
        "source_id": state.candidates["sources"][0]["id"],
        "rates": {"USD": 150.0},
    }
    explicit = run_checks(state)

    assert [finding.code for finding in blocked.findings] == ["BUDGET_FX_REQUIRED"]
    assert "BUDGET_FX_REQUIRED" not in [finding.code for finding in explicit.findings]


def test_mixed_price_bases_require_an_explicit_traveler_count(state: TripState) -> None:
    state.brief["travelers"] = []
    state.itinerary["budget_items"] = [
        {
            "id": "rail-person",
            "amount_type": "exact",
            "amount": 100,
            "currency": "USD",
            "basis": "per_person",
        },
        {
            "id": "hotel-group",
            "amount_type": "exact",
            "amount": 300,
            "currency": "USD",
            "basis": "per_group",
        },
    ]

    missing = run_checks(state)
    state.brief["travelers"] = [{"id": "traveler-1"}, {"id": "traveler-2"}]
    explicit = run_checks(state)

    assert [finding.code for finding in missing.findings] == ["BUDGET_BASIS_REQUIRED"]
    assert "BUDGET_BASIS_REQUIRED" not in [finding.code for finding in explicit.findings]


def test_declared_budget_range_must_match_known_summable_items(state: TripState) -> None:
    state.itinerary["budget_items"] = [
        {
            "id": "rail",
            "amount_type": "exact",
            "amount": 100,
            "currency": "USD",
            "basis": "per_group",
        },
        {
            "id": "hotel",
            "amount_type": "range",
            "amount_min": 50,
            "amount_max": 70,
            "currency": "USD",
            "basis": "per_group",
        },
    ]
    state.itinerary["budget_total"] = {
        "currency": "USD",
        "basis": "per_group",
        "amount_min": 140,
        "amount_max": 170,
    }

    mismatch = run_checks(state)
    state.itinerary["budget_total"]["amount_min"] = 150
    consistent = run_checks(state)

    assert [finding.code for finding in mismatch.findings] == ["BUDGET_TOTAL_MISMATCH"]
    assert "BUDGET_TOTAL_MISMATCH" not in [finding.code for finding in consistent.findings]


def test_unknown_amount_stays_visible_and_is_not_added_as_zero(state: TripState) -> None:
    state.itinerary["budget_items"] = [
        {
            "id": "known-hotel",
            "amount_type": "exact",
            "amount": 100,
            "currency": "USD",
            "basis": "per_group",
        },
        {
            "id": "unknown-rail",
            "amount_type": "unknown",
            "currency": "USD",
            "basis": "per_group",
        },
    ]
    state.itinerary["budget_total"] = {
        "currency": "USD",
        "basis": "per_group",
        "amount": 100,
    }

    report = run_checks(state)

    unknown = next(finding for finding in report.findings if finding.code == "BUDGET_AMOUNT_UNKNOWN")
    assert unknown.severity == "note"
    assert unknown.affected_ids == ("unknown-rail",)
    assert "BUDGET_TOTAL_MISMATCH" not in [finding.code for finding in report.findings]


def test_readiness_dependency_graph_rejects_cycles(state: TripState) -> None:
    state.readiness["items"] = [
        {"id": "ready-a", "category": "transport", "status": "action_needed", "dependencies": ["ready-b"]},
        {"id": "ready-b", "category": "lodging", "status": "action_needed", "dependencies": ["ready-c"]},
        {"id": "ready-c", "category": "activities", "status": "action_needed", "dependencies": ["ready-a"]},
    ]

    report = run_checks(state)

    cycle = next(finding for finding in report.findings if finding.code == "READINESS_CYCLE")
    assert cycle.affected_ids == ("ready-a", "ready-b", "ready-c", "ready-a")


def test_verified_high_stakes_claim_requires_existing_official_source(
    state: TripState,
) -> None:
    state.candidates["sources"] = [
        {
            "id": "editorial-visa",
            "url": "https://example.com/visa",
            "source_type": "editorial",
            "publisher": "Travel Blog",
            "retrieved_at": "2026-08-20T12:00:00+00:00",
        }
    ]
    state.candidates["claims"] = [
        {
            "id": "claim-entry",
            "topic": "entry",
            "status": "verified",
            "source_ids": ["editorial-visa"],
        },
        {
            "id": "claim-health-unknown",
            "topic": "health",
            "status": "unverified",
            "source_ids": [],
        },
    ]

    report = run_checks(state)

    assert [finding.code for finding in report.findings] == [
        "SOURCE_OFFICIAL_REQUIRED"
    ]
    assert report.findings[0].affected_ids == ("claim-entry",)


def test_candidate_local_claim_finding_keeps_its_canonical_path(state: TripState) -> None:
    state.candidates["sources"] = [
        {
            "id": "editorial-health",
            "url": "https://example.com/health",
            "source_type": "editorial",
            "publisher": "Travel Blog",
            "retrieved_at": "2026-08-20T12:00:00+00:00",
        }
    ]
    state.candidates["claims"] = []
    state.candidates["items"] = [
        {
            "id": "candidate-clinic",
            "claims": [
                {
                    "id": "claim-health",
                    "topic": "health",
                    "status": "verified",
                    "source_ids": ["editorial-health"],
                }
            ],
        }
    ]

    finding = run_checks(state).findings[0]

    assert finding.code == "SOURCE_OFFICIAL_REQUIRED"
    assert finding.path == "candidates.yaml.items[0].claims[0]"

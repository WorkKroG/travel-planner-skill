"""Exercise the current CLI and HTML with incomplete but valid recorded data."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from travel_planner.checks import run_checks
from travel_planner.cli import main
from travel_planner.render.html import DEFAULTS, render_html
from travel_planner.render.viewmodel import build_view
from travel_planner.state import load_trip, write_state_file

AT = "2026-09-05T12:00:00+00:00"


def _save(state):
    for name in ("brief", "candidates", "itinerary", "readiness"):
        write_state_file(state.root / f"{name}.yaml", getattr(state, name))


def _render(root, output):
    return main(["render", str(root), "--output", str(output), "--at", AT])


def _note(identifier="note-timetable"):
    return {
        "id": identifier,
        "code": "RECORDED",
        "severity": "blocking",
        "status": "unresolved",
        "path": "itinerary.yaml",
        "affected_ids": [],
        "message": "Timetable remains unpublished <check later>.",
    }


@pytest.mark.parametrize("basis", ["codex_validated", "user_confirmed"])
def test_prepared_copy_keeps_unknowns_without_requiring_risk_acceptance(
    minimal_trip: Path, tmp_path: Path, capsys, basis: str
) -> None:
    state = load_trip(minimal_trip)
    state.itinerary.update(
        document_status="final",
        finalization_basis=basis,
        verification_level="codex_validated" if basis == "codex_validated" else "ai_reviewed",
        challenge_findings=[_note()],
        accepted_blockers=[],
        open_decisions=[
            {"id": "choose-route", "question": "Which return?", "next_action": "Check publication."}
        ],
    )
    state.readiness["items"] = [
        {
            "id": "ready-return",
            "title": "Return train",
            "category": "transport",
            "status": "not_released_yet",
            "due_at": "2026-08-01T10:30:00+00:00",
            "next_action": "Read the operator's publication before choosing the return.",
        }
    ]
    _save(state)
    before = {p.name: p.read_bytes() for p in minimal_trip.iterdir() if p.is_file()}

    assert main(["check", str(minimal_trip)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["scope"] == "recorded_data_integrity"
    assert report["saved_findings"][0]["id"] == "note-timetable"
    output = tmp_path / "prepared.html"
    assert _render(minimal_trip, output) == 0
    html = output.read_text()
    assert "Prepared copy" in html
    assert "Timetable remains unpublished &lt;check later&gt;." in html
    assert "Which return?" in html
    preparation = html[html.index('id="preparation"') : html.index('id="budget"')]
    assert "Due: 2026-08-01T10:30:00+00:00" in preparation
    assert "Read the operator" in preparation
    assert "not released yet" in preparation
    assert "Final — проверено" not in html
    assert before == {p.name: p.read_bytes() for p in minimal_trip.iterdir() if p.is_file()}


def test_recorded_expenses_render_exact_separate_subtotals_and_partial_values(
    minimal_trip: Path, tmp_path: Path, capsys
) -> None:
    state = load_trip(minimal_trip)
    state.brief["travelers"] = []
    state.itinerary["budget_summary"] = {"currency": "USD", "basis": "per_group", "amount": 99999}
    state.itinerary["budget_items"] = [
        {
            "id": "small-one",
            "amount_type": "exact",
            "amount": 0.1,
            "currency": "USD",
            "basis": "per_group",
        },
        {
            "id": "small-two",
            "amount_type": "exact",
            "amount": 0.2,
            "currency": "USD",
            "basis": "per_group",
        },
        {
            "id": "person",
            "amount_type": "exact",
            "amount": 19.95,
            "currency": "USD",
            "basis": "per_person",
        },
        {
            "id": "euro",
            "amount_type": "range",
            "amount_min": 101.2,
            "amount_max": 109.35,
            "currency": "EUR",
            "basis": "per_group",
        },
        {"id": "missing-basis", "amount_type": "exact", "amount": 73.45, "currency": "USD"},
        {
            "id": "partial-range",
            "amount_type": "range",
            "amount_min": 81.23,
            "currency": "USD",
            "basis": "per_group",
        },
        {
            "id": "unknown",
            "amount_type": "unknown",
            "amount": 999.77,
            "currency": "USD",
            "basis": "per_group",
        },
        {
            "id": "missing-currency",
            "amount_type": "estimate",
            "amount": 42.61,
            "basis": "per_group",
        },
    ]
    _save(state)
    before = deepcopy(state)
    assert main(["check", str(minimal_trip)]) == 0
    capsys.readouterr()
    with localcontext() as context:
        context.prec = 2
        view = build_view(state, run_checks(state), datetime.fromisoformat(AT))
    assert [(s.currency, s.basis, s.minimum, s.maximum) for s in view.budget.subtotals] == [
        ("EUR", "per_group", Decimal("101.2"), Decimal("109.35")),
        ("USD", "per_group", Decimal("0.3"), Decimal("0.3")),
        ("USD", "per_person", Decimal("19.95"), Decimal("19.95")),
    ]
    output = tmp_path / "expenses.html"
    assert _render(minimal_trip, output) == 0
    html = output.read_text()
    assert "0.3 USD" in html and "19.95 USD" in html
    assert "101.2 EUR" in html and "109.35 EUR" in html
    assert "73.45 USD" in html and "81.23 USD" in html and "42.61 Unknown" in html
    assert "Missing basis" in html and "Missing amount_max" in html and "Missing currency" in html
    assert "999.77" not in html and "99,999" not in html
    assert "confidence" not in html[html.index('id="budget"') : html.index('id="risks"')].lower()
    assert state == before


@pytest.mark.parametrize(
    "item",
    [
        {"amount_type": "exact"},
        {"amount_type": "range", "amount_max": 20.5},
        {"amount_type": "exact", "amount": None, "currency": None, "basis": None},
    ],
)
def test_missing_expense_information_is_allowed_in_a_draft(minimal_trip, capsys, item):
    state = load_trip(minimal_trip)
    state.itinerary["budget_items"] = [{"id": "incomplete", **item}]
    _save(state)
    assert main(["check", str(minimal_trip)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


@pytest.mark.parametrize("value", [-1, True, float("nan"), float("inf")])
def test_invalid_recorded_money_stops_render_without_replacing_output(
    minimal_trip, tmp_path, value
):
    state = load_trip(minimal_trip)
    state.itinerary["budget_items"] = [
        {
            "id": "bad",
            "amount_type": "exact",
            "amount": value,
            "currency": "USD",
            "basis": "per_group",
        }
    ]
    _save(state)
    output = tmp_path / "existing.html"
    output.write_text("Existing copy")
    assert _render(minimal_trip, output) in (2, 3)
    assert output.read_text() == "Existing copy"


@pytest.mark.parametrize(
    "case", ["day", "single-cutoff", "reverse-trip", "reverse-event", "owner", "budget-source"]
)
def test_invalid_recorded_dates_and_explicit_references_are_rejected(minimal_trip, tmp_path, case):
    state = load_trip(minimal_trip)
    state.itinerary["days"] = [{"id": "day-one", "timeline": []}]
    if case == "day":
        state.itinerary["days"][0]["date"] = "2026-02-30"
    elif case == "single-cutoff":
        state.itinerary["days"][0]["timeline"] = [
            {
                "id": "event",
                "time": "Unknown",
                "title": "Visit",
                "detail": "",
                "last_admission_at": "bad-date",
            }
        ]
    elif case == "reverse-trip":
        state.brief["travel_dates"] = {"start": "2026-11-03", "end": "2026-11-02"}
    elif case == "reverse-event":
        state.itinerary["days"][0]["timeline"] = [
            {
                "id": "event",
                "time": "10:00",
                "title": "Visit",
                "detail": "",
                "start_at": "2026-11-03T10:00:00+09:00",
                "end_at": "2026-11-03T09:00:00+09:00",
            }
        ]
    elif case == "owner":
        state.readiness["items"] = [
            {
                "id": "ready-one",
                "category": "transport",
                "status": "unknown",
                "owner_id": "missing-person",
            }
        ]
    else:
        state.itinerary["budget_items"] = [
            {
                "id": "cost",
                "amount_type": "unknown",
                "currency": "USD",
                "basis": "per_group",
                "source_ids": ["missing-source"],
            }
        ]
    _save(state)
    assert main(["check", str(minimal_trip)]) in (2, 3)
    output = tmp_path / "bad.html"
    assert _render(minimal_trip, output) in (2, 3)
    assert not output.exists()


def test_unknown_times_and_route_questions_are_not_computed_feasibility_findings(
    minimal_trip, capsys
):
    state = load_trip(minimal_trip)
    state.itinerary["days"] = [
        {
            "id": "day-one",
            "timeline": [
                {
                    "id": "first",
                    "title": "Visit",
                    "detail": "Check the admission time.",
                    "start_at": "2026-11-03T10:00:00+09:00",
                    "last_admission_at": "2026-11-03T09:00:00+09:00",
                    "required_buffer_markers": ["security"],
                    "buffer_markers": [],
                },
            ],
        }
    ]
    state.candidates["claims"] = [
        {"id": "claim-known", "topic": "entry", "status": "verified", "source_ids": []}
    ]
    _save(state)
    assert main(["check", str(minimal_trip)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["findings"] == []
    assert state.candidates["claims"][0]["status"] == "verified"


def test_recorded_acceptance_remains_visible_but_cannot_waive_a_data_error(minimal_trip):
    state = load_trip(minimal_trip)
    state.itinerary.update(
        document_status="final",
        verification_level="ai_reviewed",
        finalization_basis="user_confirmed",
        challenge_findings=[_note()],
        accepted_blockers=[
            {
                "blocker_id": "note-timetable",
                "accepted_by_user": True,
                "accepted_at": AT,
                "rationale": "Keep the conditional plan and check publication before booking.",
            }
        ],
    )
    report = run_checks(state)
    html = render_html(build_view(state, report, datetime.now(UTC)), {}, DEFAULTS)
    assert "Keep the conditional plan" in html
    assert report.ok
    state.itinerary["selected_route_id"] = "absent-route"
    assert not run_checks(state).ok

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from travel_planner.checks import CheckReport, Finding, run_checks
from travel_planner.render.viewmodel import build_view
from travel_planner.state import TripState, load_trip

GENERATED_AT = datetime(2026, 8, 28, 12, tzinfo=UTC)


def test_view_places_blockers_before_day_details(
    japan_state: TripState, japan_report: CheckReport
) -> None:
    """Catch a renderer that buries feasibility blockers inside later day content."""
    view = build_view(japan_state, japan_report, GENERATED_AT)

    assert view.unaccepted_blockers[0].severity == "blocking"
    assert view.unaccepted_blockers[0].code == "BOOK-001"
    assert view.days[0].day_id == "day-1"
    assert view.open_decisions[0].severity == "blocking"


def test_view_orders_days_by_number_independent_of_yaml_sequence(
    japan_state: TripState, japan_report: CheckReport
) -> None:
    """Keep all render adapters chronological when canonical day records are reordered."""
    reordered = deepcopy(japan_state)
    reordered.itinerary["days"] = list(reversed(reordered.itinerary["days"]))
    expected = sorted((day["number"], day["id"]) for day in japan_state.itinerary["days"])

    view = build_view(reordered, japan_report, GENERATED_AT)

    assert [(day.number, day.day_id) for day in view.days] == expected


def test_view_does_not_mutate_canonical_state(
    japan_state: TripState, japan_report: CheckReport
) -> None:
    """Catch a derived view writing defaults or presentation state back into YAML data."""
    before = deepcopy(japan_state)

    view = build_view(japan_state, japan_report, GENERATED_AT)

    assert japan_state == before
    with pytest.raises(FrozenInstanceError):
        view.title = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("verification_level", "status_label", "verification_label"),
    [
        ("none", "Draft — unchecked", "Recorded data not checked"),
        (
            "ai_reviewed",
            "Draft — AI-review",
            "AI-review — probabilistic review",
        ),
    ],
)
def test_draft_lifecycle_is_copied_without_looking_final(
    japan_state: TripState,
    japan_report: CheckReport,
    verification_level: str,
    status_label: str,
    verification_label: str,
) -> None:
    """Catch Draft or AI review being upgraded through renderer-era status logic."""
    state = deepcopy(japan_state)
    state.itinerary["verification_level"] = verification_level

    view = build_view(state, japan_report, GENERATED_AT)

    assert view.document_status == "draft"
    assert view.verification_level == verification_level
    assert view.finalization_basis is None
    assert view.status_label == status_label
    assert view.verification_label == verification_label
    assert view.lifecycle_safe is True


def test_codex_validated_final_uses_exact_product_label() -> None:
    """Catch a valid Codex Final being relabelled by a renderer-specific QA receipt."""
    fixture = Path(__file__).parents[1] / "fixtures" / "japan-final-reference"
    state = load_trip(fixture)

    view = build_view(state, run_checks(state), GENERATED_AT)

    assert view.document_status == "final"
    assert view.verification_level == "codex_validated"
    assert view.finalization_basis == "codex_validated"
    assert view.status_label == "Prepared copy — checked in Codex"
    assert view.lifecycle_safe is True


def test_user_confirmed_final_keeps_accepted_blocker_blocking_and_visible(
    japan_state: TripState,
) -> None:
    """Catch acceptance being presented as resolution or losing its audit context."""
    state = deepcopy(japan_state)
    blocker = Finding(
        id="blocker-rail",
        code="SCHEDULE_UNRELEASED",
        severity="blocking",
        path="itinerary.yaml.days[1]",
        affected_ids=("day-2",),
        message="The final timetable is not released.",
    )
    state.itinerary.update(
        document_status="final",
        verification_level="ai_reviewed",
        finalization_basis="user_confirmed",
        accepted_blockers=[
            {
                "blocker_id": "blocker-rail",
                "accepted_by_user": True,
                "accepted_at": "2026-08-30T09:00:00+00:00",
                "rationale": "The user accepts the remaining timetable uncertainty.",
            }
        ],
    )
    report = CheckReport((), (), (), ("blocker-rail",), (blocker,))

    view = build_view(state, report, GENERATED_AT)

    assert view.status_label == "Prepared copy — requested by user"
    assert view.lifecycle_safe is True
    assert view.unaccepted_blockers == ()
    assert len(view.accepted_blockers) == 1
    accepted = view.accepted_blockers[0]
    assert accepted.severity == "blocking"
    assert accepted.resolution_status == "unresolved"
    assert accepted.acceptance_label == "Accepted by user — remains blocking"
    assert accepted.accepted_at == "2026-08-30T09:00:00+00:00"
    assert accepted.rationale == "The user accepts the remaining timetable uncertainty."


def test_view_uses_check_report_as_the_lifecycle_classification_boundary(
    japan_state: TripState,
) -> None:
    """Catch the renderer reimplementing acceptance rules already decided by checks."""
    state = deepcopy(japan_state)
    blocker = Finding(
        "blocker-rail",
        "SCHEDULE_UNRELEASED",
        "blocking",
        "itinerary.yaml.days[1]",
        ("day-2",),
        "The final timetable is not released.",
    )
    state.itinerary.update(
        document_status="final",
        verification_level="ai_reviewed",
        finalization_basis="user_confirmed",
        accepted_blockers=[],
    )

    view = build_view(
        state,
        CheckReport((), (), (), (blocker.id,), (blocker,)),
        GENERATED_AT,
    )

    assert view.lifecycle_safe is True
    assert view.status_label == "Prepared copy — requested by user"
    assert [item.id for item in view.accepted_blockers] == [blocker.id]
    assert view.accepted_blockers[0].acceptance_label == "Accepted by user — remains blocking"
    assert view.unaccepted_blockers == ()


def test_unaccepted_and_accepted_blockers_are_normalized_separately(
    japan_state: TripState,
) -> None:
    """Catch a renderer combining accepted risk with blockers that still prevent finalization."""
    state = deepcopy(japan_state)
    accepted = Finding(
        "accepted-one",
        "ACCEPTED",
        "blocking",
        "itinerary.yaml.days[0]",
        ("day-1",),
        "Accepted blocker.",
    )
    unaccepted = Finding(
        "open-one",
        "OPEN",
        "blocking",
        "itinerary.yaml.days[1]",
        ("day-2",),
        "Unaccepted blocker.",
    )
    state.itinerary["accepted_blockers"] = [
        {
            "blocker_id": "accepted-one",
            "accepted_by_user": True,
            "accepted_at": "2026-08-30T09:00:00+00:00",
            "rationale": "Accepted explicitly.",
        }
    ]
    report = CheckReport((), (), (), ("accepted-one",), (accepted, unaccepted))

    view = build_view(state, report, GENERATED_AT)

    assert [item.id for item in view.accepted_blockers] == ["accepted-one"]
    assert [item.id for item in view.unaccepted_blockers] == ["open-one"]


def test_invalid_data_is_never_presented_as_a_consistent_prepared_copy(
    japan_state: TripState,
) -> None:
    """Catch a contradictory Final/report combination retaining success styling and copy."""
    state = deepcopy(japan_state)
    state.itinerary.update(
        document_status="final",
        verification_level="codex_validated",
        finalization_basis="codex_validated",
    )
    blocker = Finding(
        "blocker-rail",
        "LINK_ROUTE_NOT_FOUND",
        "blocking",
        "itinerary.yaml.days[1]",
        ("day-2",),
        "Recorded route reference does not resolve.",
    )
    view = build_view(state, CheckReport((), (blocker,), (), ()), GENERATED_AT)

    assert view.document_status == "final"
    assert view.declared_final_label == "Prepared copy — checked in Codex"
    assert view.status_label == "Prepared copy — inconsistent state"
    assert view.lifecycle_safe is False
    assert "cannot be treated as a consistent prepared copy" in view.lifecycle_warning


def test_source_and_readiness_uncertainty_remain_explicit(
    japan_state: TripState, japan_report: CheckReport
) -> None:
    """Catch stale, conflicting, and unreleased facts being flattened into neutral copy."""
    view = build_view(japan_state, japan_report, GENERATED_AT)

    assert view.readiness[0].status == "recheck"
    assert view.sources[0].claim_status == "conflicting"
    assert view.sources[0].freshness_status == "stale"
    assert view.days[1].timeline[1].time == "Unknown"


def test_budget_does_not_invent_a_cross_currency_total(
    japan_state: TripState,
) -> None:
    """Catch presentation arithmetic adding unrelated currency units into one fake range."""
    state = deepcopy(japan_state)
    state.itinerary["budget_items"] = [
        {
            "id": "rail-jpy",
            "category": "transport",
            "amount_type": "exact",
            "amount": 10000,
            "currency": "JPY",
            "basis": "per_group",
            "confidence": "high",
        },
        {
            "id": "hotel-usd",
            "category": "lodging",
            "amount_type": "exact",
            "amount": 100,
            "currency": "USD",
            "basis": "per_group",
            "confidence": "high",
        },
    ]

    view = build_view(state, CheckReport((), (), (), ()), GENERATED_AT)

    assert [(item.currency, item.basis, item.minimum) for item in view.budget.subtotals] == [
        ("JPY", "per_group", Decimal(10000)),
        ("USD", "per_group", Decimal(100)),
    ]
    assert [(item.minimum, item.currency) for item in view.budget.categories] == [
        (Decimal(100), "USD"),
        (Decimal(10000), "JPY"),
    ]
    assert {item.basis for item in view.budget.categories} == {"per_group"}


def test_budget_ignores_a_saved_overall_summary_without_changing_it(japan_state: TripState) -> None:
    state = deepcopy(japan_state)
    recorded = {"currency": "JPY", "basis": "per_group", "amount_min": 250000, "amount_max": 330000}
    state.itinerary["budget_summary"] = recorded
    state.itinerary["budget_items"] = [
        {
            "id": "one-row",
            "amount_type": "exact",
            "amount": 7.25,
            "currency": "USD",
            "basis": "per_person",
        }
    ]
    view = build_view(state, CheckReport((), (), (), ()), GENERATED_AT)
    assert len(view.budget.subtotals) == 1
    assert view.budget.subtotals[0].minimum == Decimal("7.25")
    assert view.budget.subtotals[0].currency == "USD"
    assert state.itinerary["budget_summary"] == recorded


def test_view_projects_event_owned_context_and_complete_scenario_timeline(
    japan_state: TripState,
) -> None:
    """Catch the renderer flattening readable-day events back into prose side rails."""
    state = deepcopy(japan_state)
    state.itinerary["days"][0]["timeline"] = [
        {
            "id": "event-transfer",
            "kind": "transport",
            "time": "09:00",
            "title": "Train",
            "detail": "Travel to the next district.",
            "links": [
                {
                    "label": "Build route",
                    "url": "https://maps.example/route",
                    "kind": "route",
                    "requires_internet": True,
                }
            ],
            "alternatives": [
                {
                    "id": "event-transfer-bus",
                    "title": "Bus",
                    "reason": "Use when the train is disrupted.",
                    "detail": "Direct local bus.",
                    "price": "Approx. JPY 500",
                    "effort": "low",
                    "distance": "8 km",
                    "booking": "No reservation",
                    "links": [
                        {
                            "label": "Open on map",
                            "url": "https://maps.example/bus",
                            "kind": "map",
                            "requires_internet": True,
                        }
                    ],
                }
            ],
        },
        {
            "id": "event-check",
            "kind": "checkpoint",
            "time": "14:00",
            "title": "Weather check",
            "detail": "Decide at the station.",
            "checkpoint": {
                "check": "Confirm the rain warning.",
                "adjust_plan": "Use the indoor scenario.",
            },
        },
    ]
    state.itinerary["days"][0]["scenarios"] = [
        {
            "id": "rain",
            "label": "Rain",
            "summary": "Replace the outdoor half of the day.",
            "timeline": [
                {
                    "id": "event-rain-museum",
                    "kind": "activity",
                    "time": "15:00",
                    "title": "Museum",
                    "detail": "Stay indoors.",
                }
            ],
        }
    ]
    before = deepcopy(state)

    view = build_view(state, CheckReport((), (), (), ()), GENERATED_AT)

    transfer, checkpoint = view.days[0].timeline
    assert transfer.event_id == "event-transfer"
    assert transfer.kind == "transport"
    assert transfer.links[0].kind == "route"
    assert transfer.alternatives[0].reason == "Use when the train is disrupted."
    assert transfer.alternatives[0].price == "Approx. JPY 500"
    assert transfer.alternatives[0].links[0].url == "https://maps.example/bus"
    assert checkpoint.checkpoint.check == "Confirm the rain warning."
    assert checkpoint.checkpoint.adjust_plan == "Use the indoor scenario."
    scenario = view.days[0].scenarios[0]
    assert (scenario.scenario_id, scenario.label) == ("rain", "Rain")
    assert scenario.timeline[0].title == "Museum"
    assert state == before


def test_russian_document_language_localizes_renderer_owned_copy(
    japan_state: TripState,
) -> None:
    """Catch Russian itinerary content being surrounded by English system labels."""
    state = deepcopy(japan_state)
    state.brief["document_language"] = "ru"
    state.itinerary["verification_level"] = "ai_reviewed"
    state.itinerary["days"][0]["overnight"] = None
    state.itinerary["budget_items"][0]["amount_type"] = "unknown"

    view = build_view(state, CheckReport((), (), (), ()), GENERATED_AT)

    assert view.language == "ru"
    assert view.status_label == "Черновик — AI-проверка"
    assert view.verification_label == "AI-проверка — вероятностный разбор"
    assert view.days[0].weekday == "понедельник"
    assert view.days[0].date_label == "2 ноября 2026"
    assert view.days[0].overnight == "Неизвестно"
    assert view.budget.categories[0].exclusion_reason == "Сумма неизвестна"

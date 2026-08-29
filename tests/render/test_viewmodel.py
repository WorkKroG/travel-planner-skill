from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from travel_planner.challenge import ChallengeReport
from travel_planner.impact import semantic_hash
from travel_planner.render.viewmodel import build_view
from travel_planner.state import TripState

GENERATED_AT = datetime(2026, 8, 28, 12, tzinfo=UTC)


def test_view_places_blockers_before_day_details(
    japan_state: TripState, japan_report: ChallengeReport
) -> None:
    """Catch a renderer that buries feasibility blockers inside later day content."""
    view = build_view(japan_state, japan_report, GENERATED_AT)

    assert view.summary.blockers[0].severity == "blocking"
    assert view.summary.blockers[0].rule_id == "BOOK-001"
    assert view.days[0].day_id == "day-1"
    assert view.open_decisions[0].severity == "blocking"


def test_view_orders_days_by_number_independent_of_yaml_sequence(
    japan_state: TripState, japan_report: ChallengeReport
) -> None:
    """Keep all render adapters chronological when canonical day records are reordered."""
    reordered = deepcopy(japan_state)
    reordered.itinerary["days"] = list(reversed(reordered.itinerary["days"]))
    expected = sorted(
        (day["number"], day["id"]) for day in japan_state.itinerary["days"]
    )

    view = build_view(reordered, japan_report, GENERATED_AT)

    assert [(day.number, day.day_id) for day in view.days] == expected


def test_view_does_not_mutate_canonical_state(
    japan_state: TripState, japan_report: ChallengeReport
) -> None:
    """Catch a derived view writing defaults or presentation state back into YAML data."""
    before = semantic_hash(japan_state)

    view = build_view(japan_state, japan_report, GENERATED_AT)

    assert semantic_hash(japan_state) == before
    with pytest.raises(FrozenInstanceError):
        view.title = "Changed"  # type: ignore[misc]


def test_final_requires_explicit_final_state_and_no_blockers(
    japan_state: TripState, japan_report: ChallengeReport
) -> None:
    """Catch a frozen route being presented as Final before blockers and QA are cleared."""
    final_state = deepcopy(japan_state)
    final_state.itinerary["output_status"] = "final"
    final_state.itinerary["route_state"] = "frozen"

    blocked_view = build_view(final_state, japan_report, GENERATED_AT)
    clear_report = ChallengeReport("detailed", GENERATED_AT, (), ())
    final_view = build_view(final_state, clear_report, GENERATED_AT, qa_attested=True)

    assert blocked_view.status == "draft"
    assert final_view.status == "final"


def test_source_and_readiness_uncertainty_remain_explicit(
    japan_state: TripState, japan_report: ChallengeReport
) -> None:
    """Catch stale, conflicting, and unreleased facts being flattened into neutral copy."""
    view = build_view(japan_state, japan_report, GENERATED_AT)

    assert view.readiness[0].status == "recheck"
    assert view.sources[0].claim_status == "conflicting"
    assert view.sources[0].freshness_status == "stale"
    assert view.days[1].timeline[0].time == "Unknown"

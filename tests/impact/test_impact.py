from copy import deepcopy
from pathlib import Path

from travel_planner.impact import ImpactTarget, analyze_change, semantic_hash
from travel_planner.state import TripState, load_trip


def _trip_with_days(root: Path) -> TripState:
    state = load_trip(root)
    state.itinerary["days"] = [
        {
            "id": "day-4",
            "date": "2026-11-05",
            "meals": [{"id": "dinner-4", "name": "Old restaurant"}],
        },
        {
            "id": "day-5",
            "date": "2026-11-06",
            "activities": [{"id": "museum-5", "name": "Museum"}],
        },
    ]
    return state


def test_restaurant_change_does_not_touch_unrelated_days(minimal_trip: Path) -> None:
    before = _trip_with_days(minimal_trip)
    after = deepcopy(before)
    after.itinerary["days"][0]["meals"][0]["name"] = "New restaurant"

    report = analyze_change(before, after)

    assert report.targets == (
        ImpactTarget("day", "day-4"),
        ImpactTarget("outputs", "all"),
    )
    assert "day-5" not in report.changed_ids


def test_declared_bookkeeping_timestamps_do_not_change_semantic_hash(
    minimal_trip: Path,
) -> None:
    before = _trip_with_days(minimal_trip)
    after = deepcopy(before)
    after.brief["updated_at"] = "2026-08-29T12:00:00+00:00"

    assert semantic_hash(before) == semantic_hash(after)


def test_changed_readiness_item_selects_checklist_and_outputs(minimal_trip: Path) -> None:
    before = _trip_with_days(minimal_trip)
    before.readiness["items"] = [{"id": "visa-check", "status": "open"}]
    after = deepcopy(before)
    after.readiness["items"][0]["status"] = "done"

    report = analyze_change(before, after)

    assert report.targets == (
        ImpactTarget("readiness", "visa-check"),
        ImpactTarget("outputs", "all"),
    )

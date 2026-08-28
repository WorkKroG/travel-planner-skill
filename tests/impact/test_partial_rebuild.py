from copy import deepcopy
from pathlib import Path

from travel_planner.impact import analyze_change, select_rebuild_targets, semantic_hash
from travel_planner.state import load_trip


def test_partial_rebuild_preserves_unrelated_day_and_becomes_idempotent(
    minimal_trip: Path,
) -> None:
    before = load_trip(minimal_trip)
    before.itinerary["days"] = [
        {"id": "day-4", "meals": [{"id": "dinner-4", "name": "Old"}]},
        {"id": "day-5", "activities": [{"id": "walk-5", "name": "Canal walk"}]},
    ]
    after = deepcopy(before)
    day_five_before = semantic_hash(before.itinerary["days"][1])
    after.itinerary["days"][0]["meals"][0]["name"] = "New"

    report = analyze_change(before, after)

    assert select_rebuild_targets(report) == report.targets
    assert semantic_hash(after.itinerary["days"][1]) == day_five_before
    assert analyze_change(after, deepcopy(after)).targets == ()

import shutil
from datetime import UTC, datetime
from pathlib import Path

from travel_planner.challenge.base import ChallengeContext
from travel_planner.challenge.calendar import (
    OvernightRolloverRule,
    WeekdayRule,
    local_dt,
)
from travel_planner.state import load_trip


def _context(tmp_path: Path, facts: dict) -> ChallengeContext:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return ChallengeContext(
        state=load_trip(target),
        stage="detailed",
        now=datetime(2026, 8, 28, 12, tzinfo=UTC),
        facts=facts,
    )


def test_local_dt_applies_destination_timezone_to_naive_value() -> None:
    """Catch a local opening time being interpreted in the machine timezone."""
    result = local_dt("2026-11-06T16:30:00", "Asia/Tokyo")

    assert result.isoformat() == "2026-11-06T16:30:00+09:00"


def test_weekday_mismatch_is_blocking(tmp_path: Path) -> None:
    """Catch an activity scheduled on a different weekday than its fixed opening."""
    ctx = _context(
        tmp_path,
        {
            "dated_events": [
                {
                    "id": "event-1",
                    "starts_at": "2026-11-06T10:00:00+09:00",
                    "expected_weekday": "Thursday",
                    "timezone": "Asia/Tokyo",
                }
            ]
        },
    )

    finding = WeekdayRule().evaluate(ctx)[0]

    assert finding.rule_id == "CAL-001"
    assert finding.severity == "blocking"


def test_overnight_leg_updates_local_date(tmp_path: Path) -> None:
    """Catch a night segment assigned to the departure date after local rollover."""
    ctx = _context(
        tmp_path,
        {
            "overnight_legs": [
                {
                    "id": "leg-night",
                    "departure": "2026-11-06T23:30:00+09:00",
                    "arrival": "2026-11-07T06:00:00+09:00",
                    "arrival_timezone": "Asia/Tokyo",
                    "day_id": "day-5",
                    "night_id": "night-5",
                }
            ]
        },
    )

    finding = OvernightRolloverRule().evaluate(ctx)[0]

    assert finding.rule_id == "CAL-004"
    assert finding.affected_ids == ("day-5", "night-5")


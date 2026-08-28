import shutil
from datetime import UTC, datetime
from pathlib import Path

from travel_planner.challenge.base import ChallengeContext
from travel_planner.challenge.load import CumulativeLoadRule, DailyLoadRule
from travel_planner.state import load_trip


def _context(tmp_path: Path, facts: dict) -> ChallengeContext:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return ChallengeContext(
        load_trip(target), "detailed", datetime(2026, 8, 28, 12, tzinfo=UTC), facts
    )


def test_day_above_group_walking_limit_is_blocking(tmp_path: Path) -> None:
    """Catch a day whose walking demand exceeds a participant hard limit."""
    ctx = _context(
        tmp_path,
        {
            "daily_loads": [
                {"id": "day-4", "walking_km": 14, "group_max_walking_km": 8}
            ]
        },
    )

    assert DailyLoadRule().evaluate(ctx)[0].rule_id == "LOAD-001"


def test_consecutive_high_load_days_require_recovery(tmp_path: Path) -> None:
    """Catch tolerable individual days that become excessive when accumulated."""
    ctx = _context(
        tmp_path,
        {
            "daily_loads": [
                {"id": "day-3", "load_score": 8},
                {"id": "day-4", "load_score": 9},
                {"id": "day-5", "load_score": 8},
            ],
            "max_consecutive_high_load_days": 2,
            "high_load_threshold": 8,
        },
    )

    finding = CumulativeLoadRule().evaluate(ctx)[0]

    assert finding.rule_id == "LOAD-002"
    assert finding.affected_ids == ("day-3", "day-4", "day-5")

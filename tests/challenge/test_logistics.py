import shutil
from datetime import UTC, datetime
from pathlib import Path

from travel_planner.challenge.base import ChallengeContext
from travel_planner.challenge.logistics import (
    DoorToDoorRule,
    LastAdmissionRule,
    MinimumConnectionRule,
    ScheduleHorizonRule,
)
from travel_planner.state import load_trip


def _context(tmp_path: Path, facts: dict | None = None) -> ChallengeContext:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return ChallengeContext(
        state=load_trip(target),
        stage="detailed",
        now=datetime(2026, 8, 28, 12, tzinfo=UTC),
        facts=facts or {},
    )


def test_last_admission_is_not_closing_time(tmp_path: Path) -> None:
    """Catch arrival before closing but after the final admission cutoff."""
    ctx = _context(tmp_path)
    ctx.arrival = "2026-11-06T16:45:00+09:00"
    ctx.venue = {
        "id": "museum-1",
        "timezone": "Asia/Tokyo",
        "closes_at": "18:00",
        "last_admission": "16:30",
    }

    finding = LastAdmissionRule().evaluate(ctx)[0]

    assert finding.rule_id == "OPS-002"
    assert finding.severity == "blocking"


def test_door_to_door_uses_every_required_component(tmp_path: Path) -> None:
    """Catch a feasible-looking transfer that counts only vehicle time."""
    ctx = _context(
        tmp_path,
        {
            "legs": [
                {
                    "id": "leg-1",
                    "allocated_minutes": 120,
                    "components": {
                        "walk": 15,
                        "check_out": 15,
                        "station_buffer": 20,
                        "ride": 70,
                        "transfer": 20,
                    },
                }
            ]
        },
    )

    finding = DoorToDoorRule().evaluate(ctx)[0]

    assert finding.rule_id == "LEG-001"
    assert finding.severity == "blocking"
    assert "140" in finding.message


def test_short_connection_is_blocking(tmp_path: Path) -> None:
    """Catch an itinerary whose connection is below the fixture minimum."""
    ctx = _context(
        tmp_path,
        {
            "connections": [
                {"id": "connection-1", "available_minutes": 18, "minimum_minutes": 25}
            ]
        },
    )

    assert MinimumConnectionRule().evaluate(ctx)[0].rule_id == "LEG-002"


def test_unreleased_schedule_stays_unknown_and_gets_recheck(tmp_path: Path) -> None:
    """Catch a far-future schedule being fabricated to make a leg look complete."""
    ctx = _context(
        tmp_path,
        {
            "schedules": [
                {
                    "id": "future-ferry",
                    "status": "not_released_yet",
                    "next_check_at": "2026-09-15T09:00:00+09:00",
                }
            ]
        },
    )

    finding = ScheduleHorizonRule().evaluate(ctx)[0]

    assert finding.rule_id == "OPS-001"
    assert finding.severity == "warning"
    assert finding.proposed_patch["next_check_at"] == "2026-09-15T09:00:00+09:00"
    assert "departure_time" not in finding.proposed_patch

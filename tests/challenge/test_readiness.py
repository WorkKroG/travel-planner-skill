import shutil
from datetime import UTC, datetime
from pathlib import Path

from travel_planner.challenge.base import ChallengeContext
from travel_planner.challenge.readiness import (
    AccessibilityChainRule,
    BookingWindowRule,
    DependencyCycleRule,
)
from travel_planner.state import load_trip


def _context(tmp_path: Path, facts: dict) -> ChallengeContext:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return ChallengeContext(
        load_trip(target), "detailed", datetime(2026, 8, 28, 12, tzinfo=UTC), facts
    )


def test_expired_booking_window_is_blocking(tmp_path: Path) -> None:
    """Catch an unresolved booking whose local deadline has already passed."""
    ctx = _context(
        tmp_path,
        {
            "booking_items": [
                {
                    "id": "booking-1",
                    "status": "action_needed",
                    "due_at": "2026-08-27T18:00:00+09:00",
                }
            ]
        },
    )

    finding = BookingWindowRule().evaluate(ctx)[0]

    assert finding.rule_id == "BOOK-001"
    assert finding.severity == "blocking"


def test_booking_dependency_cycle_is_blocking(tmp_path: Path) -> None:
    """Catch readiness actions that can never become actionable due to a cycle."""
    ctx = _context(
        tmp_path,
        {
            "booking_items": [
                {"id": "booking-a", "dependencies": ["booking-b"]},
                {"id": "booking-b", "dependencies": ["booking-a"]},
            ]
        },
    )

    assert DependencyCycleRule().evaluate(ctx)[0].rule_id == "BOOK-002"


def test_unknown_wheelchair_transfer_creates_readiness_action(tmp_path: Path) -> None:
    """Catch a chain marked accessible when one transfer remains unknown."""
    ctx = _context(
        tmp_path,
        {
            "accessibility_chains": [
                {
                    "id": "chain-day-3",
                    "traveler_id": "traveler-1",
                    "requires_wheelchair": True,
                    "segments": [
                        {"id": "hotel-exit", "status": "accessible"},
                        {"id": "station-transfer", "status": "unknown"},
                    ],
                }
            ]
        },
    )

    finding = AccessibilityChainRule().evaluate(ctx)[0]

    assert finding.rule_id == "ACC-001"
    assert finding.proposed_patch["status"] == "action_needed"
    assert finding.affected_ids == ("chain-day-3", "station-transfer")


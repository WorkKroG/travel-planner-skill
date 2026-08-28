from datetime import UTC, datetime, timedelta

from travel_planner.evidence import Finding
from travel_planner.readiness import next_recheck, sync_evidence_findings

TRIP_START = datetime(2026, 11, 2, 9, tzinfo=UTC)


def test_unreleased_item_is_rechecked_before_departure() -> None:
    """Catch an unreleased booking window with no future review date."""
    result = next_recheck({"status": "not_released_yet"}, TRIP_START)

    assert result == TRIP_START - timedelta(days=30)


def test_confirmed_item_needs_no_automatic_recheck() -> None:
    """Catch confirmed user work being reopened without a stated reason."""
    assert next_recheck({"status": "confirmed"}, TRIP_START) is None


def test_evidence_sync_preserves_owner_decisions() -> None:
    """Catch evidence automation overwriting a user's owner or waived status."""
    readiness = {
        "items": [
            {
                "id": "evidence-claim-visa",
                "category": "entry",
                "status": "waived",
                "owner_id": "traveler-1",
            }
        ]
    }
    finding = Finding(
        rule_id="EVID-001",
        severity="blocking",
        confidence="high",
        affected_ids=("claim-visa",),
        evidence_ids=(),
        message="Official source required",
    )

    updated = sync_evidence_findings(readiness, (finding,))

    assert updated["items"][0]["status"] == "waived"
    assert updated["items"][0]["owner_id"] == "traveler-1"

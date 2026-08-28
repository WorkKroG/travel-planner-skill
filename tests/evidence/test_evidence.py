from datetime import UTC, datetime

from travel_planner.evidence import (
    assess_claim,
    critical_evidence_findings,
    render_sources_markdown,
)
from travel_planner.state import TripState

NOW = datetime(2026, 8, 28, 12, tzinfo=UTC)


def test_entry_claim_without_official_source_creates_blocker(state: TripState) -> None:
    """Catch high-stakes entry guidance presented without direct official evidence."""
    state.candidates["sources"] = [
        {
            "id": "blog-1",
            "source_type": "editorial",
            "url": "https://example.com/visa",
            "publisher": "Travel Blog",
            "retrieved_at": "2026-08-20T12:00:00+00:00",
        }
    ]
    state.candidates["claims"] = [
        {
            "id": "claim-visa",
            "topic": "entry",
            "status": "reported",
            "source_ids": ["blog-1"],
            "applies_to": ["traveler-1"],
        }
    ]

    findings = critical_evidence_findings(state, NOW)

    assert findings[0].rule_id == "EVID-001"
    assert findings[0].severity == "blocking"
    assert findings[0].affected_ids == ("claim-visa",)


def test_official_source_satisfies_high_stakes_gate(state: TripState) -> None:
    """Catch a gate that blocks a claim already backed by a direct official source."""
    state.candidates["claims"] = [
        {
            "id": "claim-entry",
            "topic": "entry",
            "status": "verified",
            "source_ids": ["official-1"],
        }
    ]

    assert critical_evidence_findings(state, NOW) == ()


def test_future_schedule_is_not_invented() -> None:
    """Catch an unreleased schedule being converted into a fabricated value."""
    assessment = assess_claim({"status": "not_released_yet"}, {}, NOW)

    assert assessment.value is None
    assert assessment.next_check_at is not None
    assert assessment.next_check_at > NOW


def test_sources_projection_includes_readiness_claims(state: TripState) -> None:
    """Catch a human-readable source view that omits operational rechecks."""
    state.candidates["claims"] = [
        {
            "id": "claim-visa",
            "topic": "entry",
            "status": "verified",
            "source_ids": ["official-1"],
        }
    ]
    state.readiness["items"] = [
        {
            "id": "ready-entry",
            "category": "entry",
            "status": "recheck",
            "source_ids": ["official-1"],
            "claim_ids": ["claim-visa"],
        }
    ]

    markdown = render_sources_markdown(state)

    assert "claim-visa" in markdown
    assert "ready-entry" in markdown
    assert "last checked" in markdown.lower()


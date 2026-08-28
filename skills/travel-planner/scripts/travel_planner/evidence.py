"""Evidence confidence, high-stakes gates, and source projections."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from .state import TripState

HIGH_STAKES_TOPICS = frozenset(
    {
        "entry",
        "transit",
        "medication_legality",
        "health",
        "safety_advisory",
        "emergency",
        "transport_operations",
    }
)


@dataclass(frozen=True)
class ClaimAssessment:
    status: str
    value: Any | None
    confidence: Literal["high", "medium", "low"]
    next_check_at: datetime | None


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Literal["blocking", "warning", "note"]
    confidence: Literal["high", "medium", "low"]
    affected_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    message: str
    proposed_patch: Mapping[str, Any] | None = None
    rule_version: int = 1


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _source_index(state: TripState) -> dict[str, dict[str, Any]]:
    sources = state.candidates.get("sources", [])
    return {
        source["id"]: source
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }


def _iter_claims(state: TripState) -> Iterable[dict[str, Any]]:
    for claim in state.candidates.get("claims", []):
        if isinstance(claim, dict):
            yield claim
    for candidate in state.candidates.get("items", []):
        if not isinstance(candidate, dict):
            continue
        for claim in candidate.get("claims", []):
            if isinstance(claim, dict):
                yield claim


def assess_claim(
    claim: Mapping[str, Any], sources: Mapping[str, Mapping[str, Any]], now: datetime
) -> ClaimAssessment:
    """Assess a claim without filling unknown values or unreleased schedules."""
    status = str(claim.get("status", "unverified"))
    if status == "not_released_yet":
        next_check = _parse_datetime(claim.get("next_check_at")) or now + timedelta(days=7)
        return ClaimAssessment(status, None, "low", next_check)

    referenced = [sources[source_id] for source_id in claim.get("source_ids", []) if source_id in sources]
    official = any(source.get("source_type") == "official" for source in referenced)
    freshness = claim.get("freshness_status", "unknown")
    if status == "conflicting" or freshness == "stale":
        confidence: Literal["high", "medium", "low"] = "low"
    elif status == "verified" and official:
        confidence = "high"
    elif status == "verified":
        confidence = "medium"
    else:
        confidence = "low"
    next_check = now if freshness == "stale" else _parse_datetime(claim.get("next_check_at"))
    return ClaimAssessment(status, claim.get("value"), confidence, next_check)


def critical_evidence_findings(state: TripState, now: datetime) -> tuple[Finding, ...]:
    """Block unresolved high-stakes guidance until direct official evidence exists."""
    del now
    sources = _source_index(state)
    findings: list[Finding] = []
    for claim in _iter_claims(state):
        if claim.get("topic") not in HIGH_STAKES_TOPICS:
            continue
        source_ids = tuple(str(value) for value in claim.get("source_ids", []))
        has_official = any(
            source_id in sources and sources[source_id].get("source_type") == "official"
            for source_id in source_ids
        )
        if claim.get("status") == "verified" and has_official:
            continue
        claim_id = str(claim.get("id", "unknown-claim"))
        topic = str(claim.get("topic"))
        findings.append(
            Finding(
                rule_id="EVID-001",
                severity="blocking",
                confidence="high",
                affected_ids=(claim_id,),
                evidence_ids=source_ids,
                message=f"{topic} requires a current direct official source before finalization.",
                proposed_patch={
                    "readiness_id": f"evidence-{claim_id}",
                    "category": topic if topic in {"entry", "transit", "health", "emergency"} else "documents",
                    "status": "action_needed",
                },
            )
        )
    return tuple(sorted(findings, key=lambda finding: (finding.rule_id, finding.affected_ids)))


def render_sources_markdown(state: TripState) -> str:
    """Build a stable human-readable projection of claims, sources, and rechecks."""
    sources = _source_index(state)
    lines = ["# Sources", "", "## Claims", ""]
    claims = sorted(_iter_claims(state), key=lambda claim: str(claim.get("id", "")))
    if not claims:
        lines.append("No structured claims recorded.")
    for claim in claims:
        claim_id = str(claim.get("id", "unknown-claim"))
        lines.append(f"- **{claim_id}** — {claim.get('status', 'unverified')}")
        for source_id in sorted(str(value) for value in claim.get("source_ids", [])):
            source = sources.get(source_id, {})
            publisher = source.get("publisher", "Unknown publisher")
            url = source.get("url", "unavailable")
            checked = source.get("retrieved_at", "unknown")
            lines.append(f"  - {source_id}: {publisher} — {url}")
            lines.append(f"  - Last checked: {checked}")
    lines.extend(["", "## Readiness references", ""])
    readiness_items = sorted(
        state.readiness.get("items", []), key=lambda item: str(item.get("id", ""))
    )
    if not readiness_items:
        lines.append("No readiness source references recorded.")
    for item in readiness_items:
        claim_ids = ", ".join(str(value) for value in item.get("claim_ids", [])) or "none"
        source_ids = ", ".join(str(value) for value in item.get("source_ids", [])) or "none"
        lines.append(
            f"- **{item.get('id', 'unknown-item')}** — claims: {claim_ids}; sources: {source_ids}"
        )
    return "\n".join(lines).rstrip() + "\n"

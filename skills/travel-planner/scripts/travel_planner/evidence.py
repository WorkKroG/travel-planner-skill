"""Source metadata indexes and the generated human-readable sources report."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .state import TripState


def source_index(state: TripState) -> dict[str, dict[str, Any]]:
    """Index explicitly identified source metadata without assessing its truth."""
    return {
        source["id"]: source
        for source in state.candidates.get("sources", [])
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }


def iter_claims(state: TripState) -> Iterable[dict[str, Any]]:
    """Iterate top-level and candidate-local claim metadata."""
    for claim in state.candidates.get("claims", []):
        if isinstance(claim, dict):
            yield claim
    for candidate in state.candidates.get("items", []):
        if not isinstance(candidate, dict):
            continue
        for claim in candidate.get("claims", []):
            if isinstance(claim, dict):
                yield claim


def render_sources_markdown(state: TripState) -> str:
    """Build a stable projection of source, claim, and readiness links."""
    sources = source_index(state)
    lines = ["# Sources", "", "## Claims", ""]
    claims = sorted(iter_claims(state), key=lambda claim: str(claim.get("id", "")))
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
        (
            item
            for item in state.readiness.get("items", [])
            if isinstance(item, dict)
        ),
        key=lambda item: str(item.get("id", "")),
    )
    if not readiness_items:
        lines.append("No readiness source references recorded.")
    for item in readiness_items:
        claim_ids = ", ".join(str(value) for value in item.get("claim_ids", [])) or "none"
        source_ids = ", ".join(str(value) for value in item.get("source_ids", [])) or "none"
        lines.append(
            f"- **{item.get('id', 'unknown-item')}** — claims: {claim_ids}; sources: {source_ids}"
        )
    photos = [
        (day["id"], photo)
        for day in state.itinerary.get("days", [])
        for photo in day.get("media", [])
    ]
    if photos:
        lines.extend(["", "## Day photographs", ""])
        for day_id, photo in photos:
            source = sources.get(photo["source_id"], {})
            lines.append(f"- **{day_id} · {photo['caption']}** — {photo['path']}")
            lines.append(f"  - {photo['attribution']} · {photo['license']}")
            lines.append(f"  - {photo['source_id']}: {source.get('url', 'unavailable')}")
            if source.get("provenance"):
                lines.append(f"  - {source['provenance']}")
    return "\n".join(lines).rstrip() + "\n"

"""Source metadata indexes and the generated human-readable sources report."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable, Mapping
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .state import TripState, dump_state_yaml
from .workspace import CANONICAL_FILES


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
    lines = ["# Sources", "", f"Trip: {state.brief['trip_id']}", "", "## Source inventory", ""]
    if not sources:
        lines.append("No sources recorded.")
    for source_id in sorted(sources):
        lines.extend([
            f"### {source_id}", "", "```yaml",
            dump_state_yaml(sources[source_id]).rstrip(),
            "```", "",
        ])
    lines.extend(["## Claims", ""])
    claims = sorted(iter_claims(state), key=lambda claim: str(claim.get("id", "")))
    if not claims:
        lines.append("No structured claims recorded.")
    for claim in claims:
        claim_id = str(claim.get("id", "unknown-claim"))
        lines.append(f"- **{claim_id}** — {claim.get('status', 'unverified')}")
        lines.extend(["", "```yaml", dump_state_yaml(claim).rstrip(), "```", ""])
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
    lines.extend(["", "## Day and program references", ""])
    for day in state.itinerary.get("days", []):
        lines.append(f"### {day['id']}")
        lines.append(f"- Sources: {', '.join(day.get('source_ids', [])) or 'none'}")
        lines.append(f"- Last checked: {day.get('last_checked', 'unknown')}")
        timelines = [("primary", day.get("timeline", []))]
        timelines.extend((scenario["id"], scenario["timeline"])
                         for scenario in day.get("scenarios", []))
        for scenario_id, timeline in timelines:
            for event in timeline:
                lines.append(f"- {scenario_id} / {event['id']}: {event.get('title', '')}")
                for key in ("source_ids", "claim_ids", "links", "alternatives"):
                    if event.get(key):
                        lines.extend(["", "```yaml",
                                      dump_state_yaml({key: event[key]}).rstrip(), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def canonical_input_hashes(root: Path) -> dict[str, str]:
    """Fingerprint the explicit trip inputs before loading them for a build."""
    root = root.expanduser().resolve()
    return {name: sha256((root / name).read_bytes()).hexdigest() for name in CANONICAL_FILES}


def write_source_snapshot(
    state: TripState, html: bytes, directory: Path, generated_at: datetime,
    *, input_hashes: Mapping[str, str],
) -> Path:
    """Archive evidence for exact HTML bytes without replacing an earlier inventory."""
    digest = sha256(html).hexdigest()
    target = directory / f"{digest}.md"
    if canonical_input_hashes(state.root) != input_hashes:
        raise ValueError("Trip inputs changed during rendering; rerun the build on saved files.")
    inputs = "\n".join(f"- {name}: {input_hashes[name]}" for name in CANONICAL_FILES)
    content = (
        f"# Build source snapshot\n\nHTML SHA-256: {digest}\n"
        f"Generated: {generated_at.isoformat()}\n"
        f"Document status: {state.itinerary.get('document_status')}\n"
        f"Verification level: {state.itinerary.get('verification_level')}\n"
        f"Finalization basis: {state.itinerary.get('finalization_basis')}\n\n"
        f"## Canonical input SHA-256\n\n{inputs}\n\n"
        "This inventory records the build's evidence, not a fresh remote verification.\n\n"
        + render_sources_markdown(state)
    ).encode("utf-8")
    if directory.is_symlink():
        raise ValueError(f"Source snapshot directory must not be a symlink: {directory}")
    directory.mkdir(parents=True, exist_ok=True)

    def validate_existing() -> None:
        if target.is_symlink() or not target.is_file():
            raise ValueError(f"Source snapshot must be a regular file: {target}")
        if target.read_bytes() != content:
            raise ValueError(
                f"Source snapshot already exists with different evidence: {target}. "
                "Use a new --at generation time for the changed plan."
            )

    if target.exists() or target.is_symlink():
        validate_existing()
        return target
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as staged:
        staging_path = Path(staged.name)
        try:
            staged.write(content)
            staged.flush()
            try:
                os.link(staging_path, target)
            except FileExistsError:
                validate_existing()
        finally:
            staging_path.unlink(missing_ok=True)
    return target

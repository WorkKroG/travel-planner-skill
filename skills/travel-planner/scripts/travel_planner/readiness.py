"""Deterministic readiness scheduling and evidence-item synchronization."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from .evidence import Finding

_CLOSED_STATUSES = frozenset({"confirmed", "waived", "not_applicable"})
_USER_DECISION_STATUSES = frozenset({"selected", "booked", "confirmed", "waived", "not_applicable"})


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def next_recheck(item: Mapping[str, Any], trip_start: datetime) -> datetime | None:
    """Return the next deterministic review time for an operational item."""
    explicit = _parse_datetime(item.get("next_check_at"))
    if explicit is not None:
        return explicit
    status = item.get("status", "unknown")
    if status in _CLOSED_STATUSES:
        return None
    if status == "not_released_yet":
        return _parse_datetime(item.get("release_at")) or trip_start - timedelta(days=30)
    if status == "recheck":
        return trip_start - timedelta(days=7)
    return _parse_datetime(item.get("due_at"))


def sync_evidence_findings(
    readiness: Mapping[str, Any], findings: Iterable[Finding]
) -> dict[str, Any]:
    """Add evidence actions without replacing user-owned readiness decisions."""
    result = dict(readiness)
    items = [dict(item) for item in readiness.get("items", [])]
    by_id = {str(item.get("id")): item for item in items}
    for finding in findings:
        if finding.rule_id != "EVID-001" or not finding.affected_ids:
            continue
        patch = dict(finding.proposed_patch or {})
        item_id = str(patch.get("readiness_id", f"evidence-{finding.affected_ids[0]}"))
        existing = by_id.get(item_id)
        if existing is None:
            existing = {
                "id": item_id,
                "category": patch.get("category", "documents"),
                "status": patch.get("status", "action_needed"),
            }
            items.append(existing)
            by_id[item_id] = existing
        elif existing.get("status") not in _USER_DECISION_STATUSES:
            existing["status"] = patch.get("status", "action_needed")
        existing.setdefault("claim_ids", list(finding.affected_ids))
        existing.setdefault("source_ids", list(finding.evidence_ids))
        existing["finding_rule_id"] = finding.rule_id
    result["items"] = items
    return result

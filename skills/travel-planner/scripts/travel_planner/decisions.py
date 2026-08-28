"""Append-only human-readable decision journal."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class DuplicateDecisionError(ValueError):
    """Raised when an immutable decision ID is reused."""


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    decided_at: datetime
    selected_option: str
    reason: str
    rejected_alternatives: tuple[str, ...] = ()
    affected_ids: tuple[str, ...] = ()


def _one_line(value: str) -> str:
    return " ".join(value.splitlines()).strip()


def _format_record(record: DecisionRecord) -> str:
    rejected = ", ".join(_one_line(value) for value in record.rejected_alternatives) or "None"
    affected = ", ".join(record.affected_ids) or "None"
    timestamp = record.decided_at.isoformat()
    return (
        f"\n<!-- decision:{record.decision_id} -->\n"
        f"## {timestamp} — {record.decision_id}\n\n"
        f"- Selected: {_one_line(record.selected_option)}\n"
        f"- Reason: {_one_line(record.reason)}\n"
        f"- Rejected alternatives: {rejected}\n"
        f"- Affected IDs: {affected}\n"
    )


def append_decision(path: Path, record: DecisionRecord) -> None:
    """Append one immutable decision without changing existing journal content."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    existing = destination.read_text(encoding="utf-8") if destination.exists() else "# Decisions\n"
    marker = f"<!-- decision:{record.decision_id} -->"
    if marker in existing:
        raise DuplicateDecisionError(f"Decision ID already exists: {record.decision_id}")
    if not destination.exists():
        destination.write_text(existing, encoding="utf-8")
    with destination.open("a", encoding="utf-8") as stream:
        stream.write(_format_record(record))
        stream.flush()
        os.fsync(stream.fileno())

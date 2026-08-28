"""Previewed, confirmed and recoverable trip-state schema migrations."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .state import STATE_SCHEMA_FILES, write_state_file


class MigrationError(RuntimeError):
    """Base error for a state migration that cannot be completed safely."""


class ConfirmationRequired(MigrationError):
    """Raised when a write is requested without explicit confirmation."""


class SourceChanged(MigrationError):
    """Raised when trip state changed after its migration preview."""


@dataclass(frozen=True)
class MigrationChange:
    file_name: str
    source_digest: str
    before: Mapping[str, Any]
    after: Mapping[str, Any]


@dataclass(frozen=True)
class MigrationPlan:
    root: Path
    target_version: int
    changes: tuple[MigrationChange, ...]
    backup_root: Path
    previewed_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": "preview",
            "root": str(self.root),
            "target_version": self.target_version,
            "files": [change.file_name for change in self.changes],
            "backup_root": str(self.backup_root),
            "previewed_at": self.previewed_at.isoformat(),
        }


def _load_mapping(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MigrationError(f"Expected a YAML mapping in {path}")
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preview_migration(root: Path, target_version: int) -> MigrationPlan:
    """Build a read-only plan from the exact current bytes of every state file."""
    trip_root = Path(root).expanduser().resolve(strict=False)
    if target_version < 1:
        raise MigrationError("Target schema version must be positive.")
    previewed_at = datetime.now(UTC)
    timestamp = previewed_at.strftime("%Y%m%dT%H%M%S%fZ")
    backup_root = trip_root.parent / f"{trip_root.name}.backup-{timestamp}"
    changes: list[MigrationChange] = []
    for file_name in STATE_SCHEMA_FILES:
        path = trip_root / file_name
        before = _load_mapping(path)
        try:
            current_version = int(before["schema_version"])
        except (KeyError, TypeError, ValueError) as error:
            raise MigrationError(f"Invalid schema_version in {path}") from error
        if current_version > target_version:
            raise MigrationError(
                f"Downgrade is not supported: {file_name} is version {current_version}."
            )
        if current_version == target_version:
            continue
        if current_version + 1 != target_version:
            raise MigrationError(
                f"No direct migration from version {current_version} to {target_version}."
            )
        after = dict(before)
        after["schema_version"] = target_version
        changes.append(MigrationChange(file_name, _digest(path), before, after))
    return MigrationPlan(trip_root, target_version, tuple(changes), backup_root, previewed_at)


def _validate_migrated_root(root: Path, target_version: int) -> None:
    trip_ids: set[str] = set()
    for file_name in STATE_SCHEMA_FILES:
        value = _load_mapping(root / file_name)
        if value.get("schema_version") != target_version:
            raise MigrationError(f"{file_name} was not migrated to version {target_version}.")
        trip_id = value.get("trip_id")
        if not isinstance(trip_id, str) or not trip_id:
            raise MigrationError(f"{file_name} has no valid trip_id.")
        trip_ids.add(trip_id)
    if len(trip_ids) != 1:
        raise MigrationError("Migrated files do not share one trip_id.")


def _restore_state_files(plan: MigrationPlan) -> None:
    for file_name in STATE_SCHEMA_FILES:
        shutil.copy2(plan.backup_root / file_name, plan.root / file_name)


def apply_migration(plan: MigrationPlan, confirmed: bool) -> None:
    """Apply an unchanged preview after backup; restore source files on any failure."""
    if not confirmed:
        raise ConfirmationRequired("Migration requires explicit confirmation after preview.")
    if not plan.changes:
        return
    for change in plan.changes:
        if _digest(plan.root / change.file_name) != change.source_digest:
            raise SourceChanged(
                f"{change.file_name} changed after preview; create a new migration plan."
            )
    if plan.backup_root.exists():
        raise MigrationError(f"Backup path already exists: {plan.backup_root}")

    backup_created = False
    try:
        shutil.copytree(plan.root, plan.backup_root)
        backup_created = True
        for change in plan.changes:
            write_state_file(plan.root / change.file_name, change.after)
        _validate_migrated_root(plan.root, plan.target_version)
    except Exception as error:
        if backup_created:
            _restore_state_files(plan)
            raise MigrationError(
                f"Migration failed and original state was restored: {error}"
            ) from error
        if isinstance(error, MigrationError):
            raise
        raise MigrationError(f"Migration failed before backup was created: {error}") from error

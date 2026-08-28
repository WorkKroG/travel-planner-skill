"""Safe creation and discovery of isolated trip workspaces."""

from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import yaml

STATE_FILES = (
    "brief.yaml",
    "candidates.yaml",
    "itinerary.yaml",
    "readiness.yaml",
    "decisions.md",
    "sources.md",
)
PROJECT_REMINDER = (
    "Для новой поездки рекомендуется отдельная папка и локальный Codex project. "
    "Подтвердите выбранный путь перед созданием файлов."
)
_TRIP_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


class WorkspaceError(ValueError):
    """Base error for unsafe workspace operations."""


class WorkspaceExistsError(WorkspaceError):
    """Raised when initialization would alter an existing trip."""


class WorkspacePathError(WorkspaceError):
    """Raised when the selected target is not a safe trip location."""


@dataclass(frozen=True)
class TripPaths:
    """Canonical paths for one trip workspace."""

    root: Path
    brief: Path
    candidates: Path
    itinerary: Path
    readiness: Path
    decisions: Path
    sources: Path
    outputs: Path


def _paths_for(root: Path) -> TripPaths:
    return TripPaths(
        root=root,
        brief=root / "brief.yaml",
        candidates=root / "candidates.yaml",
        itinerary=root / "itinerary.yaml",
        readiness=root / "readiness.yaml",
        decisions=root / "decisions.md",
        sources=root / "sources.md",
        outputs=root / "outputs",
    )


def _default_trip_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]
    return slug or f"trip-{uuid4().hex[:8]}"


def _validate_target(root: Path) -> None:
    source_root = Path(__file__).resolve().parents[4]
    if root == source_root or source_root in root.parents:
        raise WorkspacePathError("Trip workspaces must be outside the installed skill source.")
    if root.exists() and not root.is_dir():
        raise WorkspacePathError(f"Workspace target is not a directory: {root}")
    if (root / "brief.yaml").exists():
        raise WorkspaceExistsError(f"A trip workspace already exists at {root}")
    conflicts = [name for name in STATE_FILES if (root / name).exists()]
    if (root / "outputs").exists():
        conflicts.append("outputs")
    if conflicts:
        raise WorkspacePathError(
            "Workspace files already exist and will not be overwritten: " + ", ".join(conflicts)
        )


def _prepare_staging(staging: Path, title: str, trip_id: str) -> None:
    template_root = Path(__file__).resolve().parents[2] / "assets" / "trip-template"
    for name in STATE_FILES:
        source = template_root / name
        target = staging / name
        if source.suffix == ".yaml":
            data = yaml.safe_load(source.read_text(encoding="utf-8"))
            data["trip_id"] = trip_id
            if name == "brief.yaml":
                data["title"] = title
                data["updated_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
            target.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
        else:
            shutil.copyfile(source, target)
    (staging / "outputs").mkdir()


def initialize_trip(root: Path, title: str, trip_id: str | None = None) -> TripPaths:
    """Create a complete workspace without overwriting any existing trip data."""
    target = Path(root).expanduser().resolve(strict=False)
    identity = trip_id or _default_trip_id(title)
    if not _TRIP_ID_PATTERN.fullmatch(identity):
        raise WorkspacePathError(
            "trip_id must be lower-case letters, digits, and single hyphens (maximum 64 chars)."
        )
    _validate_target(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    created: list[Path] = []
    try:
        _prepare_staging(staging, title, identity)
        target.mkdir(parents=True, exist_ok=True)
        for child in sorted(staging.iterdir(), key=lambda path: path.name):
            destination = target / child.name
            child.replace(destination)
            created.append(destination)
    except Exception:
        for path in reversed(created):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return _paths_for(target)


def discover_trip_roots(start: Path) -> list[Path]:
    """Return every valid trip root; never choose one on the user's behalf."""
    search_root = Path(start).expanduser().resolve(strict=False)
    if not search_root.exists():
        return []
    found: list[Path] = []
    for brief in search_root.rglob("brief.yaml"):
        try:
            value = yaml.safe_load(brief.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(value, dict) and isinstance(value.get("trip_id"), str) and value["trip_id"]:
            found.append(brief.parent)
    return sorted(found, key=lambda path: str(path.relative_to(search_root)))

"""Locate runtime schemas and templates in source and installed distributions."""

from __future__ import annotations

import sysconfig
from collections.abc import Sequence
from pathlib import Path

_SOURCE_SUBDIRECTORIES = {
    "schemas": Path("schemas"),
    "trip-template": Path("assets/trip-template"),
}


def _default_roots(group: str) -> tuple[Path, ...]:
    if group not in _SOURCE_SUBDIRECTORIES:
        raise ValueError(f"Unknown resource group: {group}")
    skill_root = Path(__file__).resolve().parents[2]
    installed_root = (
        Path(sysconfig.get_path("data")) / "share" / "codex-travel-planner" / group
    )
    return (skill_root / _SOURCE_SUBDIRECTORIES[group], installed_root)


def resource_path(
    group: str, name: str, *, roots: Sequence[Path] | None = None
) -> Path:
    """Return a resource file from approved roots without allowing path traversal."""
    if not name or Path(name).name != name or Path(name).is_absolute():
        raise ValueError("Resource name must be a plain file name without parent traversal.")
    locations = tuple(Path(root) for root in roots) if roots is not None else _default_roots(group)
    for root in locations:
        candidate = root / name
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(root) for root in locations)
    raise FileNotFoundError(f"Resource {group}/{name} not found in: {searched}")


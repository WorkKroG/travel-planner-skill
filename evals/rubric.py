"""Shared contract validation for online-only semantic review rubrics."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from .adapters import RUBRIC_DIMENSIONS


def validate_online_rubric(
    rubric: Mapping[str, Any], *, label: str = "Rubric"
) -> Mapping[str, Any]:
    """Return an isolated rubric only when the full online-review contract is valid."""
    if set(rubric) != {"version", "review_mode", "dimensions"}:
        raise ValueError(f"{label} requires version, review_mode, and dimensions")
    if rubric.get("version") != 1:
        raise ValueError(f"{label} must use version 1")
    if rubric.get("review_mode") != "online-required":
        raise ValueError(f"{label} review_mode must be online-required")
    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != len(RUBRIC_DIMENSIONS):
        raise ValueError(f"{label} must declare six dimensions")
    if tuple(
        item.get("id") for item in dimensions if isinstance(item, Mapping)
    ) != RUBRIC_DIMENSIONS:
        raise ValueError(f"{label} has invalid dimensions")
    for item in dimensions:
        if not isinstance(item, Mapping):
            raise TypeError(f"{label} has invalid dimensions")
        if set(item) != {"id", "max_score", "criterion"}:
            raise ValueError(f"{label} dimension has unexpected fields")
        maximum = item.get("max_score")
        if isinstance(maximum, bool) or maximum != 4:
            raise ValueError(f"{label} has invalid thresholds")
        criterion = item.get("criterion")
        if not isinstance(criterion, str) or not criterion.strip():
            raise ValueError(f"{label} criterion must be non-empty")
    return copy.deepcopy(dict(rubric))

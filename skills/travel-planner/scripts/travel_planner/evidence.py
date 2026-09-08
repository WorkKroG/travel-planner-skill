"""Helpers for source and claim metadata in the current working data."""

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

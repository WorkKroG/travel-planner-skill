"""Controlled route lifecycle and structural alternative comparison."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from .state import TripState

RouteState = Literal["draft", "challenged", "selected", "frozen"]
ALLOWED: dict[RouteState, frozenset[RouteState]] = {
    "draft": frozenset({"challenged"}),
    "challenged": frozenset({"selected", "draft"}),
    "selected": frozenset({"frozen", "challenged"}),
    "frozen": frozenset({"challenged"}),
}
_STRUCTURAL_KINDS = frozenset({"hotel", "overnight", "region", "geography", "fixed_event", "flight"})
_SKELETON_DIMENSIONS = ("geography", "bases", "pace", "experience_mix")


class RouteLifecycleError(ValueError):
    """Base error for rejected route lifecycle operations."""


class FrozenRouteError(RouteLifecycleError):
    """Raised when a frozen structural decision lacks impact analysis or consent."""


class InvalidRouteTransition(RouteLifecycleError):
    """Raised when a route attempts to skip a lifecycle gate."""


@dataclass(frozen=True)
class RouteChange:
    kind: str
    affected_ids: tuple[str, ...] = ()
    consent: bool = False
    impact_summary: str | None = None


@dataclass(frozen=True)
class SkeletonComparison:
    distinct: bool
    differing_dimensions: tuple[str, ...]
    signatures: tuple[tuple[str, ...], ...]


def transition_route(state: TripState, target: RouteState, decision: RouteChange) -> TripState:
    """Return a copied state after enforcing lifecycle and frozen-route gates."""
    current = state.itinerary.get("route_state")
    if current not in ALLOWED:
        raise InvalidRouteTransition(f"Unknown route state: {current!r}")
    if current == "frozen" and (
        decision.kind in _STRUCTURAL_KINDS or target != current
    ) and (not decision.consent or not decision.impact_summary):
        raise FrozenRouteError(
            "Frozen route changes require an impact summary and explicit user consent."
        )
    if target != current and target not in ALLOWED[current]:
        raise InvalidRouteTransition(f"Route cannot transition from {current} to {target}.")
    if target == current and not (current == "frozen" and decision.kind in _STRUCTURAL_KINDS):
        raise InvalidRouteTransition(f"Route is already in state {target}.")

    updated = TripState(
        root=state.root,
        brief=deepcopy(state.brief),
        candidates=deepcopy(state.candidates),
        itinerary=deepcopy(state.itinerary),
        readiness=deepcopy(state.readiness),
    )
    updated.itinerary["route_state"] = target
    updated.itinerary["last_route_change"] = {
        "kind": decision.kind,
        "affected_ids": list(decision.affected_ids),
        "impact_summary": decision.impact_summary,
        "consent": decision.consent,
    }
    return updated


def _dimension_value(skeleton: Mapping[str, Any], dimension: str) -> str:
    return json.dumps(skeleton.get(dimension), ensure_ascii=False, sort_keys=True)


def compare_skeletons(skeletons: Sequence[Mapping[str, Any]]) -> SkeletonComparison:
    """Verify that alternatives differ in route structure, not presentation text."""
    signatures = tuple(
        tuple(_dimension_value(skeleton, dimension) for dimension in _SKELETON_DIMENSIONS)
        for skeleton in skeletons
    )
    differing = tuple(
        dimension
        for index, dimension in enumerate(_SKELETON_DIMENSIONS)
        if len({signature[index] for signature in signatures}) > 1
    )
    distinct = len(signatures) <= 1 or len(set(signatures)) == len(signatures)
    return SkeletonComparison(distinct, differing, signatures)


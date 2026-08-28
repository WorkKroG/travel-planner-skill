import shutil
from pathlib import Path

import pytest
from travel_planner.route import (
    FrozenRouteError,
    InvalidRouteTransition,
    RouteChange,
    compare_skeletons,
    transition_route,
)
from travel_planner.state import load_trip


@pytest.fixture
def frozen_state(tmp_path: Path):
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    state = load_trip(target)
    state.itinerary["route_state"] = "frozen"
    return state


def test_frozen_route_requires_impact_and_consent(frozen_state) -> None:
    """Catch a structural frozen-route mutation that bypasses explicit consent."""
    request = RouteChange(kind="hotel", affected_ids=("night-4",), consent=False)

    with pytest.raises(FrozenRouteError):
        transition_route(frozen_state, "frozen", request)

    assert frozen_state.itinerary["route_state"] == "frozen"


def test_route_cannot_jump_from_draft_to_frozen(frozen_state) -> None:
    """Catch a route that skips challenge and selection gates."""
    frozen_state.itinerary["route_state"] = "draft"

    with pytest.raises(InvalidRouteTransition):
        transition_route(frozen_state, "frozen", RouteChange(kind="status"))


def test_allowed_transition_returns_new_state_without_mutating_input(frozen_state) -> None:
    """Catch lifecycle validation mutating source state before acceptance."""
    frozen_state.itinerary["route_state"] = "draft"

    updated = transition_route(frozen_state, "challenged", RouteChange(kind="challenge"))

    assert updated.itinerary["route_state"] == "challenged"
    assert frozen_state.itinerary["route_state"] == "draft"


def test_skeletons_must_differ_structurally() -> None:
    """Catch paraphrased alternatives presented as meaningfully different routes."""
    first = {
        "id": "route-a",
        "geography": ["tokyo", "kyoto"],
        "bases": ["tokyo", "kyoto"],
        "pace": "balanced",
        "experience_mix": ["culture", "food"],
    }
    second = {**first, "id": "route-b", "label": "Classic highlights"}

    comparison = compare_skeletons([first, second])

    assert comparison.distinct is False
    assert comparison.differing_dimensions == ()


def test_structurally_different_skeletons_report_changed_dimensions() -> None:
    """Catch a comparison that detects difference but cannot explain it."""
    first = {
        "id": "route-a",
        "geography": ["tokyo"],
        "bases": ["tokyo"],
        "pace": "slow",
        "experience_mix": ["culture"],
    }
    second = {
        "id": "route-b",
        "geography": ["tokyo", "nagano"],
        "bases": ["tokyo", "matsumoto"],
        "pace": "active",
        "experience_mix": ["culture", "nature"],
    }

    comparison = compare_skeletons([first, second])

    assert comparison.distinct is True
    assert comparison.differing_dimensions == (
        "geography",
        "bases",
        "pace",
        "experience_mix",
    )


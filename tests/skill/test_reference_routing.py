"""Stage routing contracts for the travel-planner skill."""

from __future__ import annotations

import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "travel-planner"
SKILL_PATH = SKILL_ROOT / "SKILL.md"
ROUTE = re.compile(r"^\| `(?P<stage>[a-z_]+)` \| \[[^]]+\]\((?P<path>references/[^)]+)\) \|$")


def parse_reference_routes(path: Path) -> dict[str, str]:
    """Read the public stage-to-reference routing table from the dispatcher."""
    routes: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROUTE.match(line)
        if match:
            routes[match.group("stage")] = match.group("path")
    return routes


def test_every_workflow_stage_has_one_owned_reference() -> None:
    """Catch missing or ambiguous guidance when a user enters any planning stage."""
    routes = parse_reference_routes(SKILL_PATH)

    assert routes == {
        "new_trip": "references/onboarding.md",
        "resume": "references/onboarding.md",
        "intake": "references/intake.md",
        "research": "references/research.md",
        "route_synthesis": "references/route-synthesis.md",
        "challenge": "references/challenge.md",
        "day_planning": "references/day-planning.md",
        "transport_maps": "references/transport-and-maps.md",
        "readiness_budget": "references/readiness-and-budget.md",
        "security": "references/security.md",
        "finalize": "references/render-and-qa.md",
    }


def test_every_routed_reference_is_installable() -> None:
    """Catch a dead dispatcher link before the skill is packaged or installed."""
    routes = parse_reference_routes(SKILL_PATH)

    assert routes
    missing = [reference for reference in routes.values() if not (SKILL_ROOT / reference).is_file()]
    assert missing == []

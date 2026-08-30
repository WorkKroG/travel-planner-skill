"""Deterministic reference-graph contracts for the travel-planner router."""

from __future__ import annotations

import os
import re
from pathlib import Path

DEFAULT_SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "travel-planner"
ROUTE = re.compile(r"^\| `(?P<stage>[a-z_]+)` \| \[[^]]+\]\((?P<path>references/[^)]+\.md)\) \|$")
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\((?P<path>[^)#]+\.md)(?:#[^)]+)?\)")


def _skill_root() -> Path:
    return Path(os.environ.get("TRAVEL_PLANNER_SKILL_ROOT", DEFAULT_SKILL_ROOT)).resolve()


def parse_reference_routes(path: Path) -> dict[str, str]:
    """Read the public stage-to-reference routing table from the dispatcher."""
    routes: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROUTE.match(line)
        if match:
            routes[match.group("stage")] = match.group("path")
    return routes


def _reachable_markdown(skill_root: Path) -> set[Path]:
    pending = [skill_root / "SKILL.md"]
    visited: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        assert path.is_file(), f"reference graph has a dangling path: {path}"
        visited.add(path)
        for match in MARKDOWN_LINK.finditer(path.read_text(encoding="utf-8")):
            target = (path.parent / match.group("path")).resolve()
            try:
                target.relative_to(skill_root)
            except ValueError:
                continue
            pending.append(target)
    return visited


def test_primary_stages_have_one_owner_and_security_is_additive() -> None:
    """Risk guidance supplements the active stage instead of competing with it."""
    skill_root = _skill_root()
    routes = parse_reference_routes(skill_root / "SKILL.md")

    assert set(routes) == {
        "new_trip",
        "resume",
        "intake",
        "research",
        "compare_select",
        "detail_change",
        "readiness_budget",
        "review_render",
        "continue_elsewhere",
    }, f"primary stage inventory is contradictory or incomplete: {sorted(routes)}"
    assert routes["new_trip"] == routes["resume"]
    assert routes["compare_select"] == routes["detail_change"]
    assert routes["review_render"] == routes["continue_elsewhere"]
    assert all(not reference.endswith("security.md") for reference in routes.values())

    reachable = _reachable_markdown(skill_root)
    assert skill_root / "references" / "security.md" in reachable


def test_reference_graph_has_seven_reachable_documents_and_no_dangling_links() -> None:
    """Progressive disclosure reaches every installed reference through valid links."""
    skill_root = _skill_root()
    reachable = _reachable_markdown(skill_root)
    reachable_references = {path for path in reachable if path.parent == skill_root / "references"}
    installed_references = set((skill_root / "references").glob("*.md"))

    assert len(installed_references) == 7
    assert reachable_references == installed_references

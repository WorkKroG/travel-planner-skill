"""Executable contracts for the user-visible Travel Planner workflow."""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path

from travel_planner.cli import _parser, main
from travel_planner.workspace import CANONICAL_FILES, GENERATED_DIRECTORIES, GENERATED_FILES

ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / "skills" / "travel-planner"
SKILL_PATH = SKILL_ROOT / "SKILL.md"
ROUTE = re.compile(r"^\| `(?P<stage>[a-z_]+)` \| \[[^]]+\]\((?P<path>references/[^)]+)\) \|$")


def _active_documents() -> tuple[Path, ...]:
    routes: list[Path] = []
    for line in SKILL_PATH.read_text(encoding="utf-8").splitlines():
        if match := ROUTE.match(line):
            path = SKILL_ROOT / match.group("path")
            if path not in routes:
                routes.append(path)
    return (SKILL_PATH, *routes)


def _bash_examples() -> list[list[str]]:
    commands: list[list[str]] = []
    for path in _active_documents():
        fenced = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line == "```bash":
                fenced = True
                continue
            if line == "```":
                fenced = False
                continue
            if fenced and line.startswith("travel-planner "):
                commands.append(shlex.split(line))
    return commands


def _command_names(parser: argparse.ArgumentParser) -> tuple[str, ...]:
    action = next(
        item for item in parser._actions if isinstance(item, argparse._SubParsersAction)
    )
    return tuple(action.choices)


def _normalise_example(tokens: list[str], workspace: Path) -> list[str]:
    replacements = {
        "PATH": str(workspace),
        "TITLE": "Executable contract trip",
        "TRIP_ID": "executable-contract-trip",
        "<evaluation-time-iso8601-with-offset>": "2026-08-30T09:00:00+00:00",
    }
    normalized = []
    for token in tokens[1:]:
        for old, new in replacements.items():
            token = token.replace(old, new)
        normalized.append(token)
    return normalized


def _markdown_table(path: Path, required_headers: set[str]) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        headers = [cell.strip() for cell in line.strip("|").split("|")]
        if not required_headers <= set(headers) or index + 1 >= len(lines):
            continue
        rows: list[dict[str, str]] = []
        for row in lines[index + 2 :]:
            if not row.startswith("|"):
                break
            values = [cell.strip() for cell in row.strip("|").split("|")]
            if len(values) == len(headers):
                rows.append(dict(zip(headers, values, strict=True)))
        return rows
    raise AssertionError(f"table with {sorted(required_headers)} not found in {path}")


def test_documented_cli_examples_execute_real_handlers_and_match_inventory(
    tmp_path: Path, capsys,
) -> None:
    """Catch removed aliases, malformed examples, and docs that omit a real command."""
    examples = _bash_examples()
    assert examples
    assert {tokens[1] for tokens in examples} == set(_command_names(_parser()))

    workspace = tmp_path / "trip"
    for tokens in examples:
        arguments = _normalise_example(tokens, workspace)
        parsed = _parser().parse_args(arguments)
        if parsed.command == "init" and workspace.exists():
            continue
        assert main(arguments) == 0
        capsys.readouterr()

    assert (workspace / "outputs" / "itinerary.html").read_text(encoding="utf-8").startswith(
        "<!doctype html>"
    )


def test_documented_bundle_matches_init_ownership_and_projection(tmp_path: Path) -> None:
    """Catch chat/HTML/source projections being promoted to canonical state."""
    rows = _markdown_table(
        SKILL_ROOT / "references" / "onboarding.md", {"Path", "Ownership"}
    )
    documented = {
        row["Path"].strip("`"): row["Ownership"]
        for row in rows
    }
    assert {name for name, role in documented.items() if role == "canonical"} == set(
        CANONICAL_FILES
    )
    assert {name for name, role in documented.items() if role == "generated"} == {
        *GENERATED_FILES,
        *(f"{name}/" for name in GENERATED_DIRECTORIES),
    }

    workspace = tmp_path / "trip"
    assert main(
        [
            "init",
            str(workspace),
            "--title",
            "Ownership contract",
            "--trip-id",
            "ownership-contract",
            "--confirm-path",
        ]
    ) == 0
    assert {path.name for path in workspace.iterdir()} == {
        name.removesuffix("/") for name in documented
    }


def test_surface_matrix_never_grants_codex_validation_without_helpers() -> None:
    """Catch Chat/Work/mobile guidance claiming deterministic Codex validation."""
    rows = _markdown_table(
        SKILL_ROOT / "references" / "verification-and-render.md",
        {"Surface", "Deterministic helpers", "Allowed verification"},
    )
    by_surface = {row["Surface"]: row for row in rows}

    assert "check" in by_surface["Codex"]["Deterministic helpers"]
    assert "codex_validated" in by_surface["Codex"]["Allowed verification"]
    for surface in ("Chat/Work", "mobile"):
        assert by_surface[surface]["Deterministic helpers"] == "unavailable"
        assert set(re.findall(r"`([^`]+)`", by_surface[surface]["Allowed verification"])) == {
            "none",
            "ai_reviewed",
        }


def test_material_change_and_source_routing_have_user_controlled_outcomes() -> None:
    """Catch a route state machine replacing consent, decisions, or source policy."""
    planning = SKILL_ROOT / "references" / "planning.md"
    rows = _markdown_table(planning, {"Situation", "Required outcome"})
    outcomes = {row["Situation"]: row["Required outcome"] for row in rows}

    material = outcomes["Material user-decision change"].lower()
    assert all(token in material for token in ("affected", "consent", "decisions.md"))
    assert "yandex" in outcomes["Russia/CIS/Turkey with auto maps"].lower()

    research = (SKILL_ROOT / "references" / "research.md").read_text(encoding="utf-8").lower()
    for topic in ("visa", "transit", "medical", "legal", "safety"):
        assert topic in research
    assert "official" in research


def test_active_workflow_has_no_removed_pipeline_or_state_machine() -> None:
    """Catch legacy workflow concepts even when they are no longer shell examples."""
    active = "\n".join(path.read_text(encoding="utf-8") for path in _active_documents())
    forbidden = (
        r"\bvalidate\b",
        r"\bchallenge\b",
        r"\bimpact\b",
        r"\bfinalize\b",
        r"\bqa\b",
        r"\breceipt\b",
        r"\battestation\b",
        r"\bfrozen?\b",
        r"partial rebuild",
        r"offline (?:mode|workflow|review)",
        r"degraded",
        r"pdf (?:adapter|pipeline|command|output)",
        r"markdown (?:output|renderer)",
    )
    matches = [pattern for pattern in forbidden if re.search(pattern, active, re.IGNORECASE)]
    assert matches == []

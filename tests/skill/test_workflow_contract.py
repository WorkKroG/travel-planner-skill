"""Deterministic contracts for docs, CLI, state, and the reference graph.

These tests exercise concrete artifacts. They do not simulate or score model behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from travel_planner.cli import _parser, main
from travel_planner.workspace import CANONICAL_FILES, GENERATED_DIRECTORIES, GENERATED_FILES

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SKILL_ROOT = ROOT / "skills" / "travel-planner"
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\((?P<path>[^)#]+\.md)(?:#[^)]+)?\)")


def _skill_root() -> Path:
    return Path(os.environ.get("TRAVEL_PLANNER_SKILL_ROOT", DEFAULT_SKILL_ROOT)).resolve()


def _active_documents() -> tuple[Path, ...]:
    """Follow every local Markdown edge from SKILL.md and fail cleanly on a dead edge."""
    skill_root = _skill_root()
    pending = [skill_root / "SKILL.md"]
    visited: set[Path] = set()

    while pending:
        path = pending.pop()
        if path in visited:
            continue
        assert path.is_file(), f"active reference graph has a dangling path: {path}"
        visited.add(path)
        for match in MARKDOWN_LINK.finditer(path.read_text(encoding="utf-8")):
            target = (path.parent / match.group("path")).resolve()
            try:
                target.relative_to(skill_root)
            except ValueError:
                continue
            pending.append(target)

    return tuple(sorted(visited))


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
    action = next(item for item in parser._actions if isinstance(item, argparse._SubParsersAction))
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


def _markdown_tables(path: Path) -> list[tuple[set[str], list[dict[str, str]]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    tables: list[tuple[set[str], list[dict[str, str]]]] = []
    for index, line in enumerate(lines):
        if not line.startswith("|") or index + 1 >= len(lines):
            continue
        headers = [cell.strip() for cell in line.strip("|").split("|")]
        separator = lines[index + 1]
        if not separator.startswith("|") or not all(
            re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in separator.strip("|").split("|")
        ):
            continue
        rows: list[dict[str, str]] = []
        for row in lines[index + 2 :]:
            if not row.startswith("|"):
                break
            values = [cell.strip() for cell in row.strip("|").split("|")]
            if len(values) == len(headers):
                rows.append(dict(zip(headers, values, strict=True)))
        tables.append((set(headers), rows))
    return tables


def _contract_rows(required_headers: set[str]) -> list[dict[str, str]]:
    for path in _active_documents():
        for headers, rows in _markdown_tables(path):
            if required_headers <= headers:
                return rows
    raise AssertionError(
        "active reference graph lacks a structured contract with columns "
        f"{sorted(required_headers)}"
    )


def _code_values(value: str) -> set[str]:
    return set(re.findall(r"`([^`]+)`", value))


def _row_by_code(rows: list[dict[str, str]], column: str, value: str) -> dict[str, str]:
    matches = [row for row in rows if value in _code_values(row[column])]
    assert len(matches) == 1, f"expected one {value!r} row in {column!r}, got {len(matches)}"
    return matches[0]


def _single_code_value(value: str, label: str) -> str:
    values = _code_values(value)
    assert len(values) == 1, f"expected one structured value for {label}, got {sorted(values)}"
    return next(iter(values))


def _accepted_blocker_schema() -> tuple[dict[str, object], dict[str, object]]:
    schema = json.loads(
        (_skill_root() / "schemas" / "itinerary.schema.json").read_text(encoding="utf-8")
    )
    definition = schema["$defs"]["accepted_blocker"]
    validator_schema = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": "#/$defs/accepted_blocker",
    }
    return definition, validator_schema


def _yaml_examples() -> list[dict[str, object]]:
    examples: list[dict[str, object]] = []
    for path in _active_documents():
        text = path.read_text(encoding="utf-8")
        for block in re.findall(r"```yaml\n(.*?)\n```", text, re.DOTALL):
            value = yaml.safe_load(block)
            if isinstance(value, dict):
                examples.append(value)
    return examples


def test_documented_cli_examples_execute_real_handlers_and_match_inventory(
    tmp_path: Path,
    capsys,
) -> None:
    """Every documented command must be recognized and execute its real handler."""
    examples = _bash_examples()
    assert examples, "active docs contain no executable travel-planner examples"
    documented = {tokens[1] for tokens in examples}
    actual = set(_command_names(_parser()))
    assert documented == actual, f"documented commands {documented} != parser commands {actual}"

    workspace = tmp_path / "trip"
    for tokens in examples:
        arguments = _normalise_example(tokens, workspace)
        parsed = _parser().parse_args(arguments)
        if parsed.command == "init" and workspace.exists():
            continue
        assert main(arguments) == 0
        capsys.readouterr()

    assert (
        (workspace / "outputs" / "itinerary.html")
        .read_text(encoding="utf-8")
        .startswith("<!doctype html>")
    )


def test_documented_bundle_matches_init_ownership_and_projection(tmp_path: Path) -> None:
    """Canonical ownership and generated projections must match real init output."""
    rows = _contract_rows({"Path", "Ownership"})
    documented = {row["Path"].strip("`"): row["Ownership"] for row in rows}
    assert {name for name, role in documented.items() if role == "canonical"} == set(
        CANONICAL_FILES
    )
    assert {name for name, role in documented.items() if role == "generated"} == {
        *GENERATED_FILES,
        *(f"{name}/" for name in GENERATED_DIRECTORIES),
    }

    workspace = tmp_path / "trip"
    assert (
        main(
            [
                "init",
                str(workspace),
                "--title",
                "Ownership contract",
                "--trip-id",
                "ownership-contract",
                "--confirm-path",
            ]
        )
        == 0
    )
    assert {path.name for path in workspace.iterdir()} == {
        name.removesuffix("/") for name in documented
    }


def test_surface_contract_requires_honest_verification_gates() -> None:
    """Helperless surfaces stay below Codex validation and disclose AI-review limits."""
    rows = _contract_rows(
        {
            "Surface",
            "Deterministic helpers",
            "Allowed verification",
            "Required disclosure",
            "Codex validation gate",
        }
    )
    by_surface = {_single_code_value(row["Surface"], "surface"): row for row in rows}

    codex = by_surface["codex"]
    assert "check" in _code_values(codex["Deterministic helpers"])
    assert "codex_validated" in _code_values(codex["Allowed verification"])
    assert {"successful_check", "no_blockers"} <= _code_values(codex["Codex validation gate"])

    for surface in ("chat_web", "mobile"):
        row = by_surface[surface]
        assert _code_values(row["Deterministic helpers"]) == {"unavailable"}
        assert _code_values(row["Allowed verification"]) == {"none", "ai_reviewed"}
        assert _code_values(row["Codex validation gate"]) == {"never"}
        assert {"less_precise", "careful_human_review"} <= _code_values(row["Required disclosure"])


def test_material_change_contract_preserves_consent_and_affected_scope() -> None:
    """A material decision change must explain consequences before the smallest edit."""
    rows = _contract_rows({"Case", "Explain before edit", "User gate", "Update scope", "Record"})
    material = _row_by_code(rows, "Case", "material_change")

    assert _code_values(material["Explain before edit"]) == {
        "route",
        "days",
        "budget",
        "readiness",
    }
    assert _code_values(material["User gate"]) == {"explicit_consent"}
    assert _code_values(material["Update scope"]) == {"affected_only"}
    assert _code_values(material["Record"]) == {"decisions.md"}


def test_day_contract_applies_to_initial_detail_and_material_change() -> None:
    """Detailed and changed days retain the decision-relevant information reviewers need."""
    applicability = _contract_rows({"Day contract applicability"})
    assert {
        value for row in applicability for value in _code_values(row["Day contract applicability"])
    } == {"initial_detail", "material_change"}

    rows = _contract_rows({"Day facet", "Required content"})
    actual = {
        _single_code_value(row["Day facet"], "day facet"): _code_values(row["Required content"])
        for row in rows
    }
    expected = {
        "intent": {"thesis"},
        "summary": {"load", "travel"},
        "cutoffs": {"critical_cutoffs", "latest_switch_point"},
        "scenarios": {"primary", "realistic_backup"},
        "context": {"meal", "booking"},
        "evidence": {"linked_sources", "claim_status"},
        "transport": {
            "local_time",
            "door_to_door",
            "comfortable_alternative",
            "budget_alternative",
        },
    }
    assert actual == expected


def test_documented_acceptance_fields_validate_against_actual_schema() -> None:
    """The lifecycle table must name fields accepted by the shipped itinerary schema."""
    rows = _contract_rows({"Final basis", "Required state", "Remaining blockers"})
    user_confirmed = _row_by_code(rows, "Final basis", "user_confirmed")
    documented_fields = _code_values(user_confirmed["Remaining blockers"].split(";", 1)[0])
    definition, _ = _accepted_blocker_schema()

    assert documented_fields == set(definition["required"])


def test_documented_acceptance_yaml_example_validates_against_actual_schema() -> None:
    """The copyable acceptance record must remain valid when the real schema changes."""
    definition, validator_schema = _accepted_blocker_schema()
    property_names = set(definition["properties"])
    candidates = [example for example in _yaml_examples() if property_names & set(example)]
    assert len(candidates) == 1, (
        f"expected one accepted_blocker YAML example, got {len(candidates)}"
    )

    errors = sorted(
        Draft202012Validator(validator_schema, format_checker=FormatChecker()).iter_errors(
            candidates[0]
        ),
        key=lambda error: error.message,
    )

    assert errors == [], "; ".join(error.message for error in errors)


def test_user_confirmed_final_keeps_every_accepted_blocker_visible() -> None:
    """User confirmation records acceptance without erasing unresolved blockers."""
    rows = _contract_rows({"Final basis", "Required state", "Remaining blockers"})
    user_confirmed = _row_by_code(rows, "Final basis", "user_confirmed")

    assert {"document_status: final", "finalization_basis: user_confirmed"} <= _code_values(
        user_confirmed["Required state"]
    )
    assert {
        "blocker_id",
        "itinerary.yaml.accepted_blockers",
        "one_per_blocker",
        "partial_forbidden",
        "duplicate_forbidden",
        "orphan_forbidden",
        "challenge_findings",
        "acceptance_not_replacement",
        "blocking",
        "unresolved",
        "visible",
    } <= _code_values(user_confirmed["Remaining blockers"])


def test_source_routing_keeps_yandex_and_official_high_stakes_sources() -> None:
    """Location policy and high-stakes freshness remain in the active graph."""
    active = "\n".join(path.read_text(encoding="utf-8") for path in _active_documents()).lower()
    assert "yandex" in active
    assert "russia/cis/turkey" in active
    for topic in ("visa", "transit", "medical", "legal", "safety"):
        assert topic in active
    assert "official" in active


def test_active_workflow_has_no_removed_pipeline_or_state_machine() -> None:
    """Active docs must not reintroduce retired commands or workflow machinery."""
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

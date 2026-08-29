"""Load executable, offline scenario directories for the eval harness."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from travel_planner.impact import semantic_hash

SCENARIOS_ROOT = Path(__file__).resolve().parent / "scenarios"
REQUIRED_FILES = frozenset(
    {
        "brief.yaml",
        "sources.yaml",
        "operations.yaml",
        "traps.yaml",
        "expected-hard.yaml",
        "rubric.yaml",
        "README.md",
    }
)
RUBRIC_DIMENSIONS = (
    "skeleton_distinctness",
    "tradeoffs",
    "pacing",
    "backup_usefulness",
    "readability",
    "calibrated_uncertainty",
)


@dataclass(frozen=True)
class ScenarioCase:
    """One self-contained offline fixture, including its own grading rubric."""

    case_id: str
    path: Path
    brief: Mapping[str, Any]
    sources: Mapping[str, Any]
    operations: Mapping[str, Any]
    traps: Mapping[str, Any]
    expected_hard: Mapping[str, Any]
    rubric_path: Path
    scenario: Mapping[str, Any]
    semantic_hashes: Mapping[str, str]


def _mapping(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"Cannot load {label}: {path}: {error}") from error
    if not isinstance(value, Mapping):
        raise TypeError(f"{label.capitalize()} must be a YAML mapping: {path}")
    return value


def _case_paths(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    cases: dict[str, Path] = {}
    for path in sorted(root.iterdir()):
        if path.is_dir() and path.name != "adversarial":
            cases[path.name] = path
    adversarial = root / "adversarial"
    if adversarial.is_dir():
        for path in sorted(adversarial.iterdir()):
            if path.is_dir():
                if path.name in cases:
                    raise ValueError(f"Duplicate scenario id: {path.name}")
                cases[path.name] = path
    return cases


def scenario_ids(root: Path = SCENARIOS_ROOT) -> set[str]:
    """Return every executable directory id, including the adversarial matrix."""
    return set(_case_paths(Path(root)))


def adversarial_case_ids(root: Path = SCENARIOS_ROOT) -> set[str]:
    """Return the case ids represented by adversarial fixture directories."""
    adversarial = Path(root) / "adversarial"
    return {path.name for path in adversarial.iterdir() if path.is_dir()} if adversarial.is_dir() else set()


def _semantic_hashes(operations: Mapping[str, Any]) -> dict[str, str]:
    preservation = operations.get("preservation", [])
    if not isinstance(preservation, list):
        raise TypeError("operations.preservation must be a list when supplied")
    hashes: dict[str, str] = {}
    for mutation in preservation:
        if not isinstance(mutation, Mapping):
            raise TypeError("operations.preservation entries must be mappings")
        for boundary in ("before", "after"):
            value = mutation.get(boundary)
            if not isinstance(value, Mapping):
                raise TypeError("operations.preservation entries require before and after mappings")
            for entity_id, entity in value.items():
                hashes[f"{entity_id}-{boundary}"] = semantic_hash(entity)
    return hashes


def _hard_checks(expected_hard: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings = expected_hard.get("required_findings")
    if not isinstance(findings, list) or not findings:
        raise ValueError("expected-hard.yaml requires a non-empty required_findings list")
    checks: list[dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, Mapping):
            raise TypeError("expected-hard.yaml required_findings must be mappings")
        rule_id = finding.get("rule_id")
        path = finding.get("path")
        expected = finding.get("equals")
        if not isinstance(rule_id, str) or not isinstance(path, str) or not path:
            raise ValueError("required findings need rule_id and operation path")
        checks.append(
            {
                "rule_id": rule_id,
                "path": path,
                "equals": expected,
                "evidence": {
                    "severity": finding.get("severity"),
                    "affected_ids": finding.get("affected_ids", []),
                    "fixture": finding.get("evidence", rule_id),
                },
            }
        )
    return checks


def load_scenario_case(case_id: str, root: Path = SCENARIOS_ROOT) -> ScenarioCase:
    """Read a fixture directory into the exact scenario mapping the harness executes."""
    paths = _case_paths(Path(root))
    try:
        path = paths[case_id]
    except KeyError as error:
        raise ValueError(f"Unknown scenario fixture: {case_id}") from error
    missing = REQUIRED_FILES - {item.name for item in path.iterdir()}
    if missing:
        raise ValueError(f"Scenario fixture {case_id} is missing: {', '.join(sorted(missing))}")
    brief = _mapping(path / "brief.yaml", "brief")
    sources = _mapping(path / "sources.yaml", "sources")
    operations_data = _mapping(path / "operations.yaml", "operations")
    operations = operations_data.get("operations")
    if not isinstance(operations, Mapping):
        raise TypeError("operations.yaml requires an operations mapping")
    traps = _mapping(path / "traps.yaml", "traps")
    expected_hard = _mapping(path / "expected-hard.yaml", "expected hard expectations")
    if expected_hard.get("scenario_id") != case_id:
        raise ValueError(f"Scenario id in expected-hard.yaml must match directory: {case_id}")
    expected_macro_pass = expected_hard.get("expected_macro_pass")
    if not isinstance(expected_macro_pass, bool):
        raise TypeError("expected-hard.yaml requires boolean expected_macro_pass")
    prompt = operations_data.get("prompt")
    prompt_version = operations_data.get("prompt_version")
    response = operations_data.get("response")
    if not all(isinstance(value, str) and value for value in (prompt, prompt_version, response)):
        raise ValueError("operations.yaml requires non-empty prompt, prompt_version, and response strings")
    scenario = {
        "id": case_id,
        "prompt_version": prompt_version,
        "prompt": prompt,
        "hard_checks": _hard_checks(expected_hard),
        "fixture_response": {"text": response, "operations": copy.deepcopy(dict(operations))},
        "fixture_judge": {
            "scores": {dimension: 4 for dimension in RUBRIC_DIMENSIONS},
        },
        "expected_macro_pass": expected_macro_pass,
        "rubric_path": path / "rubric.yaml",
        "scenario_semantic_hashes": _semantic_hashes(operations_data),
    }
    return ScenarioCase(
        case_id=case_id,
        path=path,
        brief=brief,
        sources=sources,
        operations=copy.deepcopy(dict(operations)),
        traps=traps,
        expected_hard=expected_hard,
        rubric_path=path / "rubric.yaml",
        scenario=scenario,
        semantic_hashes=scenario["scenario_semantic_hashes"],
    )


def load_scenario_world(root: Path = SCENARIOS_ROOT) -> Mapping[str, Any]:
    """Build a fixture-adapter world exclusively from checked-in scenario directories."""
    cases = {case_id: load_scenario_case(case_id, root) for case_id in sorted(scenario_ids(root))}
    return {"version": 1, "scenarios": {case_id: case.scenario for case_id, case in cases.items()}}

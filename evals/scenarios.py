"""Validated, input-driven offline scenario contracts for the eval harness."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from travel_planner.resources import resource_path

from .reference_evaluator import validate_contract
from .rubric import validate_online_rubric

SCENARIOS_ROOT = Path(__file__).resolve().parent / "scenarios"
REQUIRED_FILES = frozenset({"brief.yaml", "sources.yaml", "operations.yaml", "traps.yaml", "expected-hard.yaml", "rubric.yaml", "README.md"})


@dataclass(frozen=True)
class ScenarioCatalog:
    case_ids: set[str]


@dataclass(frozen=True)
class ScenarioCase:
    case_id: str
    path: Path
    brief: Mapping[str, Any]
    sources: Mapping[str, Any]
    reference_evaluator: Mapping[str, Any]
    traps: Mapping[str, Any]
    expected_hard: Mapping[str, Any]
    rubric_path: Path
    scenario: Mapping[str, Any]


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
        raise ValueError(f"Scenario root must be a directory: {root}")
    cases = {path.name: path for path in sorted(root.iterdir()) if path.is_dir() and path.name != "adversarial"}
    adversarial = root / "adversarial"
    if not adversarial.is_dir():
        raise ValueError(f"Scenario root is missing adversarial directory: {root}")
    for path in sorted(adversarial.iterdir()):
        if path.is_dir():
            if path.name in cases:
                raise ValueError(f"Duplicate scenario id: {path.name}")
            cases[path.name] = path
    if not cases:
        raise ValueError(f"Scenario root contains no fixture directories: {root}")
    return cases


def scenario_ids(root: Path = SCENARIOS_ROOT) -> set[str]:
    return set(_case_paths(Path(root)))


def adversarial_case_ids(root: Path = SCENARIOS_ROOT) -> set[str]:
    adversarial = Path(root) / "adversarial"
    if not adversarial.is_dir():
        raise ValueError(f"Scenario root is missing adversarial directory: {root}")
    return {path.name for path in adversarial.iterdir() if path.is_dir()}


def _validate_brief(brief: Mapping[str, Any], case_id: str) -> None:
    schema = json.loads(resource_path("schemas", "brief.schema.json").read_text(encoding="utf-8"))
    issues = list(Draft202012Validator(schema).iter_errors(brief))
    if issues:
        raise ValueError(f"Scenario {case_id} brief is not valid v1 state: {issues[0].message}")


def _validate_rubric(path: Path) -> Mapping[str, Any]:
    return validate_online_rubric(
        _mapping(path, "rubric"), label=f"Scenario rubric {path}"
    )


def _validate_sources_traps(sources: Mapping[str, Any], traps: Mapping[str, Any], case_id: str) -> None:
    source_items, trap_items = sources.get("sources"), traps.get("injected")
    if sources.get("mode") != "offline-frozen" or not isinstance(source_items, list) or not source_items:
        raise ValueError(f"Scenario {case_id} sources must be non-empty offline-frozen inputs")
    if not isinstance(trap_items, list) or not trap_items:
        raise ValueError(f"Scenario {case_id} traps must contain injected cases")
    for source in source_items:
        if (
            not isinstance(source, Mapping)
            or not isinstance(source.get("id"), str)
            or not source["id"]
            or not isinstance(source.get("type"), str)
            or not source["type"]
            or not isinstance(source.get("data"), Mapping)
            or not source["data"]
        ):
            raise ValueError(f"Scenario {case_id} source requires id, type, and structured data")
    for trap in trap_items:
        if (
            not isinstance(trap, Mapping)
            or not isinstance(trap.get("id"), str)
            or not trap["id"]
            or not isinstance(trap.get("kind"), str)
            or not trap["kind"]
            or not isinstance(trap.get("data"), Mapping)
            or not trap["data"]
        ):
            raise ValueError(f"Scenario {case_id} trap requires id, kind, and structured data")


def _hard_checks(expected: Mapping[str, Any]) -> list[dict[str, Any]]:
    findings = expected.get("required_findings")
    if not isinstance(findings, list) or not findings:
        raise ValueError("expected-hard.yaml requires a non-empty required_findings list")
    checks: list[dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, Mapping):
            raise TypeError("expected-hard.yaml required_findings must be mappings")
        rule, path, severity, affected = (finding.get(key) for key in ("rule_id", "path", "severity", "affected_ids"))
        if not isinstance(rule, str) or not isinstance(path, str) or not path or severity not in {"blocking", "warning"} or not isinstance(affected, list) or not affected or "equals" not in finding:
            raise ValueError("required findings need rule_id, path, severity, affected_ids, and equals")
        checks.append({"rule_id": rule, "path": path, "equals": finding["equals"], "evidence": dict(finding)})
    forbidden = expected.get("forbidden_behaviors")
    if not isinstance(forbidden, list) or not forbidden:
        raise ValueError("scenario requires forbidden behavior declarations")
    for behavior in forbidden:
        if not isinstance(behavior, Mapping) or not isinstance(behavior.get("behavior"), str) or not isinstance(behavior.get("path"), str) or not behavior["path"].startswith("effects."):
            raise ValueError("forbidden behavior requires behavior and effects path")
        checks.append({"rule_id": f"EVAL-FORBID-{behavior['behavior']}", "path": behavior["path"], "equals": behavior.get("equals", False), "evidence": {"behavior": behavior["behavior"]}})
    return checks


def load_scenario_case(case_id: str, root: Path = SCENARIOS_ROOT) -> ScenarioCase:
    paths = _case_paths(Path(root))
    if case_id not in paths:
        raise ValueError(f"Unknown scenario fixture: {case_id}")
    path = paths[case_id]
    missing = REQUIRED_FILES - {item.name for item in path.iterdir()}
    if missing:
        raise ValueError(f"Scenario fixture {case_id} is missing: {', '.join(sorted(missing))}")
    if not (path / "README.md").read_text(encoding="utf-8").strip().startswith("#"):
        raise ValueError(f"Scenario {case_id} requires a human-readable README")
    brief, sources, traps = _mapping(path / "brief.yaml", "brief"), _mapping(path / "sources.yaml", "sources"), _mapping(path / "traps.yaml", "traps")
    _validate_brief(brief, case_id)
    _validate_sources_traps(sources, traps, case_id)
    rubric = _validate_rubric(path / "rubric.yaml")
    expected, data = _mapping(path / "expected-hard.yaml", "expected hard expectations"), _mapping(path / "operations.yaml", "operations")
    if set(data) != {"prompt", "prompt_version", "reference_evaluator"}:
        raise ValueError("operations.yaml requires exactly prompt, prompt_version, and reference evaluator")
    if expected.get("scenario_id") != case_id or not isinstance(expected.get("expected_macro_pass"), bool):
        raise ValueError(f"Scenario {case_id} has invalid expected-hard metadata")
    prompt, version, reference_evaluator = (data.get(key) for key in ("prompt", "prompt_version", "reference_evaluator"))
    if not all(isinstance(value, str) and value for value in (prompt, version)):
        raise ValueError("operations.yaml requires prompt and prompt_version")
    if not isinstance(reference_evaluator, Mapping):
        raise TypeError("operations.yaml requires a reference evaluator mapping")
    if "response" in data or "operations" in data:
        raise ValueError("operations.yaml must not contain authored response or outcome operations")
    if set(reference_evaluator) != {"version", "kind", "parameters"}:
        raise ValueError("reference evaluator requires exactly version, kind, and parameters")
    fixture_input = {
        "brief": json.loads(json.dumps(brief)),
        "sources": json.loads(json.dumps(sources)),
        "traps": json.loads(json.dumps(traps)),
    }
    evaluator_contract = {
        "version": reference_evaluator["version"],
        "kind": reference_evaluator["kind"],
        "parameters": json.loads(json.dumps(reference_evaluator["parameters"])),
    }
    validate_contract(case_id, fixture_input, evaluator_contract)
    input_hash = hashlib.sha256(
        json.dumps(fixture_input, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    scenario = {
        "id": case_id,
        "check_scope": "legacy_skill_behavior",
        "prompt_version": version,
        "prompt": f"{prompt}\n\nSCENARIO_INPUT:\n{json.dumps(fixture_input, ensure_ascii=False, sort_keys=True)}",
        "fixture_input": fixture_input,
        "fixture_input_hash": input_hash,
        "hard_checks": _hard_checks(expected),
        "reference_evaluator": {
            "version": evaluator_contract["version"],
            "kind": evaluator_contract["kind"],
            "fixture_input": fixture_input,
            "parameters": evaluator_contract["parameters"],
        },
        "online_review_required": rubric["review_mode"] == "online-required",
        "expected_macro_pass": expected["expected_macro_pass"],
        "expected_failed_findings": expected.get("expected_failed_findings", []),
        "rubric_path": path / "rubric.yaml",
    }
    return ScenarioCase(
        case_id,
        path,
        brief,
        sources,
        evaluator_contract,
        traps,
        expected,
        path / "rubric.yaml",
        scenario,
    )


def validate_scenario_catalog(root: Path = SCENARIOS_ROOT) -> ScenarioCatalog:
    ids = scenario_ids(root)
    for case_id in ids:
        load_scenario_case(case_id, root)
    return ScenarioCatalog(ids)


def load_scenario_world(root: Path = SCENARIOS_ROOT) -> Mapping[str, Any]:
    catalog = validate_scenario_catalog(root)
    return {"version": 2, "scenarios": {case_id: load_scenario_case(case_id, root).scenario for case_id in sorted(catalog.case_ids)}}

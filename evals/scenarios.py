"""Validated, input-driven offline scenario contracts for the eval harness."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from travel_planner.impact import analyze_change, semantic_hash
from travel_planner.resources import resource_path
from travel_planner.route import FrozenRouteError, RouteChange, transition_route
from travel_planner.state import TripState

SCENARIOS_ROOT = Path(__file__).resolve().parent / "scenarios"
REQUIRED_FILES = frozenset({"brief.yaml", "sources.yaml", "operations.yaml", "traps.yaml", "expected-hard.yaml", "rubric.yaml", "README.md"})
RUBRIC_DIMENSIONS = ("skeleton_distinctness", "tradeoffs", "pacing", "backup_usefulness", "readability", "calibrated_uncertainty")


@dataclass(frozen=True)
class ScenarioCatalog:
    case_ids: set[str]


@dataclass(frozen=True)
class ScenarioCase:
    case_id: str
    path: Path
    brief: Mapping[str, Any]
    sources: Mapping[str, Any]
    operations: Mapping[str, Any]
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


def _validate_rubric(path: Path) -> None:
    rubric = _mapping(path, "rubric")
    dimensions = rubric.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) != len(RUBRIC_DIMENSIONS):
        raise ValueError(f"Scenario rubric must declare six dimensions: {path}")
    if tuple(item.get("id") for item in dimensions if isinstance(item, Mapping)) != RUBRIC_DIMENSIONS:
        raise ValueError(f"Scenario rubric has invalid dimensions: {path}")
    if any(not isinstance(item.get("max_score"), (int, float)) or isinstance(item.get("max_score"), bool) for item in dimensions if isinstance(item, Mapping)):
        raise ValueError(f"Scenario rubric has invalid thresholds: {path}")


def _validate_sources_traps(sources: Mapping[str, Any], traps: Mapping[str, Any], case_id: str) -> None:
    source_items, trap_items = sources.get("sources"), traps.get("injected")
    if sources.get("mode") != "offline-frozen" or not isinstance(source_items, list) or not source_items:
        raise ValueError(f"Scenario {case_id} sources must be non-empty offline-frozen inputs")
    if not isinstance(trap_items, list) or not trap_items:
        raise ValueError(f"Scenario {case_id} traps must contain injected cases")
    for source in source_items:
        if not isinstance(source, Mapping) or not isinstance(source.get("id"), str) or not isinstance(source.get("type"), str) or not isinstance(source.get("facts"), list) or not source["facts"]:
            raise ValueError(f"Scenario {case_id} source requires id, type, and concrete facts")
    for trap in trap_items:
        if not isinstance(trap, Mapping) or not all(isinstance(trap.get(key), str) and trap[key] for key in ("id", "input", "required_behavior")):
            raise ValueError(f"Scenario {case_id} trap requires id, input, and required_behavior")


def _hard_checks(expected: Mapping[str, Any], operations: Mapping[str, Any]) -> list[dict[str, Any]]:
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
    effects = operations.get("effects")
    forbidden = expected.get("forbidden_behaviors")
    if not isinstance(effects, Mapping) or not isinstance(forbidden, list) or not forbidden:
        raise ValueError("scenario requires observable effects and forbidden behavior declarations")
    for behavior in forbidden:
        if isinstance(behavior, str):
            checks.append({"rule_id": f"EVAL-FORBID-{behavior}", "path": "effects.forbidden_behaviors", "equals": [], "evidence": {"behavior": behavior}})
            continue
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
    _validate_rubric(path / "rubric.yaml")
    expected, data = _mapping(path / "expected-hard.yaml", "expected hard expectations"), _mapping(path / "operations.yaml", "operations")
    if expected.get("scenario_id") != case_id or not isinstance(expected.get("expected_macro_pass"), bool):
        raise ValueError(f"Scenario {case_id} has invalid expected-hard metadata")
    operations, prompt, version, response, judge = (data.get(key) for key in ("operations", "prompt", "prompt_version", "response", "fixture_judge"))
    if not isinstance(operations, Mapping) or not all(isinstance(value, str) and value for value in (prompt, version, response)):
        raise ValueError("operations.yaml requires operations, prompt, prompt_version, and response")
    operations = copy.deepcopy(dict(operations))
    operations.setdefault("effects", {"forbidden_behaviors": []})
    if not isinstance(operations["effects"], Mapping):
        raise TypeError("operations effects must be a mapping")
    judge = judge if isinstance(judge, Mapping) else {"scores": {dimension: 3 + ((len(case_id) + index) % 2) for index, dimension in enumerate(RUBRIC_DIMENSIONS)}}
    scores = judge.get("scores")
    if not isinstance(scores, Mapping) or set(scores) != set(RUBRIC_DIMENSIONS):
        raise ValueError("operations.yaml requires six-dimension fixture_judge scores")
    fixture_input = {"brief": copy.deepcopy(dict(brief)), "sources": copy.deepcopy(dict(sources)), "traps": copy.deepcopy(dict(traps))}
    input_hash = semantic_hash(fixture_input)
    scenario = {"id": case_id, "prompt_version": version, "prompt": f"{prompt}\n\nSCENARIO_INPUT:\n{json.dumps(fixture_input, ensure_ascii=False, sort_keys=True)}", "fixture_input": fixture_input, "fixture_input_hash": input_hash, "hard_checks": _hard_checks(expected, operations), "fixture_response": {"text": response, "operations": copy.deepcopy(dict(operations)) | {"fixture_input_hash": input_hash}}, "fixture_judge": copy.deepcopy(dict(judge)), "expected_macro_pass": expected["expected_macro_pass"], "expected_failed_findings": expected.get("expected_failed_findings", []), "rubric_path": path / "rubric.yaml"}
    case = ScenarioCase(case_id, path, brief, sources, copy.deepcopy(dict(operations)), traps, expected, path / "rubric.yaml", scenario)
    scenario["case_mutation"] = execute_case(case)
    return case


def validate_scenario_catalog(root: Path = SCENARIOS_ROOT) -> ScenarioCatalog:
    ids = scenario_ids(root)
    for case_id in ids:
        load_scenario_case(case_id, root)
    return ScenarioCatalog(ids)


def load_scenario_world(root: Path = SCENARIOS_ROOT) -> Mapping[str, Any]:
    catalog = validate_scenario_catalog(root)
    return {"version": 2, "scenarios": {case_id: load_scenario_case(case_id, root).scenario for case_id in sorted(catalog.case_ids)}}


def _mutation_state(case: ScenarioCase) -> TripState:
    route_state = "frozen" if case.case_id == "frozen-mutation" else "selected"
    return TripState(Path("."), {"schema_version": 1, "trip_id": "fixture-mutation", "updated_at": "2026-08-28T12:00:00+00:00", "title": "Fixture", "travel_dates": {"start": "2026-11-04", "end": "2026-11-05"}, "travelers": [{"id": "traveler-a"}], "map_provider": "auto"}, {"schema_version": 1, "trip_id": "fixture-mutation", "sources": [], "items": []}, {"schema_version": 1, "trip_id": "fixture-mutation", "route_state": route_state, "alternatives": [], "selected_route_id": "route-a", "days": [{"id": "day-4", "activity": "garden-walk"}, {"id": "day-5", "activity": "market"}], "budget_items": [], "challenge_findings": []}, {"schema_version": 1, "trip_id": "fixture-mutation", "items": []})


def execute_case(case: ScenarioCase) -> Mapping[str, Any]:
    mutation = case.operations.get("mutation")
    if not isinstance(mutation, Mapping):
        return {}
    before = _mutation_state(case)
    if mutation.get("kind") == "weather_swap":
        after = copy.deepcopy(before)
        after.itinerary["days"][0]["activity"] = str(mutation["replacement_activity"])
        report = analyze_change(before, after)
        return {"day-4-before": semantic_hash(before.itinerary["days"][0]), "day-4-after": semantic_hash(after.itinerary["days"][0]), "day-5-before": semantic_hash(before.itinerary["days"][1]), "day-5-after": semantic_hash(after.itinerary["days"][1]), "impact_targets": [f"{item.kind}:{item.entity_id}" for item in report.targets]}
    if mutation.get("kind") == "frozen_hotel":
        route_before = semantic_hash(before.itinerary)
        try:
            transition_route(before, "frozen", RouteChange("hotel", (str(mutation["affected_id"]),)))
        except FrozenRouteError:
            return {"rejected": True, "route-before": route_before, "route-after": semantic_hash(before.itinerary)}
        return {"rejected": False, "route-before": route_before, "route-after": semantic_hash(before.itinerary)}
    raise ValueError(f"Unknown fixture mutation kind: {mutation.get('kind')!r}")

"""Run deterministic behavioral scenarios and write versioned audit traces."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:  # Support `python evals/run.py` from a checkout.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.adapters import AgentAdapter, CodexCliAdapter, FixtureAdapter
from evals.graders import grade_hard_invariants, grade_soft_rubric
from evals.types import AgentRun, EvalResult, HardCheck

TRACE_SCHEMA_VERSION = 1
_ROOT = Path(__file__).resolve().parent
DEFAULT_WORLD = _ROOT / "fixture-world" / "base.yaml"
DEFAULT_RUBRIC = _ROOT / "rubrics" / "quality.yaml"


def _load_yaml_mapping(path: Path, label: str) -> Mapping[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"Cannot load {label}: {path}: {error}") from error
    if not isinstance(loaded, Mapping):
        raise TypeError(f"{label.capitalize()} must be a YAML mapping: {path}")
    return loaded


def load_fixture_world(path: Path = DEFAULT_WORLD) -> Mapping[str, Any]:
    """Load the declared offline source of scenarios and fixture responses."""
    world = _load_yaml_mapping(path, "fixture world")
    if not isinstance(world.get("scenarios"), Mapping):
        raise TypeError("Fixture world requires a scenarios mapping.")
    return world


def _scenario_id(scenario: Mapping[str, Any]) -> str:
    value = scenario.get("id")
    if not isinstance(value, str) or not value:
        raise ValueError("Scenario requires a non-empty id.")
    return value


def _lookup(value: Mapping[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for component in dotted_path.split("."):
        if not isinstance(current, Mapping) or component not in current:
            return None
        current = current[component]
    return current


def _hard_checks(scenario: Mapping[str, Any], operations: Mapping[str, Any]) -> list[HardCheck]:
    definitions = scenario.get("hard_checks")
    if not isinstance(definitions, list) or not definitions:
        raise ValueError(f"Scenario {_scenario_id(scenario)} requires a non-empty hard_checks list.")
    checks: list[HardCheck] = []
    for definition in definitions:
        if not isinstance(definition, Mapping):
            raise TypeError("Scenario hard_checks entries must be mappings.")
        rule_id = definition.get("rule_id")
        dotted_path = definition.get("path")
        expected = definition.get("equals")
        if not isinstance(rule_id, str) or not rule_id or not isinstance(dotted_path, str) or not dotted_path:
            raise ValueError("Hard checks require non-empty rule_id and path.")
        actual = _lookup(operations, dotted_path)
        evidence = {
            "fixture_evidence": definition.get("evidence", ""),
            "path": dotted_path,
            "expected": expected,
            "actual": actual,
        }
        checks.append(
            HardCheck(
                rule_id=rule_id,
                status="passed" if actual == expected else "failed",
                evidence=evidence,
                message=f"Expected {dotted_path} to equal {expected!r}.",
                rule_version=int(definition.get("rule_version", 1)),
            )
        )
    return checks


def _prompt(scenario: Mapping[str, Any]) -> tuple[str, str]:
    prompt = scenario.get("prompt")
    version = scenario.get("prompt_version")
    if not isinstance(prompt, str) or not prompt or not isinstance(version, str) or not version:
        raise ValueError(f"Scenario {_scenario_id(scenario)} requires prompt and prompt_version strings.")
    return version, f"SCENARIO_ID: {_scenario_id(scenario)}\nPROMPT_VERSION: {version}\n\n{prompt}"


def _failed_adapter_run(adapter: AgentAdapter, error: Exception) -> AgentRun:
    return AgentRun(
        response="",
        operations={},
        metadata={"adapter": adapter.name},
        errors=(f"adapter error: {type(error).__name__}: {error}",),
    )


def run_scenario(
    scenario: Mapping[str, Any],
    adapter: AgentAdapter,
    *,
    results_dir: Path = _ROOT / "results",
    rubric_path: Path = DEFAULT_RUBRIC,
    workspace: Path | None = None,
) -> EvalResult:
    """Run one scenario, grade it, and retain every input/output needed to inspect it."""
    scenario_id = _scenario_id(scenario)
    prompt_version, prompt = _prompt(scenario)
    started_at = datetime.now(UTC)
    try:
        agent_run = adapter.run(prompt, workspace or Path.cwd())
    except Exception as error:  # noqa: BLE001 - third-party adapters may raise arbitrary exceptions.
        agent_run = _failed_adapter_run(adapter, error)
    errors = list(agent_run.errors)
    try:
        checks = _hard_checks(scenario, agent_run.operations)
    except (TypeError, ValueError) as error:
        checks = [
            HardCheck(
                "EVAL-001",
                "failed",
                {"scenario_id": scenario_id},
                "Scenario hard-check configuration is invalid.",
            )
        ]
        errors.append(f"scenario error: {error}")
    try:
        rubric = _load_yaml_mapping(rubric_path, "rubric")
        soft = grade_soft_rubric(agent_run.operations, rubric)
    except (TypeError, ValueError) as error:
        checks.append(
            HardCheck(
                "EVAL-002",
                "failed",
                {"rubric_path": str(rubric_path)},
                "Soft-rubric configuration could not be loaded or graded.",
            )
        )
        soft = None
        errors.append(f"rubric error: {error}")
    hard = grade_hard_invariants(checks)
    results_path = Path(results_dir)
    results_path.mkdir(parents=True, exist_ok=True)
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    trace_path = results_path / f"{scenario_id}-{timestamp}.json"
    trace = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "scenario_id": scenario_id,
        "adapter": adapter.name,
        "adapter_metadata": dict(agent_run.metadata),
        "prompt_version": prompt_version,
        "started_at": started_at.isoformat(),
        "prompt": prompt,
        "response": agent_run.response,
        "operations": dict(agent_run.operations),
        "grading": {"hard": hard.as_dict(), "soft": soft.as_dict() if soft else None},
        "degraded": list(agent_run.degraded),
        "errors": errors,
    }
    trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return EvalResult(scenario_id, hard, soft, trace_path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Travel Planner behavioral evals.")
    parser.add_argument("--adapter", choices=("fixture", "codex-cli"), required=True)
    requested = parser.add_mutually_exclusive_group(required=True)
    requested.add_argument("--scenario")
    requested.add_argument("--all", action="store_true")
    parser.add_argument("--results-dir", type=Path, default=_ROOT / "results")
    parser.add_argument("--fixture-world", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--codex-command", nargs="+")
    parser.add_argument("--model")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        world = load_fixture_world(args.fixture_world)
        scenarios = world["scenarios"]
        assert isinstance(scenarios, Mapping)
        if args.all:
            selected = [scenario for _, scenario in sorted(scenarios.items())]
        else:
            scenario = scenarios.get(args.scenario)
            if not isinstance(scenario, Mapping):
                raise ValueError(f"Unknown scenario: {args.scenario}")
            selected = [scenario]
        if args.adapter == "fixture":
            adapter: AgentAdapter = FixtureAdapter(world)
        else:
            adapter = CodexCliAdapter(args.codex_command or (), model=args.model)
        results = [
            run_scenario(scenario, adapter, results_dir=args.results_dir, rubric_path=args.rubric)
            for scenario in selected
        ]
    except (TypeError, ValueError) as error:
        print(f"eval error: {error}", file=sys.stderr)
        return 2
    for result in results:
        status = "PASS" if result.hard.macro_pass else "FAIL"
        print(f"{result.scenario_id}: macro {status} ({result.trace_path})")
    return 0 if all(result.hard.macro_pass for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

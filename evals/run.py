"""Run deterministic behavioral scenarios and write versioned audit traces."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:  # Support `python evals/run.py` from a checkout.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.adapters import (
    AgentAdapter,
    CodexCliAdapter,
    FixtureAdapter,
    FixtureJudge,
    JudgeAdapter,
    normalize_judge_run,
)
from evals.graders import grade_hard_invariants, grade_soft_rubric
from evals.redaction import redact_value
from evals.types import AgentRun, EvalResult, HardCheck, JudgeRun, RubricReport

TRACE_SCHEMA_VERSION = 1
_ROOT = Path(__file__).resolve().parent
DEFAULT_WORLD = _ROOT / "fixture-world" / "base.yaml"
DEFAULT_RUBRIC = _ROOT / "rubrics" / "quality.yaml"
DEFAULT_SCENARIOS_ROOT = _ROOT / "scenarios"
_SAFE_SCENARIO_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_MISSING = object()


class EvalSetupError(RuntimeError):
    """A deterministic, user-facing failure to allocate or write an eval trace."""


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


def load_executable_fixture_world(
    path: Path = DEFAULT_WORLD, scenarios_root: Path = DEFAULT_SCENARIOS_ROOT
) -> Mapping[str, Any]:
    """Merge legacy base cases with self-contained scenario-directory cases."""
    from evals.scenarios import load_scenario_world

    world = load_fixture_world(path)
    scenarios = dict(world["scenarios"])
    for case_id, scenario in load_scenario_world(scenarios_root)["scenarios"].items():
        if case_id in scenarios:
            raise ValueError(f"Scenario id collides with base fixture world: {case_id}")
        scenarios[case_id] = scenario
    return dict(world) | {"scenarios": scenarios}


def _scenario_id(scenario: Mapping[str, Any]) -> str:
    value = scenario.get("id")
    if not isinstance(value, str) or not _SAFE_SCENARIO_ID.fullmatch(value):
        raise ValueError("Scenario requires an id using the safe filename grammar.")
    return value


def _lookup(value: Mapping[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for component in dotted_path.split("."):
        if not isinstance(current, Mapping) or component not in current:
            return _MISSING
        current = current[component]
    return current


def _hard_checks(scenario: Mapping[str, Any], operations: Mapping[str, Any]) -> tuple[list[HardCheck], list[str]]:
    definitions = scenario.get("hard_checks")
    if not isinstance(definitions, list) or not definitions:
        raise ValueError(f"Scenario {_scenario_id(scenario)} requires a non-empty hard_checks list.")
    checks: list[HardCheck] = []
    missing_rules: list[str] = []
    for definition in definitions:
        if not isinstance(definition, Mapping):
            raise TypeError("Scenario hard_checks entries must be mappings.")
        rule_id = definition.get("rule_id")
        dotted_path = definition.get("path")
        expected = definition.get("equals")
        if not isinstance(rule_id, str) or not rule_id or not isinstance(dotted_path, str) or not dotted_path:
            raise ValueError("Hard checks require non-empty rule_id and path.")
        actual = _lookup(operations, dotted_path)
        missing = actual is _MISSING
        if missing:
            missing_rules.append(rule_id)
        evidence = {
            "fixture_evidence": definition.get("evidence", ""),
            "path": dotted_path,
            "expected": expected,
            "actual": "<missing>" if missing else actual,
        }
        checks.append(
            HardCheck(
                rule_id=rule_id,
                status="passed" if not missing and actual == expected else "failed",
                evidence=evidence,
                message=f"Expected {dotted_path} to equal {expected!r}.",
                rule_version=int(definition.get("rule_version", 1)),
            )
        )
    return checks, missing_rules


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


def _error_findings(errors: Sequence[str], missing_rules: Sequence[str]) -> list[HardCheck]:
    findings: list[HardCheck] = []
    if errors:
        findings.append(
            HardCheck(
                "EVAL-ADAPTER",
                "failed",
                {"errors": list(errors)},
                "Adapter reported errors; hard evidence is incomplete.",
            )
        )
    for rule_id in missing_rules:
        findings.append(
            HardCheck(
                f"EVAL-{rule_id}",
                "invalid",
                {"required_rule_id": rule_id},
                "Required operation path is missing.",
            )
        )
    return findings


def _trace_root(results_dir: Path) -> Path:
    root = Path(results_dir).resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise EvalSetupError(f"Cannot create results directory: {root}") from error
    if not root.is_dir():
        raise EvalSetupError(f"Cannot create results directory: {root}")
    return root


def _write_trace(
    results_dir: Path, scenario_id: str, started_at: datetime, trace: Mapping[str, Any]
) -> Path:
    """Create an audit trace exactly once; collision retries preserve concurrent evidence."""
    root = _trace_root(results_dir)
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    for _ in range(16):
        run_id = uuid.uuid4().hex
        destination = root / f"{scenario_id}-{timestamp}-{run_id}.json"
        if not destination.resolve().is_relative_to(root):
            raise ValueError("Resolved trace path escapes results_dir.")
        try:
            serialized = json.dumps(
                redact_value(dict(trace) | {"run_id": run_id}),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
        except (TypeError, ValueError) as error:
            raise EvalSetupError("Cannot serialize a standard JSON trace.") from error
        try:
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(serialized)
        except FileExistsError:
            continue
        except OSError as error:
            raise EvalSetupError(f"Cannot write trace: {destination}") from error
        return destination
    raise EvalSetupError("Could not allocate a unique trace path after 16 attempts.")


def run_scenario(
    scenario: Mapping[str, Any],
    adapter: AgentAdapter,
    *,
    results_dir: Path = _ROOT / "results",
    rubric_path: Path = DEFAULT_RUBRIC,
    workspace: Path | None = None,
    judge: JudgeAdapter | None = None,
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
    degraded = list(agent_run.degraded)
    try:
        checks, missing_rules = _hard_checks(scenario, agent_run.operations)
    except (EvalSetupError, TypeError, ValueError) as error:
        checks = [
            HardCheck(
                "EVAL-001",
                "failed",
                {"scenario_id": scenario_id},
                "Scenario hard-check configuration is invalid.",
            )
        ]
        missing_rules = []
        errors.append(f"scenario error: {error}")
    checks.extend(_error_findings(errors, missing_rules))
    soft: RubricReport | None = None
    judge_trace: Mapping[str, Any] | None = None
    if judge is None:
        degraded.append("no independent judge configured")
    else:
        try:
            judge_run = judge.judge(prompt, agent_run.response, workspace or Path.cwd())
        except Exception as error:  # noqa: BLE001 - third-party judge adapters may raise arbitrary exceptions.
            judge_run = JudgeRun({}, {"judge": judge.name}, errors=(f"judge error: {type(error).__name__}: {error}",))
        judge_run = normalize_judge_run(judge_run)
        judge_trace = {
            "name": judge.name,
            "metadata": dict(judge_run.metadata),
            "scores": dict(judge_run.scores),
            "degraded": list(judge_run.degraded),
            "errors": list(judge_run.errors),
        }
        degraded.extend(judge_run.degraded)
        if judge_run.errors:
            degraded.append("independent judge did not produce a valid score envelope")
        else:
            try:
                rubric = _load_yaml_mapping(rubric_path, "rubric")
                soft = grade_soft_rubric(judge_run, rubric)
            except (TypeError, ValueError) as error:
                degraded.append(f"rubric unavailable: {error}")
                judge_trace = dict(judge_trace) | {"rubric_error": str(error)}
    hard = grade_hard_invariants(checks)
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
        "judge": judge_trace,
        "degraded": degraded,
        "errors": errors,
    }
    trace_path = _write_trace(results_dir, scenario_id, started_at, trace)
    raw_hashes = scenario.get("scenario_semantic_hashes", {})
    semantic_hashes = dict(raw_hashes) if isinstance(raw_hashes, Mapping) else {}
    raw_mutation = scenario.get("case_mutation", {})
    case_mutation = dict(raw_mutation) if isinstance(raw_mutation, Mapping) else {}
    return EvalResult(scenario_id, hard, soft, trace_path, semantic_hashes, case_mutation)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Travel Planner behavioral evals.")
    parser.add_argument("--adapter", choices=("fixture", "codex-cli"), required=True)
    requested = parser.add_mutually_exclusive_group(required=True)
    requested.add_argument("--scenario")
    requested.add_argument("--all", action="store_true")
    parser.add_argument("--results-dir", type=Path, default=_ROOT / "results")
    parser.add_argument("--fixture-world", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--scenarios-root", type=Path, default=DEFAULT_SCENARIOS_ROOT)
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--codex-command", help="Quoted explicit command for the agent adapter.")
    parser.add_argument("--model")
    parser.add_argument("--judge-command", help="Quoted explicit command for the semantic judge.")
    parser.add_argument("--judge-model")
    return parser


def _matches_declared_outcome(result: EvalResult, scenario: Mapping[str, Any]) -> bool:
    """Accept a negative fixture only for its exact declared raw hard-failure signature."""
    expected_macro = scenario.get("expected_macro_pass", True)
    if not isinstance(expected_macro, bool) or result.hard.macro_pass != expected_macro:
        return False
    if expected_macro:
        return True
    expected = scenario.get("expected_failed_findings")
    if not isinstance(expected, list) or not expected:
        return False
    signature = {(item.rule_id, item.status) for item in result.hard.findings if item.status != "passed"}
    declared: set[tuple[str, str]] = set()
    for item in expected:
        if not isinstance(item, Mapping) or not isinstance(item.get("rule_id"), str) or not isinstance(item.get("status"), str):
            return False
        declared.add((item["rule_id"], item["status"]))
    forbidden_infrastructure = {"EVAL-ADAPTER", "EVAL-001"}
    return signature == declared and not any(rule_id in forbidden_infrastructure for rule_id, _ in signature)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        world = load_executable_fixture_world(args.fixture_world, args.scenarios_root)
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
            judge: JudgeAdapter | None = FixtureJudge(world)
        else:
            adapter = CodexCliAdapter(shlex.split(args.codex_command or ""), model=args.model)
            if not args.judge_command or not args.judge_model:
                raise ValueError("codex-cli requires --judge-command and --judge-model for semantic scoring.")
            from evals.adapters import CodexCliJudge

            judge = CodexCliJudge(shlex.split(args.judge_command), model=args.judge_model)
        results = [
            run_scenario(
                scenario,
                adapter,
                results_dir=args.results_dir,
                rubric_path=Path(scenario.get("rubric_path", args.rubric)),
                judge=judge,
            )
            for scenario in selected
        ]
    except (EvalSetupError, TypeError, ValueError) as error:
        print(f"eval error: {error}", file=sys.stderr)
        return 2
    for result in results:
        status = "PASS" if result.hard.macro_pass else "FAIL"
        if args.all:
            outcome = "EXPECTED" if _matches_declared_outcome(result, next(item for item in selected if _scenario_id(item) == result.scenario_id)) else "UNEXPECTED"
            print(f"{result.scenario_id}: {outcome} {status} ({result.trace_path})")
        else:
            print(f"{result.scenario_id}: macro {status} ({result.trace_path})")
    if args.all:
        return 0 if all(
            _matches_declared_outcome(result, next(item for item in selected if _scenario_id(item) == result.scenario_id))
            for result in results
        ) else 1
    return 0 if all(result.hard.macro_pass for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

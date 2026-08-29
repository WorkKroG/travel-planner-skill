"""Behavioral preservation and expected-negative semantics for adversarial eval fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from evals.adapters import FixtureAdapter, FixtureJudge
from evals.run import main, run_scenario
from evals.scenarios import load_scenario_case, load_scenario_world

ROOT = Path(__file__).parents[2] / "evals" / "scenarios"


def _run_case(case_id: str, tmp_path: Path):
    world = load_scenario_world(ROOT)
    case = load_scenario_case(case_id, ROOT)
    return run_scenario(
        case.scenario,
        FixtureAdapter(world),
        results_dir=tmp_path,
        rubric_path=case.rubric_path,
        judge=FixtureJudge(world),
    )


def test_weather_swap_preserves_unrelated_days_and_changes_only_target_day(tmp_path: Path) -> None:
    """A local weather fallback must not rewrite the neighbouring day during a partial rebuild."""
    result = _run_case("local-weather-swap", tmp_path)
    hashes = result.scenario_semantic_hashes

    assert result.hard.macro_pass is True
    assert hashes["day-5-before"] == hashes["day-5-after"]
    assert hashes["day-4-before"] != hashes["day-4-after"]


def test_frozen_mutation_preserves_frozen_route_and_is_an_expected_negative(tmp_path: Path) -> None:
    """A silent hotel mutation must stay a raw macro failure without corrupting frozen route state."""
    result = _run_case("frozen-mutation", tmp_path)
    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))

    assert result.hard.macro_pass is False
    assert result.scenario_semantic_hashes["frozen-route-before"] == result.scenario_semantic_hashes["frozen-route-after"]
    assert trace["grading"]["hard"]["macro_pass"] is False


def test_all_accepts_declared_negative_outcomes_without_overriding_raw_hard_gate(
    tmp_path: Path, capsys
) -> None:
    """Suite mode succeeds only when every raw result matches its fixture declaration."""
    exit_code = main(
        ["--adapter", "fixture", "--all", "--scenarios-root", str(ROOT), "--results-dir", str(tmp_path)]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "last-admission: EXPECTED FAIL" in output
    assert "frozen-mutation: EXPECTED FAIL" in output


def test_direct_negative_scenario_keeps_raw_failure_and_nonzero_exit(tmp_path: Path, capsys) -> None:
    """Selecting a negative fixture directly must never convert its failed hard gate into success."""
    exit_code = main(
        [
            "--adapter",
            "fixture",
            "--scenario",
            "last-admission",
            "--scenarios-root",
            str(ROOT),
            "--results-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 1
    assert "last-admission: macro FAIL" in capsys.readouterr().out
    trace = next(tmp_path.glob("last-admission-*.json"))
    assert json.loads(trace.read_text(encoding="utf-8"))["grading"]["hard"]["macro_pass"] is False

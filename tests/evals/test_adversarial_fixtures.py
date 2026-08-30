"""Behavioral preservation and expected-negative semantics for adversarial eval fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from evals.adapters import FixtureAdapter
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
    )


def test_weather_swap_preserves_unrelated_days_and_changes_only_target_day(tmp_path: Path) -> None:
    """A local weather fallback must not rewrite the neighbouring day during a partial rebuild."""
    result = _run_case("local-weather-swap", tmp_path)
    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    mutation = trace["operations"]["weather_change"]
    hashes = mutation["semantic_hashes"]

    assert result.hard.macro_pass is True
    assert hashes["day-5-before"] == hashes["day-5-after"]
    assert hashes["day-4-before"] != hashes["day-4-after"]
    assert mutation["impact_targets"] == ["day:day-4", "outputs:all"]


def test_frozen_mutation_preserves_frozen_route_and_is_an_expected_negative(tmp_path: Path) -> None:
    """A silent hotel mutation must stay a raw macro failure without corrupting frozen route state."""
    result = _run_case("frozen-mutation", tmp_path)
    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    transition = trace["operations"]["route_transition"]

    assert result.hard.macro_pass is False
    assert transition["rejected"] is True
    assert transition["route_before"] == transition["route_after"]
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


def test_expected_negative_rejects_an_adapter_crash_and_unrelated_failures(tmp_path: Path, capsys) -> None:
    """A negative fixture is expected only for its declared failed signature, never an adapter outage."""
    command = f'{sys.executable} -c "import sys; sys.exit(1)"'
    exit_code = main(
        [
            "--adapter", "codex-cli", "--all", "--scenarios-root", str(ROOT), "--results-dir", str(tmp_path),
            "--codex-command", command, "--model", "fixture-crash", "--judge-command", command, "--judge-model", "judge",
        ]
    )

    assert exit_code == 1
    assert "last-admission: UNEXPECTED FAIL" in capsys.readouterr().out

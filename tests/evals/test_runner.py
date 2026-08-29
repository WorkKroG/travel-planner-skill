from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from evals.adapters import CodexCliAdapter, FixtureAdapter
from evals.run import load_fixture_world, main, run_scenario

FIXTURE_WORLD = Path(__file__).parents[2] / "evals" / "fixture-world" / "base.yaml"
RUBRIC = Path(__file__).parents[2] / "evals" / "rubrics" / "quality.yaml"


def test_trace_records_versions_prompt_operations_and_grading(tmp_path: Path) -> None:
    """A trace missing audit material must fail this contract check."""
    world = load_fixture_world(FIXTURE_WORLD)
    scenario = world["scenarios"]["harness-smoke"]

    result = run_scenario(
        scenario,
        FixtureAdapter(world),
        results_dir=tmp_path,
        rubric_path=RUBRIC,
    )
    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))

    assert result.hard.macro_pass is True
    assert trace["schema_version"] == 1
    assert trace["scenario_id"] == "harness-smoke"
    assert {"adapter", "adapter_metadata", "prompt_version", "started_at", "prompt"} <= trace.keys()
    assert {"response", "operations", "grading", "degraded", "errors"} <= trace.keys()
    assert trace["adapter"] == "fixture"
    assert trace["degraded"] == []
    assert trace["grading"]["hard"]["macro_pass"] is True


def test_last_admission_mutation_fails_the_macro_gate_and_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Removing last-admission detection must make the deliberate mutation fail."""
    exit_code = main(
        [
            "--adapter",
            "fixture",
            "--scenario",
            "last-admission-mutation",
            "--results-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 1
    assert "macro FAIL" in capsys.readouterr().out
    trace = next(tmp_path.glob("last-admission-mutation-*.json"))
    assert json.loads(trace.read_text(encoding="utf-8"))["grading"]["hard"]["macro_pass"] is False


def test_unknown_scenario_is_a_deterministic_cli_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A typo must not silently run another scenario."""
    exit_code = main(
        ["--adapter", "fixture", "--scenario", "does-not-exist", "--results-dir", str(tmp_path)]
    )

    assert exit_code == 2
    assert "Unknown scenario: does-not-exist" in capsys.readouterr().err


def test_fixture_adapter_is_offline_and_returns_the_selected_fixture() -> None:
    """Fixture mode must use the declared world, not a network or model fallback."""
    world = yaml.safe_load(FIXTURE_WORLD.read_text(encoding="utf-8"))
    run = FixtureAdapter(world).run("SCENARIO_ID: harness-smoke", Path.cwd())

    assert run.metadata["mode"] == "offline"
    assert run.operations["checks"]["OPS-011"]["status"] == "identified"


def test_codex_adapter_requires_an_explicit_command() -> None:
    """An absent command must fail at setup rather than become fixture mode."""
    with pytest.raises(ValueError, match="explicit command"):
        CodexCliAdapter(command=())


def test_missing_rubric_is_recorded_in_a_trace_instead_of_disappearing(tmp_path: Path) -> None:
    """A bad rubric path must leave an inspectable failed run, not raise before tracing."""
    world = load_fixture_world(FIXTURE_WORLD)
    result = run_scenario(
        world["scenarios"]["harness-smoke"],
        FixtureAdapter(world),
        results_dir=tmp_path,
        rubric_path=tmp_path / "missing-rubric.yaml",
    )

    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    assert result.soft is None
    assert result.hard.macro_pass is False
    assert trace["errors"][0].startswith("rubric error: Cannot load rubric:")

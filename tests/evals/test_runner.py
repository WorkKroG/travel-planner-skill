from __future__ import annotations

import importlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from evals.adapters import (
    CodexCliAdapter,
    CodexCliJudge,
    FixtureAdapter,
    FixtureJudge,
    _safe_command,
)
from evals.redaction import redact_text
from evals.run import load_fixture_world, main, run_scenario
from evals.types import JudgeRun

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
        judge=FixtureJudge(world),
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
    assert trace["grading"]["soft"]["score"] == 20


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


def test_fixture_adapter_deep_copies_nested_operations() -> None:
    """Mutating one fixture run must not poison the next deterministic run."""
    world = load_fixture_world(FIXTURE_WORLD)
    adapter = FixtureAdapter(world)
    first = adapter.run("SCENARIO_ID: harness-smoke", Path.cwd())
    first.operations["checks"]["OPS-011"]["status"] = "mutated"

    second = adapter.run("SCENARIO_ID: harness-smoke", Path.cwd())

    assert second.operations["checks"]["OPS-011"]["status"] == "identified"


def test_codex_adapter_requires_an_explicit_command() -> None:
    """An absent command must fail at setup rather than become fixture mode."""
    with pytest.raises(ValueError, match="explicit command"):
        CodexCliAdapter(command=(), model="codex-test")


def test_codex_adapter_requires_non_empty_model_and_cli_rejects_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A real-agent trace with model=null is not admissible evidence."""
    with pytest.raises(ValueError, match="non-empty model"):
        CodexCliAdapter(command=(sys.executable, "-c", "print('{}')"), model=None)

    exit_code = main(
        [
            "--adapter",
            "codex-cli",
            "--scenario",
            "harness-smoke",
            "--codex-command",
            sys.executable,
            "--results-dir",
            str(tmp_path),
        ]
    )
    assert exit_code == 2
    assert "non-empty model" in capsys.readouterr().err


def test_missing_rubric_is_recorded_in_a_trace_instead_of_disappearing(tmp_path: Path) -> None:
    """A bad rubric path must leave an inspectable failed run, not raise before tracing."""
    world = load_fixture_world(FIXTURE_WORLD)
    result = run_scenario(
        world["scenarios"]["harness-smoke"],
        FixtureAdapter(world),
        results_dir=tmp_path,
        rubric_path=tmp_path / "missing-rubric.yaml",
        judge=FixtureJudge(world),
    )

    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    assert result.soft is None
    assert result.hard.macro_pass is True
    assert trace["degraded"][-1].startswith("rubric unavailable: Cannot load rubric:")


def test_adapter_crash_and_missing_path_never_match_a_null_expectation(tmp_path: Path) -> None:
    """Missing operations are distinct from a present JSON null after an adapter crash."""

    class CrashingAdapter:
        name = "crashing"

        def run(self, prompt: str, workspace: Path):
            del prompt, workspace
            raise RuntimeError("token=adapter-secret")

    scenario = {
        "id": "null-missing",
        "prompt_version": "v1",
        "prompt": "check this",
        "hard_checks": [{"rule_id": "OPS-011", "path": "must.exist", "equals": None}],
    }

    result = run_scenario(scenario, CrashingAdapter(), results_dir=tmp_path)

    assert result.hard.macro_pass is False
    assert {item.rule_id for item in result.hard.findings} >= {"OPS-011", "EVAL-ADAPTER", "EVAL-OPS-011"}
    assert next(item for item in result.hard.findings if item.rule_id == "OPS-011").status == "failed"


def test_valid_structured_command_envelope_can_pass_hard_checks(tmp_path: Path) -> None:
    """A real command emitting the required envelope must expose its operations to grading."""
    envelope = json.dumps(
        {
            "schema_version": 1,
            "response": "identified",
            "operations": {"checks": {"OPS-011": {"status": "identified"}}},
            "degraded": [],
            "errors": [],
        }
    )
    command = (sys.executable, "-c", f"print({envelope!r})")
    scenario = {
        "id": "command-envelope",
        "prompt_version": "v1",
        "prompt": "check this",
        "hard_checks": [{"rule_id": "OPS-011", "path": "checks.OPS-011.status", "equals": "identified"}],
    }

    result = run_scenario(
        scenario,
        CodexCliAdapter(command, model="codex-test"),
        results_dir=tmp_path,
    )

    assert result.hard.macro_pass is True
    assert result.soft is None
    assert "no independent judge configured" in json.loads(result.trace_path.read_text())["degraded"]


def test_malformed_successful_command_stdout_is_an_explicit_macro_failure(tmp_path: Path) -> None:
    """A command exit code of zero cannot hide a malformed agent-result envelope."""
    scenario = {
        "id": "malformed-command",
        "prompt_version": "v1",
        "prompt": "check this",
        "hard_checks": [{"rule_id": "OPS-011", "path": "checks.OPS-011.status", "equals": "identified"}],
    }
    result = run_scenario(
        scenario,
        CodexCliAdapter((sys.executable, "-c", "print('not json')"), model="codex-test"),
        results_dir=tmp_path,
    )

    assert result.hard.macro_pass is False
    assert any(item.rule_id == "EVAL-ADAPTER" for item in result.hard.findings)
    assert "result envelope error" in json.loads(result.trace_path.read_text())["errors"][0]


def test_independent_judge_ignores_agent_self_scoring(tmp_path: Path) -> None:
    """Changing agent operations.rubric must not change independently judged soft score."""
    agent_envelope = json.dumps(
        {
            "schema_version": 1,
            "response": "identified",
            "operations": {
                "checks": {"OPS-011": {"status": "identified"}},
                "rubric": {"readability": 999},
            },
            "degraded": [],
            "errors": [],
        }
    )
    judge_envelope = json.dumps(
        {
            "schema_version": 1,
            "scores": {
                "skeleton_distinctness": 1,
                "tradeoffs": 1,
                "pacing": 1,
                "backup_usefulness": 1,
                "readability": 1,
                "calibrated_uncertainty": 1,
            },
            "degraded": [],
            "errors": [],
        }
    )
    scenario = {
        "id": "independent-judge",
        "prompt_version": "v1",
        "prompt": "check this",
        "hard_checks": [{"rule_id": "OPS-011", "path": "checks.OPS-011.status", "equals": "identified"}],
    }
    result = run_scenario(
        scenario,
        CodexCliAdapter((sys.executable, "-c", f"print({agent_envelope!r})"), model="codex-test"),
        results_dir=tmp_path,
        judge=CodexCliJudge(
            (sys.executable, "-c", f"print({judge_envelope!r})"), model="judge-test"
        ),
    )

    assert result.hard.macro_pass is True
    assert result.soft is not None
    assert result.soft.score == 6


@pytest.mark.parametrize("scenario_id", ["../escape", "/absolute", "two/parts"])
def test_unsafe_scenario_ids_are_rejected_before_trace_write(tmp_path: Path, scenario_id: str) -> None:
    """Scenario IDs must be safe filenames, never user-controlled paths."""
    scenario = {
        "id": scenario_id,
        "prompt_version": "v1",
        "prompt": "check this",
        "hard_checks": [{"rule_id": "OPS-011", "path": "checks.OPS-011.status", "equals": "identified"}],
    }
    world = load_fixture_world(FIXTURE_WORLD)
    with pytest.raises(ValueError, match="safe filename"):
        run_scenario(scenario, FixtureAdapter(world), results_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_same_frozen_clock_produces_distinct_exclusive_trace_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two runs at the same clock instant must retain two independent audit files."""
    run_module = importlib.import_module("evals.run")

    class FrozenDatetime:
        @classmethod
        def now(cls, timezone: object) -> datetime:
            del timezone
            return datetime(2026, 8, 29, 12, tzinfo=UTC)

    monkeypatch.setattr(run_module, "datetime", FrozenDatetime)
    world = load_fixture_world(FIXTURE_WORLD)
    first = run_scenario(world["scenarios"]["harness-smoke"], FixtureAdapter(world), results_dir=tmp_path)
    second = run_scenario(world["scenarios"]["harness-smoke"], FixtureAdapter(world), results_dir=tmp_path)

    assert first.trace_path != second.trace_path
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_trace_allocation_retries_an_existing_run_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A rare UUID collision must retry rather than overwrite or lose the second trace."""
    run_module = importlib.import_module("evals.run")
    ids = iter(("fixed", "fixed", "replacement"))
    monkeypatch.setattr(run_module.uuid, "uuid4", lambda: type("RunId", (), {"hex": next(ids)})())

    class FrozenDatetime:
        @classmethod
        def now(cls, timezone: object) -> datetime:
            del timezone
            return datetime(2026, 8, 29, 12, tzinfo=UTC)

    monkeypatch.setattr(run_module, "datetime", FrozenDatetime)
    world = load_fixture_world(FIXTURE_WORLD)

    first = run_scenario(world["scenarios"]["harness-smoke"], FixtureAdapter(world), results_dir=tmp_path)
    second = run_scenario(world["scenarios"]["harness-smoke"], FixtureAdapter(world), results_dir=tmp_path)

    assert first.trace_path != second.trace_path
    assert "replacement" in second.trace_path.name


def test_trace_recursively_redacts_secrets_and_subprocess_diagnostics(tmp_path: Path) -> None:
    """Trace evidence may be useful, but secrets and passport/card-like values must never persist."""
    scenario = {
        "id": "redaction",
        "prompt_version": "v1",
        "prompt": "Authorization: Bearer prompt-secret passport AB1234567 card 4111 1111 1111 1111",
        "hard_checks": [{"rule_id": "OPS-011", "path": "checks.OPS-011.status", "equals": "identified"}],
    }
    command = (
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('token=error-secret Authorization: Bearer stderr-secret'); sys.exit(2)",
        "--api-key=command-secret",
    )

    class SensitiveJudge:
        name = "sensitive-judge"

        def judge(self, prompt: str, response: str, workspace: Path) -> JudgeRun:
            del prompt, response, workspace
            return JudgeRun(
                {},
                {"Authorization": "Bearer judge-secret", "passport": "AB1234567"},
                errors=("password=judge-password",),
            )

    result = run_scenario(
        scenario,
        CodexCliAdapter(command, model="codex-test"),
        results_dir=tmp_path,
        judge=SensitiveJudge(),
    )

    trace_text = result.trace_path.read_text(encoding="utf-8")
    for secret in (
        "prompt-secret",
        "AB1234567",
        "4111 1111 1111 1111",
        "error-secret",
        "stderr-secret",
        "command-secret",
        "judge-secret",
        "judge-password",
    ):
        assert secret not in trace_text
    assert "<redacted>" in trace_text


def test_redaction_masks_bare_bearer_and_split_command_credentials(tmp_path: Path) -> None:
    """Separate command arguments must retain safe flags while hiding adjacent credentials."""
    command = (
        "codex",
        "--token",
        "split-token",
        "--api-key",
        "split-key",
        "--password",
        "split-password",
        "--header",
        "Authorization:",
        "Bearer",
        "split-header-secret",
        "--verbose",
    )

    safe = _safe_command(command)

    assert safe == [
        "codex",
        "--token",
        "<redacted>",
        "--api-key",
        "<redacted>",
        "--password",
        "<redacted>",
        "--header",
        "Authorization:",
        "Bearer",
        "<redacted>",
        "--verbose",
    ]
    assert redact_text("Bearer bare-secret") == "Bearer <redacted>"

    scenario = {
        "id": "bare-bearer",
        "prompt_version": "v1",
        "prompt": "Bearer prompt-bearer-secret",
        "hard_checks": [{"rule_id": "OPS-011", "path": "checks.OPS-011.status", "equals": "identified"}],
    }
    result = run_scenario(
        scenario,
        CodexCliAdapter(
            (sys.executable, "-c", "import sys; sys.stderr.write('Bearer error-bearer-secret'); sys.exit(2)", *command[1:]),
            model="codex-test",
        ),
        results_dir=tmp_path,
    )
    trace = result.trace_path.read_text(encoding="utf-8")
    for secret in ("prompt-bearer-secret", "error-bearer-secret", "split-token", "split-key", "split-password", "split-header-secret"):
        assert secret not in trace
    assert "--verbose" in trace


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_judge_envelope_is_soft_only_error_with_standard_json_trace(
    tmp_path: Path, constant: str
) -> None:
    """A non-finite judge value degrades soft scoring without changing a valid macro result."""
    agent_envelope = json.dumps(
        {
            "schema_version": 1,
            "response": "identified",
            "operations": {"checks": {"OPS-011": {"status": "identified"}}},
            "degraded": [],
            "errors": [],
        }
    )
    scores = ", ".join(
        f'"{name}": {constant if name == "readability" else "1"}'
        for name in (
            "skeleton_distinctness",
            "tradeoffs",
            "pacing",
            "backup_usefulness",
            "readability",
            "calibrated_uncertainty",
        )
    )
    judge_envelope = f'{{"schema_version": 1, "scores": {{{scores}}}, "degraded": [], "errors": []}}'
    scenario = {
        "id": f"nonfinite-{constant.lower().replace('-', 'minus-')}",
        "prompt_version": "v1",
        "prompt": "check this",
        "hard_checks": [{"rule_id": "OPS-011", "path": "checks.OPS-011.status", "equals": "identified"}],
    }
    result = run_scenario(
        scenario,
        CodexCliAdapter((sys.executable, "-c", f"print({agent_envelope!r})"), model="codex-test"),
        results_dir=tmp_path,
        judge=CodexCliJudge((sys.executable, "-c", f"print({judge_envelope!r})"), model="judge-test"),
    )

    trace_text = result.trace_path.read_text(encoding="utf-8")
    assert result.hard.macro_pass is True
    assert result.soft is None
    assert "independent judge did not produce a valid score envelope" in json.loads(trace_text)["degraded"]
    json.loads(trace_text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-standard")))


def test_file_results_dir_is_a_concise_cli_setup_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Trace setup errors must use the eval CLI diagnostic path rather than a traceback."""
    results_file = tmp_path / "results-file"
    results_file.write_text("not a directory", encoding="utf-8")

    exit_code = main(
        ["--adapter", "fixture", "--scenario", "harness-smoke", "--results-dir", str(results_file)]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err.startswith("eval error: Cannot create results directory:")
    assert "Traceback" not in captured.err

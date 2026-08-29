"""Offline evals prove hard constraints and defer semantic review to Codex."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import yaml

from evals.adapters import CodexCliAdapter, CodexCliJudge, FixtureAdapter
from evals.run import load_fixture_world, main, run_scenario
from evals.scenarios import load_scenario_case

ROOT = Path(__file__).parents[2] / "evals" / "scenarios"
DIMENSIONS = (
    "skeleton_distinctness",
    "tradeoffs",
    "pacing",
    "backup_usefulness",
    "readability",
    "calibrated_uncertainty",
)
FIXTURE_WORLD = Path(__file__).parents[2] / "evals" / "fixture-world" / "base.yaml"
RUBRIC = Path(__file__).parents[2] / "evals" / "rubrics" / "quality.yaml"


def test_fixture_cli_records_hard_only_result_and_online_review_receipt(
    tmp_path: Path, capsys
) -> None:
    """Adding an offline prose scorer must make this receipt contract fail."""
    exit_code = main(
        [
            "--adapter",
            "fixture",
            "--scenario",
            "japan-autumn",
            "--results-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Soft review: NOT RUN offline; run the online Codex judge" in output
    trace_path = next(tmp_path.glob("japan-autumn-*.json"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["grading"]["hard"]["macro_pass"] is True
    assert trace["grading"]["soft"] is None
    assert trace["judge"] is None
    assert trace["soft_review"] == {
        "status": "requires_online_review",
        "reason": "Soft qualities are not evaluated in offline fixture mode.",
        "dimensions": list(DIMENSIONS),
    }


def test_scenario_rubric_is_online_criteria_not_offline_phrase_matching(
    tmp_path: Path,
) -> None:
    """Requiring phrase anchors or claims in fixture mode must fail this contract."""
    root = tmp_path / "scenarios"
    shutil.copytree(ROOT, root)
    rubric_path = root / "japan-autumn" / "rubric.yaml"
    rubric_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "review_mode": "online-required",
                "dimensions": [
                    {
                        "id": dimension,
                        "max_score": 4,
                        "criterion": f"Review {dimension.replace('_', ' ')} in context.",
                    }
                    for dimension in DIMENSIONS
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    case = load_scenario_case("japan-autumn", root)

    assert case.scenario["online_review_required"] is True
    assert "fixture_rubric" not in case.scenario


def test_fixture_adapter_never_invokes_a_soft_judge_even_when_one_is_passed(
    tmp_path: Path,
) -> None:
    """The public runner must preserve the hard-only fixture boundary."""
    class ExplodingJudge:
        name = "must-not-run"

        def judge(self, prompt: str, response: str, workspace: Path):
            del prompt, response, workspace
            raise AssertionError("fixture mode invoked a semantic judge")

    world = load_fixture_world(FIXTURE_WORLD)
    result = run_scenario(
        world["scenarios"]["harness-smoke"],
        FixtureAdapter(world),
        results_dir=tmp_path,
        judge=ExplodingJudge(),
    )

    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    assert result.soft is None
    assert trace["judge"] is None
    assert trace["soft_review"]["status"] == "requires_online_review"


def test_online_codex_judge_receives_the_validated_rubric_criteria(
    tmp_path: Path,
) -> None:
    """Online criteria must affect the judge input rather than only cap its output."""
    agent_envelope = json.dumps(
        {
            "schema_version": 1,
            "response": "route response",
            "operations": {"checks": {"OPS-011": {"status": "identified"}}},
            "degraded": [],
            "errors": [],
        }
    )
    judge_code = (
        "import json,sys; p=json.load(sys.stdin); "
        "ok=p['rubric']['review_mode']=='online-required' and "
        "all(d.get('criterion') for d in p['rubric']['dimensions']); "
        f"dims={list(DIMENSIONS)!r}; score=4 if ok else 0; "
        "print(json.dumps({'schema_version':1,'scores':{d:score for d in dims},"
        "'degraded':[],'errors':[]}))"
    )
    scenario = {
        "id": "online-rubric",
        "prompt_version": "v1",
        "prompt": "Review the route.",
        "hard_checks": [
            {
                "rule_id": "OPS-011",
                "path": "checks.OPS-011.status",
                "equals": "identified",
            }
        ],
    }

    result = run_scenario(
        scenario,
        CodexCliAdapter(
            (sys.executable, "-c", f"print({agent_envelope!r})"),
            model="agent-test",
        ),
        results_dir=tmp_path,
        rubric_path=RUBRIC,
        judge=CodexCliJudge(
            (sys.executable, "-c", judge_code),
            model="judge-test",
        ),
    )

    assert result.soft is not None
    assert result.soft.score == result.soft.max_score == 24


def test_reference_evaluator_emits_only_a_neutral_offline_diagnostic(
    tmp_path: Path,
) -> None:
    """Offline evidence may be structured, but must not imitate a model-written answer."""
    exit_code = main(
        [
            "--adapter",
            "fixture",
            "--scenario",
            "booking-timezone",
            "--results-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    trace_path = next(tmp_path.glob("booking-timezone-*.json"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["response"] == (
        "Offline fixture computed deterministic hard evidence only; "
        "soft qualities require online Codex review."
    )
    assert all(
        label not in trace["response"]
        for label in ("Finding:", "Evidence:", "Action:", "Backup:", "Uncertainty:")
    )


def test_invalid_online_rubric_is_rejected_before_the_judge_runs(
    tmp_path: Path,
) -> None:
    """The public runner must enforce the same online rubric contract as scenarios."""
    invalid_rubric = tmp_path / "invalid-rubric.yaml"
    invalid_rubric.write_text(
        "version: 1\ndimensions:\n  - id: readability\n    max_score: 4\n",
        encoding="utf-8",
    )
    agent_envelope = json.dumps(
        {
            "schema_version": 1,
            "response": "route response",
            "operations": {"checks": {"OPS-011": {"status": "identified"}}},
            "degraded": [],
            "errors": [],
        }
    )
    calls: list[str] = []

    class ProbeJudge:
        name = "probe-judge"

        def judge(
            self,
            prompt: str,
            response: str,
            workspace: Path,
            rubric: object,
        ):
            del prompt, response, workspace, rubric
            calls.append("called")
            raise AssertionError("invalid rubric reached judge")

    scenario = {
        "id": "invalid-online-rubric",
        "prompt_version": "v1",
        "prompt": "Review the route.",
        "hard_checks": [
            {
                "rule_id": "OPS-011",
                "path": "checks.OPS-011.status",
                "equals": "identified",
            }
        ],
    }
    result = run_scenario(
        scenario,
        CodexCliAdapter(
            (sys.executable, "-c", f"print({agent_envelope!r})"),
            model="agent-test",
        ),
        results_dir=tmp_path / "results",
        rubric_path=invalid_rubric,
        judge=ProbeJudge(),
    )

    trace = json.loads(result.trace_path.read_text(encoding="utf-8"))
    assert calls == []
    assert result.soft is None
    assert trace["judge"]["name"] == "probe-judge"
    assert "rubric_error" in trace["judge"]
    assert trace["degraded"][-1].startswith("rubric unavailable:")

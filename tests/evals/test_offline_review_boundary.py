"""Offline evals prove hard constraints and defer semantic review to Codex."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from evals.run import main
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


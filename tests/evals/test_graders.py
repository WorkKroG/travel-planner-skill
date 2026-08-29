from __future__ import annotations

import math

import pytest

from evals.graders import grade_hard_invariants, grade_soft_rubric
from evals.types import HardCheck, JudgeRun


def test_one_hard_failure_fails_the_whole_scenario() -> None:
    """A regression that treats hard checks as score deductions must fail here."""
    report = grade_hard_invariants(
        [
            HardCheck("CAL-001", "passed", {"date": "2026-11-02"}),
            HardCheck("OPS-011", "failed", {"last_admission": "missed"}),
        ]
    )

    assert report.macro_pass is False
    assert [(finding.rule_id, finding.status) for finding in report.findings] == [
        ("CAL-001", "passed"),
        ("OPS-011", "failed"),
    ]
    assert report.findings[1].evidence == {"last_admission": "missed"}


def test_soft_rubric_uses_the_independent_judge_result() -> None:
    """A high self-score in an agent operation must not be the rubric input."""
    hard = grade_hard_invariants([HardCheck("OPS-011", "failed", {"actual": "ignored"})])
    rubric = grade_soft_rubric(
        JudgeRun({"clarity": 4, "tradeoffs": 3}, {"judge": "fixture"}),
        {
            "version": 1,
            "dimensions": [
                {"id": "clarity", "max_score": 4},
                {"id": "tradeoffs", "max_score": 3},
            ],
        },
    )

    assert hard.macro_pass is False
    assert rubric.score == 7
    assert rubric.max_score == 7


def test_malformed_rubric_value_becomes_a_deterministic_zero() -> None:
    """A non-numeric judge value must not crash or inflate the score."""
    report = grade_soft_rubric(
        JudgeRun({"clarity": "excellent"}, {"judge": "fixture"}),
        {"version": 1, "dimensions": [{"id": "clarity", "max_score": 4}]},
    )

    assert report.score == 0
    assert report.items[0].status == "invalid"


@pytest.mark.parametrize("non_finite", [math.nan, math.inf, -math.inf])
def test_non_finite_judge_scores_and_rubric_limits_are_rejected(non_finite: float) -> None:
    """NaN and infinities are invalid JSON values, never soft-rubric inputs."""
    with pytest.raises(ValueError, match="finite"):
        grade_soft_rubric(
            JudgeRun({"clarity": non_finite}, {"judge": "fixture"}),
            {"version": 1, "dimensions": [{"id": "clarity", "max_score": 4}]},
        )
    with pytest.raises(ValueError, match="finite"):
        grade_soft_rubric(
            JudgeRun({"clarity": 1}, {"judge": "fixture"}),
            {"version": 1, "dimensions": [{"id": "clarity", "max_score": non_finite}]},
        )

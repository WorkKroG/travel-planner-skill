from __future__ import annotations

from evals.graders import grade_hard_invariants, grade_soft_rubric
from evals.types import HardCheck


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


def test_soft_rubric_is_scored_separately_from_hard_findings() -> None:
    """A high soft score must never make a failed hard gate pass."""
    hard = grade_hard_invariants([HardCheck("OPS-011", "failed", {"actual": "ignored"})])
    rubric = grade_soft_rubric(
        {"rubric": {"clarity": 4, "tradeoffs": 3}},
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
        {"rubric": {"clarity": "excellent"}},
        {"version": 1, "dimensions": [{"id": "clarity", "max_score": 4}]},
    )

    assert report.score == 0
    assert report.items[0].status == "invalid"

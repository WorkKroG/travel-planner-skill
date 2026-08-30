"""Deterministic macro and soft-rubric graders; soft scores never change hard gates."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from .types import Finding, GradeReport, HardCheck, JudgeRun, RubricItem, RubricReport


def grade_hard_invariants(checks: Sequence[HardCheck]) -> GradeReport:
    """Apply the macro gate: every hard check must pass."""
    findings = tuple(
        Finding(
            rule_id=check.rule_id,
            status=check.status,
            evidence=dict(check.evidence),
            message=check.message,
        )
        for check in checks
    )
    return GradeReport(macro_pass=all(item.status == "passed" for item in findings), findings=findings)


def _rubric_mapping(rubric: Mapping[str, Any] | Path) -> Mapping[str, Any]:
    if isinstance(rubric, Path):
        loaded = yaml.safe_load(rubric.read_text(encoding="utf-8"))
        if not isinstance(loaded, Mapping):
            raise TypeError(f"Rubric must be a YAML mapping: {rubric}")
        return loaded
    return rubric


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        raise ValueError("Rubric scores and limits must be finite.")
    return value


def grade_soft_rubric(judge_result: JudgeRun, rubric: Mapping[str, Any] | Path) -> RubricReport:
    """Score declared qualitative dimensions without touching the hard-gate decision."""
    rubric_data = _rubric_mapping(rubric)
    dimensions = rubric_data.get("dimensions")
    if not isinstance(dimensions, list):
        raise TypeError("Rubric requires a dimensions list.")
    values = judge_result.scores

    items: list[RubricItem] = []
    for dimension in dimensions:
        if not isinstance(dimension, Mapping):
            raise TypeError("Rubric dimensions must be mappings.")
        rubric_id = dimension.get("id")
        maximum = _number(dimension.get("max_score"))
        if not isinstance(rubric_id, str) or not rubric_id or maximum is None or maximum < 0:
            raise ValueError("Each rubric dimension needs id and non-negative max_score.")
        raw = values.get(rubric_id)
        numeric = _number(raw)
        if raw is None:
            items.append(RubricItem(rubric_id, 0, maximum, "missing"))
        elif numeric is None:
            items.append(RubricItem(rubric_id, 0, maximum, "invalid"))
        else:
            items.append(RubricItem(rubric_id, min(max(numeric, 0), maximum), maximum, "scored"))
    return RubricReport(
        version=int(rubric_data.get("version", 1)),
        score=sum(item.score for item in items),
        max_score=sum(item.max_score for item in items),
        items=tuple(items),
    )

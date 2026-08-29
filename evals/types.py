"""Small, serializable public types shared by eval adapters, graders, and runner."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

CheckStatus = Literal["passed", "failed", "invalid"]
RubricStatus = Literal["scored", "missing", "invalid"]


@dataclass(frozen=True)
class AgentRun:
    """One adapter response and the explicit operations it reports."""

    response: str
    operations: Mapping[str, Any]
    metadata: Mapping[str, Any]
    degraded: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class JudgeRun:
    """Independent semantic-judge result; it cannot change hard-gate outcomes."""

    scores: Mapping[str, Any]
    metadata: Mapping[str, Any]
    degraded: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class HardCheck:
    """A completed invariant check with stable evidence for human review."""

    rule_id: str
    status: CheckStatus
    evidence: Mapping[str, Any]
    message: str = ""
    rule_version: int = 1


@dataclass(frozen=True)
class Finding:
    """Serialized hard-gate outcome. Status and evidence remain independent of prose."""

    rule_id: str
    status: CheckStatus
    evidence: Mapping[str, Any]
    message: str
    rule_version: int = 1


@dataclass(frozen=True)
class GradeReport:
    macro_pass: bool
    findings: tuple[Finding, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"macro_pass": self.macro_pass, "findings": [asdict(item) for item in self.findings]}


@dataclass(frozen=True)
class RubricItem:
    rubric_id: str
    score: int | float
    max_score: int | float
    status: RubricStatus


@dataclass(frozen=True)
class RubricReport:
    version: int
    score: int | float
    max_score: int | float
    items: tuple[RubricItem, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "score": self.score,
            "max_score": self.max_score,
            "items": [asdict(item) for item in self.items],
        }


@dataclass(frozen=True)
class EvalResult:
    scenario_id: str
    hard: GradeReport
    soft: RubricReport | None
    trace_path: Path
    scenario_semantic_hashes: Mapping[str, str]
    case_mutation: Mapping[str, Any]

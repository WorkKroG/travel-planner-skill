"""Core challenge protocols, stable ordering, and macro gating."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal, Protocol

from ..evidence import Finding
from ..state import TripState

ChallengeStage = Literal["skeleton", "detailed"]
_SEVERITY_ORDER = {"blocking": 0, "warning": 1, "note": 2}


class DuplicateRuleError(ValueError):
    """Raised when a challenge catalog contains a duplicate stable rule ID."""


class Rule(Protocol):
    rule_id: str
    version: int
    stages: frozenset[ChallengeStage]

    def evaluate(self, ctx: ChallengeContext) -> Iterable[Finding]: ...


@dataclass
class ChallengeContext:
    state: TripState
    stage: ChallengeStage
    now: datetime
    facts: Mapping[str, Any]


@dataclass(frozen=True)
class ChallengeReport:
    stage: ChallengeStage
    evaluated_at: datetime
    findings: tuple[Finding, ...]
    rule_versions: tuple[tuple[str, int], ...]

    @property
    def hard_pass(self) -> bool:
        return all(finding.severity != "blocking" for finding in self.findings)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "evaluated_at": self.evaluated_at.isoformat(),
            "hard_pass": self.hard_pass,
            "rule_versions": [
                {"rule_id": rule_id, "version": version}
                for rule_id, version in self.rule_versions
            ],
            "findings": [asdict(finding) for finding in self.findings],
        }


def _finding_key(finding: Finding) -> tuple[int, str, tuple[str, ...]]:
    return (
        _SEVERITY_ORDER[finding.severity],
        finding.rule_id,
        finding.affected_ids,
    )


def run_challenge(
    state: TripState,
    stage: ChallengeStage,
    now: datetime,
    *,
    rules: Iterable[Rule] | None = None,
    facts: Mapping[str, Any] | None = None,
) -> ChallengeReport:
    """Evaluate selected rules and preserve hard blockers as a macro gate."""
    if stage not in {"skeleton", "detailed"}:
        raise ValueError(f"Unknown challenge stage: {stage}")
    if rules is None:
        from .catalog import registered_rules

        selected_rules = registered_rules()
    else:
        selected_rules = tuple(rules)
    ids = [rule.rule_id for rule in selected_rules]
    if len(ids) != len(set(ids)):
        raise DuplicateRuleError("Challenge rule IDs must be unique.")
    active_rules = tuple(rule for rule in selected_rules if stage in rule.stages)
    context = ChallengeContext(state=state, stage=stage, now=now, facts=facts or {})
    findings = tuple(
        sorted(
            (finding for rule in active_rules for finding in rule.evaluate(context)),
            key=_finding_key,
        )
    )
    versions = tuple(sorted((rule.rule_id, rule.version) for rule in active_rules))
    return ChallengeReport(stage, now, findings, versions)


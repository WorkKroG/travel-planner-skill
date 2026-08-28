"""Central registry for versioned challenge rules."""

from __future__ import annotations

from dataclasses import dataclass

from ..evidence import critical_evidence_findings
from .base import ChallengeContext, ChallengeStage, Rule
from .calendar import DstTransitionRule, OperatingDateRule, OvernightRolloverRule, WeekdayRule
from .logistics import (
    DoorToDoorRule,
    HotelWindowRule,
    LastAdmissionRule,
    LastServiceRule,
    LuggageStorageRule,
    MinimumConnectionRule,
    OperatingHoursRule,
    OvernightAccommodationRule,
    RequiredBufferRule,
    ScheduleHorizonRule,
)


@dataclass(frozen=True)
class EvidenceGateRule:
    rule_id: str = "EVID-001"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return critical_evidence_findings(ctx.state, ctx.now)


def registered_rules() -> tuple[Rule, ...]:
    """Return the stable built-in catalog in rule-ID order."""
    rules: tuple[Rule, ...] = (
        WeekdayRule(),
        OperatingDateRule(),
        DstTransitionRule(),
        OvernightRolloverRule(),
        EvidenceGateRule(),
        DoorToDoorRule(),
        MinimumConnectionRule(),
        RequiredBufferRule(),
        HotelWindowRule(),
        LuggageStorageRule(),
        OvernightAccommodationRule(),
        ScheduleHorizonRule(),
        LastAdmissionRule(),
        LastServiceRule(),
        OperatingHoursRule(),
    )
    return tuple(sorted(rules, key=lambda rule: rule.rule_id))

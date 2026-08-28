"""Central registry for versioned challenge rules."""

from __future__ import annotations

from dataclasses import dataclass

from ..evidence import critical_evidence_findings
from .base import ChallengeContext, ChallengeStage, Rule
from .budget import BudgetBasisRule, BudgetCoverageRule, BudgetFxRule, ContingencyRule
from .calendar import DstTransitionRule, OperatingDateRule, OvernightRolloverRule, WeekdayRule
from .load import CumulativeLoadRule, DailyLoadRule, DrivingLoadRule, RecoveryRule
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
from .readiness import (
    AccessibilityChainRule,
    AccessibilityConflictRule,
    BookingWindowRule,
    CancellationRule,
    CapacityRule,
    DependencyCycleRule,
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
        AccessibilityChainRule(),
        AccessibilityConflictRule(),
        BookingWindowRule(),
        DependencyCycleRule(),
        CapacityRule(),
        CancellationRule(),
        BudgetFxRule(),
        BudgetBasisRule(),
        BudgetCoverageRule(),
        ContingencyRule(),
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
        DailyLoadRule(),
        CumulativeLoadRule(),
        DrivingLoadRule(),
        RecoveryRule(),
        ScheduleHorizonRule(),
        LastAdmissionRule(),
        LastServiceRule(),
        OperatingHoursRule(),
    )
    return tuple(sorted(rules, key=lambda rule: rule.rule_id))

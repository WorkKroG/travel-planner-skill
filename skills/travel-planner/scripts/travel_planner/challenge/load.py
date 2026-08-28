"""Physical load and recovery challenge rules."""

from __future__ import annotations

from dataclasses import dataclass

from ..evidence import Finding
from .base import ChallengeContext, ChallengeStage


@dataclass(frozen=True)
class DailyLoadRule:
    rule_id: str = "LOAD-001"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for day in ctx.facts.get("daily_loads", []):
            walk = day.get("walking_km")
            maximum = day.get("group_max_walking_km")
            if walk is not None and maximum is not None and float(walk) > float(maximum):
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (day["id"],),
                        (),
                        f"Walking demand {walk} km exceeds group limit {maximum} km.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class CumulativeLoadRule:
    rule_id: str = "LOAD-002"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        threshold = float(ctx.facts.get("high_load_threshold", 8))
        maximum = int(ctx.facts.get("max_consecutive_high_load_days", 2))
        streak: list[str] = []
        for day in ctx.facts.get("daily_loads", []):
            if float(day.get("load_score", 0)) >= threshold:
                streak.append(day["id"])
                if len(streak) > maximum:
                    return (
                        Finding(
                            self.rule_id,
                            "warning",
                            "high",
                            tuple(streak),
                            (),
                            "Consecutive high-load days exceed the configured recovery limit.",
                        ),
                    )
            else:
                streak = []
        return ()


@dataclass(frozen=True)
class DrivingLoadRule:
    rule_id: str = "LOAD-003"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "blocking",
                "high",
                (day["id"],),
                (),
                "Daily driving exceeds the configured driver limit.",
            )
            for day in ctx.facts.get("daily_loads", [])
            if day.get("driving_hours") is not None
            and day.get("max_driving_hours") is not None
            and float(day["driving_hours"]) > float(day["max_driving_hours"])
        )


@dataclass(frozen=True)
class RecoveryRule:
    rule_id: str = "LOAD-004"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        if not ctx.facts.get("recovery_required") or ctx.facts.get("recovery_planned"):
            return ()
        return (
            Finding(
                self.rule_id,
                "warning",
                "medium",
                (ctx.state.brief["trip_id"],),
                (),
                "Route load requires a recovery block, but none is planned.",
            ),
        )


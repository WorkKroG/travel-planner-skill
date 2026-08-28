"""Budget normalization and completeness challenge rules."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from ..evidence import Finding
from .base import ChallengeContext, ChallengeStage


@dataclass(frozen=True)
class MoneyAmount:
    amount: Decimal
    currency: str
    amount_type: Literal["estimate", "observed_price", "quote", "booked", "paid"]
    basis: Literal["person", "group"]
    taxes_included: bool | None


@dataclass(frozen=True)
class BudgetFxRule:
    rule_id: str = "BUD-001"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        items = ctx.facts.get("budget_items", ctx.state.itinerary.get("budget_items", []))
        currencies = {item.get("currency") for item in items if item.get("currency")}
        fx = ctx.facts.get("fx")
        if len(currencies) <= 1 or (
            isinstance(fx, dict) and {"rate", "source_id", "observed_at"} <= fx.keys()
        ):
            return ()
        return (
            Finding(
                self.rule_id,
                "blocking",
                "high",
                tuple(sorted(str(item.get("id")) for item in items)),
                (),
                "Mixed-currency budget requires a dated FX rate and source.",
            ),
        )


@dataclass(frozen=True)
class BudgetBasisRule:
    rule_id: str = "BUD-002"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        items = ctx.facts.get("budget_items", ctx.state.itinerary.get("budget_items", []))
        bases = {item.get("basis") for item in items if item.get("basis")}
        normalized = ctx.facts.get("budget_normalized", False)
        if len(bases) <= 1 or normalized:
            return ()
        return (
            Finding(
                self.rule_id,
                "blocking",
                "high",
                tuple(sorted(str(item.get("id")) for item in items)),
                (),
                "Per-person and per-group prices must be normalized before summing.",
            ),
        )


@dataclass(frozen=True)
class BudgetCoverageRule:
    rule_id: str = "BUD-003"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        required = set(ctx.facts.get("required_budget_categories", []))
        items = ctx.facts.get("budget_items", ctx.state.itinerary.get("budget_items", []))
        present = {item.get("category") for item in items}
        missing = tuple(sorted(str(category) for category in required - present))
        if not missing:
            return ()
        return (
            Finding(
                self.rule_id,
                "warning",
                "high",
                missing,
                (),
                "Missing mandatory budget categories: " + ", ".join(missing),
            ),
        )


@dataclass(frozen=True)
class ContingencyRule:
    rule_id: str = "BUD-004"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        if ctx.facts.get("contingency_percent") is not None:
            return ()
        return (
            Finding(
                self.rule_id,
                "warning",
                "medium",
                (ctx.state.brief["trip_id"],),
                (),
                "Budget has no explicit contingency buffer.",
            ),
        )


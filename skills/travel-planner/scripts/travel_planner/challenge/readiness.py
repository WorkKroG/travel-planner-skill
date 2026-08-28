"""Booking dependency and end-to-end accessibility challenge rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..evidence import Finding
from .base import ChallengeContext, ChallengeStage


def _booking_items(ctx: ChallengeContext) -> list[dict[str, Any]]:
    return list(ctx.facts.get("booking_items", ctx.state.readiness.get("items", [])))


@dataclass(frozen=True)
class BookingWindowRule:
    rule_id: str = "BOOK-001"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        closed = {"booked", "confirmed", "waived", "not_applicable"}
        for item in _booking_items(ctx):
            due_value = item.get("due_at")
            if not due_value or item.get("status") in closed:
                continue
            due = datetime.fromisoformat(due_value)
            if due < ctx.now:
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (item["id"],),
                        tuple(item.get("source_ids", [])),
                        f"Booking deadline passed at {due.isoformat()}.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class DependencyCycleRule:
    rule_id: str = "BOOK-002"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        items = _booking_items(ctx)
        graph = {str(item["id"]): tuple(item.get("dependencies", [])) for item in items}
        visiting: list[str] = []
        visited: set[str] = set()

        def visit(node: str) -> tuple[str, ...] | None:
            if node in visiting:
                start = visiting.index(node)
                return tuple(visiting[start:] + [node])
            if node in visited:
                return None
            visiting.append(node)
            for dependency in graph.get(node, ()):
                cycle = visit(str(dependency))
                if cycle:
                    return cycle
            visiting.pop()
            visited.add(node)
            return None

        for node in sorted(graph):
            cycle = visit(node)
            if cycle:
                return (
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        cycle,
                        (),
                        "Booking dependency cycle: " + " -> ".join(cycle),
                    ),
                )
        return ()


@dataclass(frozen=True)
class CapacityRule:
    rule_id: str = "BOOK-003"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "blocking",
                "high",
                (item["id"],),
                tuple(item.get("source_ids", [])),
                "Known capacity is below the required party size.",
            )
            for item in _booking_items(ctx)
            if item.get("capacity") is not None
            and item.get("party_size") is not None
            and int(item["capacity"]) < int(item["party_size"])
        )


@dataclass(frozen=True)
class CancellationRule:
    rule_id: str = "BOOK-004"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "warning",
                "medium",
                (item["id"],),
                tuple(item.get("source_ids", [])),
                "Selected booking has no cancellation/refund summary.",
            )
            for item in _booking_items(ctx)
            if item.get("status") in {"selected", "booked"} and not item.get("cancellation_summary")
        )


@dataclass(frozen=True)
class AccessibilityChainRule:
    rule_id: str = "ACC-001"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for chain in ctx.facts.get("accessibility_chains", []):
            if not chain.get("requires_wheelchair"):
                continue
            unknown = [segment for segment in chain.get("segments", []) if segment.get("status") == "unknown"]
            for segment in unknown:
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (chain["id"], segment["id"]),
                        tuple(segment.get("source_ids", [])),
                        "Wheelchair accessibility is unknown for one segment of the chain.",
                        {
                            "status": "action_needed",
                            "category": "transport",
                            "owner_id": chain.get("traveler_id"),
                        },
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class AccessibilityConflictRule:
    rule_id: str = "ACC-002"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "blocking",
                "high",
                (chain["id"], segment["id"]),
                tuple(segment.get("source_ids", [])),
                "A required accessibility segment is explicitly inaccessible.",
            )
            for chain in ctx.facts.get("accessibility_chains", [])
            for segment in chain.get("segments", [])
            if chain.get("requires_wheelchair") and segment.get("status") == "inaccessible"
        )


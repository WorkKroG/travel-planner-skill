"""Operating cutoff and door-to-door logistics challenge rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..evidence import Finding
from .base import ChallengeContext, ChallengeStage
from .calendar import local_dt


@dataclass(frozen=True)
class ScheduleHorizonRule:
    rule_id: str = "OPS-001"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "warning",
                "high",
                (schedule["id"],),
                tuple(schedule.get("source_ids", [])),
                "Schedule is not released yet; no departure time may be assumed.",
                {"status": "recheck", "next_check_at": schedule.get("next_check_at")},
            )
            for schedule in ctx.facts.get("schedules", [])
            if schedule.get("status") == "not_released_yet"
        )


@dataclass(frozen=True)
class LastAdmissionRule:
    rule_id: str = "OPS-002"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        visits = list(ctx.facts.get("venue_arrivals", []))
        if hasattr(ctx, "arrival") and hasattr(ctx, "venue"):
            visits.append({"arrival": ctx.arrival, "venue": ctx.venue})
        findings = []
        for visit in visits:
            venue = visit["venue"]
            arrival = local_dt(visit["arrival"], venue["timezone"])
            hour, minute = (int(part) for part in venue["last_admission"].split(":"))
            cutoff = arrival.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if arrival > cutoff:
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (venue.get("id", "venue"),),
                        tuple(venue.get("source_ids", [])),
                        f"Arrival {arrival.time()} is after last admission {venue['last_admission']}.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class LastServiceRule:
    rule_id: str = "OPS-003"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for service in ctx.facts.get("last_services", []):
            arrival = datetime.fromisoformat(service["ready_at"])
            cutoff = datetime.fromisoformat(service["last_service_at"])
            if arrival > cutoff:
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (service["id"],),
                        tuple(service.get("source_ids", [])),
                        "Ready time is after the last available service.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class OperatingHoursRule:
    rule_id: str = "OPS-004"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for visit in ctx.facts.get("operating_visits", []):
            starts = datetime.fromisoformat(visit["starts_at"])
            ends = datetime.fromisoformat(visit["ends_at"])
            opens = datetime.fromisoformat(visit["opens_at"])
            closes = datetime.fromisoformat(visit["closes_at"])
            if starts < opens or ends > closes:
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (visit["id"],),
                        tuple(visit.get("source_ids", [])),
                        "Planned visit falls outside operating hours.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class DoorToDoorRule:
    rule_id: str = "LEG-001"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for leg in ctx.facts.get("legs", []):
            required = sum(int(value) for value in leg.get("components", {}).values())
            allocated = int(leg.get("allocated_minutes", 0))
            if required > allocated:
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (leg["id"],),
                        (),
                        f"Door-to-door components require {required} minutes, but only {allocated} are allocated.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class MinimumConnectionRule:
    rule_id: str = "LEG-002"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "blocking",
                "high",
                (connection["id"],),
                (),
                f"Connection has {connection['available_minutes']} minutes; minimum is {connection['minimum_minutes']}.",
            )
            for connection in ctx.facts.get("connections", [])
            if int(connection["available_minutes"]) < int(connection["minimum_minutes"])
        )


@dataclass(frozen=True)
class RequiredBufferRule:
    rule_id: str = "LEG-003"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for leg in ctx.facts.get("buffer_checks", []):
            missing = [name for name in leg.get("required", []) if not leg.get("buffers", {}).get(name)]
            if missing:
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (leg["id"],),
                        (),
                        "Missing required buffers: " + ", ".join(sorted(missing)),
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class HotelWindowRule:
    rule_id: str = "LEG-004"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "warning",
                "medium",
                (stay["id"],),
                (),
                "Arrival or departure falls outside the confirmed hotel handling window.",
            )
            for stay in ctx.facts.get("hotel_windows", [])
            if stay.get("outside_window") and not stay.get("handling_confirmed")
        )


@dataclass(frozen=True)
class LuggageStorageRule:
    rule_id: str = "LEG-005"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "blocking",
                "medium",
                (item["id"],),
                tuple(item.get("source_ids", [])),
                "Luggage storage is required but not confirmed.",
                {"status": "action_needed", "category": "lodging"},
            )
            for item in ctx.facts.get("luggage_storage", [])
            if item.get("required") and item.get("status") != "confirmed"
        )


@dataclass(frozen=True)
class OvernightAccommodationRule:
    rule_id: str = "LEG-006"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return tuple(
            Finding(
                self.rule_id,
                "blocking",
                "high",
                (leg["id"],),
                (),
                "Overnight arrival has no linked accommodation night.",
            )
            for leg in ctx.facts.get("overnight_legs", [])
            if not leg.get("night_id")
        )

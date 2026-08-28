"""Calendar, local-date, and timezone challenge rules."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from ..evidence import Finding
from .base import ChallengeContext, ChallengeStage


def local_dt(value: str, timezone: str) -> datetime:
    """Interpret naive values in the stated timezone and normalize aware values to it."""
    zone = ZoneInfo(timezone)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)


@dataclass(frozen=True)
class WeekdayRule:
    rule_id: str = "CAL-001"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for event in ctx.facts.get("dated_events", []):
            starts = local_dt(event["starts_at"], event["timezone"])
            actual = calendar.day_name[starts.weekday()]
            if actual != event.get("expected_weekday"):
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (event["id"],),
                        (),
                        f"{event['id']} falls on {actual}, not {event.get('expected_weekday')}.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class OperatingDateRule:
    rule_id: str = "CAL-002"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for visit in ctx.facts.get("dated_visits", []):
            visit_date = local_dt(visit["starts_at"], visit["timezone"]).date().isoformat()
            if visit_date in visit.get("closed_dates", []):
                findings.append(
                    Finding(
                        self.rule_id,
                        "blocking",
                        "high",
                        (visit["id"],),
                        tuple(visit.get("source_ids", [])),
                        f"{visit['id']} is closed on {visit_date}.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class DstTransitionRule:
    rule_id: str = "CAL-003"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for interval in ctx.facts.get("timezone_intervals", []):
            start = local_dt(interval["start"], interval["timezone"])
            end = local_dt(interval["end"], interval["timezone"])
            if start.utcoffset() != end.utcoffset():
                findings.append(
                    Finding(
                        self.rule_id,
                        "warning",
                        "high",
                        (interval["id"],),
                        (),
                        "Local UTC offset changes during this interval; recheck all cutoffs.",
                    )
                )
        return tuple(findings)


@dataclass(frozen=True)
class OvernightRolloverRule:
    rule_id: str = "CAL-004"
    version: int = 1
    stages: frozenset[ChallengeStage] = frozenset({"detailed"})

    def evaluate(self, ctx: ChallengeContext):
        findings = []
        for leg in ctx.facts.get("overnight_legs", []):
            zone = leg["arrival_timezone"]
            departure = local_dt(leg["departure"], zone)
            arrival = local_dt(leg["arrival"], zone)
            if arrival.date() > departure.date():
                findings.append(
                    Finding(
                        self.rule_id,
                        "note",
                        "high",
                        (leg["day_id"], leg["night_id"]),
                        (),
                        f"{leg['id']} arrives on local date {arrival.date().isoformat()}.",
                    )
                )
        return tuple(findings)


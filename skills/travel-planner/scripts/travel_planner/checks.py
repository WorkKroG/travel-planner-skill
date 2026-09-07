"""Explicit deterministic checks over the canonical trip YAML shape."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from .budget import budget_item_errors
from .state import TripState, ValidationIssue

Severity = Literal["blocking", "warning", "note"]
Entry = tuple[dict[str, Any], str]
_SEVERITY_ORDER = {"blocking": 0, "warning": 1, "note": 2}


@dataclass(frozen=True)
class Finding:
    id: str
    code: str
    severity: Severity
    path: str
    affected_ids: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class CheckReport:
    structural_errors: tuple[ValidationIssue, ...]
    findings: tuple[Finding, ...]
    lifecycle_findings: tuple[Finding, ...]
    accepted_blocker_ids: tuple[str, ...]
    saved_findings: tuple[Finding, ...] = ()

    @property
    def all_findings(self) -> tuple[Finding, ...]:
        return tuple(
            sorted(
                (*self.findings, *self.saved_findings, *self.lifecycle_findings), key=_finding_key
            )
        )

    @property
    def blocking_findings(self) -> tuple[Finding, ...]:
        return tuple(filter(lambda item: item.severity == "blocking", self.all_findings))

    @property
    def accepted_blocking_findings(self) -> tuple[Finding, ...]:
        accepted = set(self.accepted_blocker_ids)
        return tuple(filter(lambda item: item.id in accepted, self.saved_findings))

    @property
    def unaccepted_blocking_findings(self) -> tuple[Finding, ...]:
        accepted = set(self.accepted_blocker_ids)
        return tuple(
            filter(
                lambda item: item.id not in accepted or item in self.lifecycle_findings,
                self.blocking_findings,
            )
        )

    @property
    def lifecycle_consistent(self) -> bool:
        return not self.lifecycle_findings

    @property
    def ok(self) -> bool:
        return (
            not self.structural_errors
            and self.lifecycle_consistent
            and not any(item.severity == "blocking" for item in self.findings)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope": "recorded_data_integrity",
            "ok": self.ok,
            "saved_findings": list(map(asdict, self.saved_findings)),
            "structural_errors": list(map(asdict, self.structural_errors)),
            "lifecycle_consistent": self.lifecycle_consistent,
            "lifecycle_findings": list(map(asdict, self.lifecycle_findings)),
            "blocking_findings": list(map(asdict, self.blocking_findings)),
            "accepted_blocking_findings": list(map(asdict, self.accepted_blocking_findings)),
            "unaccepted_blocking_findings": list(map(asdict, self.unaccepted_blocking_findings)),
            "findings": list(map(asdict, self.all_findings)),
        }


def _finding_key(item: Finding) -> tuple[int, str, str, tuple[str, ...]]:
    return (_SEVERITY_ORDER[item.severity], item.code, item.path, item.affected_ids)


def _finding(
    code: str,
    path: str,
    message: str,
    *affected_ids: str,
    severity: Severity = "blocking",
) -> Finding:
    raw = "-".join((code.lower().replace("_", "-"), *affected_ids))
    slug = re.sub(r"[^a-z0-9-]+", "-", raw).strip("-")[:54].rstrip("-")
    digest = hashlib.sha256(path.encode()).hexdigest()[:8]
    return Finding(f"{slug}-{digest}", code, severity, path, affected_ids, message)


def _records(value: Any, base_path: str) -> tuple[Entry, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        (item, f"{base_path}[{position}]")
        for position, item in enumerate(value)
        if isinstance(item, dict)
    )


def _timeline_entries(days: tuple[Entry, ...]) -> tuple[Entry, ...]:
    entries: list[Entry] = []
    for day, day_path in days:
        entries.extend(_records(day.get("timeline"), f"{day_path}.timeline"))
        for scenario, scenario_path in _records(day.get("scenarios"), f"{day_path}.scenarios"):
            entries.extend(_records(scenario.get("timeline"), f"{scenario_path}.timeline"))
    return tuple(entries)


def _scenario_entries(days: tuple[Entry, ...]) -> tuple[Entry, ...]:
    return tuple(
        entry
        for day, day_path in days
        for entry in _records(day.get("scenarios"), f"{day_path}.scenarios")
    )


def _event_alternative_entries(timeline: tuple[Entry, ...]) -> tuple[Entry, ...]:
    return tuple(
        entry
        for event, event_path in timeline
        for entry in _records(event.get("alternatives"), f"{event_path}.alternatives")
    )


def _claim_entries(state: TripState) -> tuple[Entry, ...]:
    claims = list(_records(state.candidates.get("claims"), "candidates.yaml.claims"))
    for candidate, path in _records(state.candidates.get("items"), "candidates.yaml.items"):
        claims.extend(_records(candidate.get("claims"), f"{path}.claims"))
    return tuple(claims)


def _unique_ids(entries: tuple[Entry, ...], key: str = "id") -> set[str]:
    counts = Counter(str(record.get(key, "")) for record, _ in entries)
    return {identifier for identifier, count in counts.items() if identifier and count == 1}


def _identity_findings(entries: tuple[Entry, ...], key: str = "id") -> tuple[Finding, ...]:
    seen: set[str] = set()
    findings: list[Finding] = []
    for record, path in entries:
        identifier = str(record.get(key, ""))
        if not identifier:
            continue
        if identifier in seen:
            findings.append(
                _finding(
                    "ID_DUPLICATE",
                    f"{path}.{key}",
                    f"Duplicate canonical ID {identifier!r} is ambiguous.",
                    identifier,
                )
            )
        else:
            seen.add(identifier)
    return tuple(findings)


def _identity_checks(state: TripState, days: tuple[Entry, ...]) -> tuple[Finding, ...]:
    timeline = _timeline_entries(days)
    groups = (
        _records(state.brief.get("travelers"), "brief.yaml.travelers"),
        _records(state.candidates.get("items"), "candidates.yaml.items"),
        _records(state.itinerary.get("alternatives"), "itinerary.yaml.alternatives"),
        _records(state.itinerary.get("route_stops"), "itinerary.yaml.route_stops"),
        days,
        _scenario_entries(days),
        timeline,
        _event_alternative_entries(timeline),
        _records(state.itinerary.get("budget_items"), "itinerary.yaml.budget_items"),
        _records(state.candidates.get("sources"), "candidates.yaml.sources"),
        _claim_entries(state),
        _records(state.readiness.get("items"), "readiness.yaml.items"),
        _records(state.itinerary.get("challenge_findings"), "itinerary.yaml.challenge_findings"),
    )
    findings = [item for group in groups for item in _identity_findings(group)]
    acceptances = _records(
        state.itinerary.get("accepted_blockers"), "itinerary.yaml.accepted_blockers"
    )
    findings.extend(_identity_findings(acceptances, "blocker_id"))
    return tuple(findings)


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


def _date_checks(state: TripState, timeline: tuple[Entry, ...]) -> tuple[Finding, ...]:
    """Check recorded date order, without interpreting travel feasibility."""
    findings: list[Finding] = []
    dates = state.brief.get("travel_dates", {})
    try:
        start_date, end_date = (date.fromisoformat(dates[key]) for key in ("start", "end"))
    except (TypeError, ValueError, KeyError):
        pass  # Missing dates are allowed; schemas diagnose malformed present dates.
    else:
        if end_date < start_date:
            findings.append(
                _finding(
                    "DATE_ORDER_INVALID",
                    "brief.yaml.travel_dates",
                    "Recorded end date precedes start date.",
                )
            )
    fields = (
        "start_at",
        "end_at",
        "operating_start_at",
        "operating_end_at",
        "last_admission_at",
        "last_service_at",
    )
    for event, path in timeline:
        owner = str(event.get("id", "unknown-event"))
        recorded = {field: _timestamp(event.get(field)) for field in fields}
        for field in fields:
            if event.get(field) is not None and recorded[field] is None:
                findings.append(
                    _finding(
                        "CALENDAR_TIMESTAMP_INVALID",
                        f"{path}.{field}",
                        "Recorded timestamps require a valid UTC offset.",
                        owner,
                    )
                )
        for first, last in (("start_at", "end_at"), ("operating_start_at", "operating_end_at")):
            if (
                recorded[first] is not None
                and recorded[last] is not None
                and recorded[last] < recorded[first]
            ):
                findings.append(
                    _finding(
                        "CALENDAR_INTERVAL_INVALID",
                        f"{path}.{last}",
                        "Recorded end precedes its start.",
                        owner,
                    )
                )
    return tuple(findings)


def _reference_findings(
    record: dict[str, Any],
    path: str,
    key: str,
    known: set[str],
    code: str,
    owner_id: str,
) -> tuple[Finding, ...]:
    value = record.get(key)
    if isinstance(value, str):
        references = ((value, f"{path}.{key}"),)
    elif isinstance(value, list):
        references = tuple(
            (str(item), f"{path}.{key}[{position}]") for position, item in enumerate(value)
        )
    else:
        return ()
    return tuple(
        _finding(
            code,
            item_path,
            f"Reference {reference!r} does not resolve to one unambiguous canonical ID.",
            owner_id,
            reference,
        )
        for reference, item_path in references
        if reference not in known
    )


def _link_checks(state: TripState, days: tuple[Entry, ...]) -> tuple[Finding, ...]:
    alternatives = _records(state.itinerary.get("alternatives"), "itinerary.yaml.alternatives")
    stops = _records(state.itinerary.get("route_stops"), "itinerary.yaml.route_stops")
    timeline = _timeline_entries(days)
    readiness = _records(state.readiness.get("items"), "readiness.yaml.items")
    sources = _records(state.candidates.get("sources"), "candidates.yaml.sources")
    claims = _claim_entries(state)
    route_ids, stop_ids = _unique_ids(alternatives), _unique_ids(stops)
    readiness_ids, source_ids, claim_ids = (
        _unique_ids(readiness),
        _unique_ids(sources),
        _unique_ids(claims),
    )
    findings: list[Finding] = []
    selected = state.itinerary.get("selected_route_id")
    if isinstance(selected, str) and selected not in route_ids:
        findings.append(
            _finding(
                "LINK_ROUTE_NOT_FOUND",
                "itinerary.yaml.selected_route_id",
                "selected_route_id must resolve to one itinerary alternative.",
                selected,
            )
        )
    day_specs = (
        ("route_id", route_ids, "LINK_ROUTE_NOT_FOUND"),
        ("readiness_ids", readiness_ids, "LINK_READINESS_NOT_FOUND"),
        ("source_ids", source_ids, "LINK_SOURCE_NOT_FOUND"),
        ("claim_ids", claim_ids, "LINK_CLAIM_NOT_FOUND"),
        ("overnight_stop_id", stop_ids, "LINK_OVERNIGHT_STAY_NOT_FOUND"),
    )
    event_specs = day_specs[:4]
    readiness_specs = (
        (
            "owner_id",
            _unique_ids(_records(state.brief.get("travelers"), "brief.yaml.travelers")),
            "LINK_OWNER_NOT_FOUND",
        ),
        ("dependencies", readiness_ids, "LINK_READINESS_NOT_FOUND"),
        ("source_ids", source_ids, "LINK_SOURCE_NOT_FOUND"),
        ("claim_ids", claim_ids, "LINK_CLAIM_NOT_FOUND"),
    )
    for entries, specs in (
        (days, day_specs),
        (timeline, event_specs),
        (readiness, readiness_specs),
        (alternatives, day_specs[1:4]),
        (stops, day_specs[1:4]),
        (
            _records(state.itinerary.get("budget_items"), "itinerary.yaml.budget_items"),
            day_specs[2:4],
        ),
    ):
        for record, path in entries:
            owner = str(record.get("id", "unknown-item"))
            for key, known, code in specs:
                findings.extend(_reference_findings(record, path, key, known, code, owner))
    for day, day_path in days:
        for photo, path in _records(day.get("media"), f"{day_path}.media"):
            findings.extend(_reference_findings(
                photo, path, "source_id", source_ids, "LINK_SOURCE_NOT_FOUND", str(day["id"])
            ))
    for claim, path in claims:
        findings.extend(
            _reference_findings(
                claim,
                path,
                "source_ids",
                source_ids,
                "LINK_SOURCE_NOT_FOUND",
                str(claim.get("id", "unknown-claim")),
            )
        )
    summary = state.itinerary.get("budget_summary")
    if isinstance(summary, dict) and isinstance(summary.get("fx"), dict):
        findings.extend(
            _reference_findings(
                summary["fx"],
                "itinerary.yaml.budget_summary.fx",
                "source_id",
                source_ids,
                "LINK_SOURCE_NOT_FOUND",
                "budget-summary",
            )
        )
    return tuple(findings)


def _budget_checks(state: TripState) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for item, path in _records(state.itinerary.get("budget_items"), "itinerary.yaml.budget_items"):
        errors = budget_item_errors(item)
        if errors:
            findings.append(
                _finding("BUDGET_ITEM_INVALID", path, "; ".join(errors), str(item["id"]))
            )
    summary = state.itinerary.get("budget_summary")
    if isinstance(summary, dict):
        errors = budget_item_errors(summary)
        if errors:
            findings.append(
                _finding("BUDGET_VALUE_INVALID", "itinerary.yaml.budget_summary", "; ".join(errors))
            )
        fx = summary.get("fx")
        if isinstance(fx, dict) and isinstance(fx.get("rates"), dict):
            for currency, value in fx["rates"].items():
                if (
                    budget_item_errors({"amount": value})
                    or value is None
                    or Decimal(str(value)) <= 0
                ):
                    findings.append(
                        _finding(
                            "BUDGET_FX_INVALID",
                            f"itinerary.yaml.budget_summary.fx.rates.{currency}",
                            "Recorded FX rates must be finite positive numbers.",
                        )
                    )
    return tuple(findings)


def _stored_blockers(state: TripState) -> tuple[Finding, ...]:
    return tuple(
        Finding(
            item["id"],
            item["code"],
            "blocking",
            item["path"],
            tuple(item["affected_ids"]),
            item["message"],
        )
        for item, _ in _records(
            state.itinerary.get("challenge_findings"),
            "itinerary.yaml.challenge_findings",
        )
    )


def _effective_acceptances(
    state: TripState, blockers: tuple[Finding, ...], collided: set[str]
) -> tuple[str, ...]:
    itinerary = state.itinerary
    blocker_counts = Counter(item.id for item in blockers)
    entries = _records(itinerary.get("accepted_blockers"), "itinerary.yaml.accepted_blockers")
    acceptance_counts = Counter(str(item.get("blocker_id", "")) for item, _ in entries)
    return tuple(
        sorted(
            identifier
            for identifier, count in acceptance_counts.items()
            if count == 1 and blocker_counts[identifier] == 1 and identifier not in collided
        )
    )


def _lifecycle_checks(
    state: TripState,
    blockers: tuple[Finding, ...],
    collided: set[str],
) -> tuple[Finding, ...]:
    itinerary = state.itinerary
    status, verification, basis = (
        itinerary.get("document_status"),
        itinerary.get("verification_level"),
        itinerary.get("finalization_basis"),
    )
    findings: list[Finding] = []
    if status == "draft" and basis is not None:
        findings.append(
            _finding(
                "DRAFT_FINALIZATION_BASIS",
                "itinerary.yaml.finalization_basis",
                "Draft requires finalization_basis=null.",
            )
        )
    if status == "final" and basis not in {"codex_validated", "user_confirmed"}:
        findings.append(
            _finding(
                "FINAL_BASIS_REQUIRED",
                "itinerary.yaml.finalization_basis",
                "Final requires a valid finalization basis.",
            )
        )
    if basis == "codex_validated" and verification != "codex_validated":
        findings.append(
            _finding(
                "FINAL_CODEX_VERIFICATION_REQUIRED",
                "itinerary.yaml.verification_level",
                "Codex finalization requires verification_level=codex_validated.",
            )
        )
    blocker_ids = {item.id for item in blockers}
    for acceptance, path in _records(
        itinerary.get("accepted_blockers"), "itinerary.yaml.accepted_blockers"
    ):
        identifier = acceptance.get("blocker_id")
        if not isinstance(identifier, str) or identifier not in blocker_ids:
            findings.append(
                _finding(
                    "ACCEPTED_BLOCKER_NOT_FOUND",
                    f"{path}.blocker_id",
                    "Accepted blocker_id must reference an existing blocker.",
                    str(identifier),
                )
            )
    for identifier in sorted(collided):
        findings.append(
            _finding(
                "FINDING_ID_COLLISION",
                "itinerary.yaml.challenge_findings",
                "Stored and computed findings must not share an ID.",
                identifier,
            )
        )
    return tuple(findings)


def run_checks(state: TripState) -> CheckReport:
    """Check recorded data; saved trip concerns never decide the result."""
    days = _records(state.itinerary.get("days"), "itinerary.yaml.days")
    timeline = _timeline_entries(days)
    stored = _stored_blockers(state)
    computed = (
        *_identity_checks(state, days),
        *_date_checks(state, timeline),
        *_link_checks(state, days),
        *_budget_checks(state),
    )
    collided = {item.id for item in computed} & {item.id for item in stored}
    findings = tuple(sorted(computed, key=_finding_key))
    blockers = stored
    accepted = _effective_acceptances(state, blockers, collided)
    lifecycle = tuple(
        sorted(
            _lifecycle_checks(state, blockers, collided),
            key=_finding_key,
        )
    )
    return CheckReport((), findings, lifecycle, accepted, stored)

"""Explicit deterministic checks for canonical trip state."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from .evidence import HIGH_STAKES_TOPICS
from .state import TripState, ValidationIssue

Severity = Literal["blocking", "warning", "note"]
_SEVERITY_ORDER = {"blocking": 0, "warning": 1, "note": 2}


@dataclass(frozen=True)
class Finding:
    """One stable, visible result from an explicit check."""

    id: str
    code: str
    severity: Severity
    path: str
    affected_ids: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class CheckReport:
    """Structural, hard-check, and lifecycle results kept as separate surfaces."""

    structural_errors: tuple[ValidationIssue, ...]
    findings: tuple[Finding, ...]
    lifecycle_findings: tuple[Finding, ...]
    accepted_blocker_ids: tuple[str, ...]

    @property
    def all_findings(self) -> tuple[Finding, ...]:
        return tuple(sorted((*self.findings, *self.lifecycle_findings), key=_finding_key))

    @property
    def blocking_findings(self) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.all_findings if finding.severity == "blocking")

    @property
    def accepted_blocking_findings(self) -> tuple[Finding, ...]:
        accepted = set(self.accepted_blocker_ids)
        return tuple(finding for finding in self.findings if finding.id in accepted)

    @property
    def unaccepted_blocking_findings(self) -> tuple[Finding, ...]:
        accepted = set(self.accepted_blocker_ids)
        return tuple(
            finding
            for finding in self.blocking_findings
            if finding.id not in accepted or finding in self.lifecycle_findings
        )

    @property
    def lifecycle_consistent(self) -> bool:
        return not self.lifecycle_findings

    @property
    def ok(self) -> bool:
        return (
            not self.structural_errors
            and self.lifecycle_consistent
            and not self.unaccepted_blocking_findings
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "structural_errors": [asdict(error) for error in self.structural_errors],
            "lifecycle_consistent": self.lifecycle_consistent,
            "lifecycle_findings": [asdict(finding) for finding in self.lifecycle_findings],
            "blocking_findings": [asdict(finding) for finding in self.blocking_findings],
            "accepted_blocking_findings": [
                asdict(finding) for finding in self.accepted_blocking_findings
            ],
            "unaccepted_blocking_findings": [
                asdict(finding) for finding in self.unaccepted_blocking_findings
            ],
            "findings": [asdict(finding) for finding in self.all_findings],
        }


def _finding_key(finding: Finding) -> tuple[int, str, str, tuple[str, ...]]:
    return (
        _SEVERITY_ORDER[finding.severity],
        finding.code,
        finding.path,
        finding.affected_ids,
    )


def _lifecycle_finding(code: str, path: str, message: str, *affected_ids: str) -> Finding:
    return Finding(code.lower().replace("_", "-"), code, "blocking", path, affected_ids, message)


def _finding(code: str, path: str, message: str, *affected_ids: str) -> Finding:
    raw_id = "-".join((code.lower().replace("_", "-"), *affected_ids))
    finding_id = re.sub(r"[^a-z0-9-]+", "-", raw_id).strip("-")[:63].rstrip("-")
    return Finding(finding_id, code, "blocking", path, affected_ids, message)


def _note(code: str, path: str, message: str, *affected_ids: str) -> Finding:
    blocking = _finding(code, path, message, *affected_ids)
    return Finding(
        blocking.id,
        blocking.code,
        "note",
        blocking.path,
        blocking.affected_ids,
        blocking.message,
    )


def _mapping_items(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _record_id(record: dict[str, Any], fallback: str) -> str:
    value = record.get("id")
    return value if isinstance(value, str) and value else fallback


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _calendar_checks(state: TripState) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for day_position, day in enumerate(_mapping_items(state.itinerary.get("days"))):
        day_id = _record_id(day, f"day-{day_position + 1}")
        comparable: list[tuple[datetime, datetime, str, str]] = []
        for interval_position, interval in enumerate(_mapping_items(day.get("intervals"))):
            interval_id = _record_id(interval, f"interval-{interval_position + 1}")
            path = f"itinerary.yaml.days[{day_position}].intervals[{interval_position}]"
            start = _parse_timestamp(interval.get("start"))
            end = _parse_timestamp(interval.get("end"))
            if start is None or end is None:
                findings.append(
                    _finding(
                        "CALENDAR_TIMESTAMP_INVALID",
                        path,
                        "Explicit interval start and end must be ISO timestamps.",
                        day_id,
                        interval_id,
                    )
                )
                continue
            try:
                valid_interval = end > start
            except TypeError:
                valid_interval = False
            if not valid_interval:
                findings.append(
                    _finding(
                        "CALENDAR_INTERVAL_INVALID",
                        path,
                        "Explicit interval end must be later than start.",
                        day_id,
                        interval_id,
                    )
                )
                continue
            comparable.append((start, end, interval_id, path))

            cutoff_keys = (
                "operating_start",
                "operating_end",
                "last_admission_at",
                "last_service_at",
            )
            cutoffs = {key: _parse_timestamp(interval.get(key)) for key in cutoff_keys}
            if any(
                key in interval
                and (
                    cutoffs[key] is None
                    or (cutoffs[key].tzinfo is None) != (start.tzinfo is None)
                )
                for key in cutoff_keys
            ):
                findings.append(
                    _finding(
                        "CALENDAR_TIMESTAMP_INVALID",
                        path,
                        "Explicit operating and service cutoffs must be comparable ISO timestamps.",
                        day_id,
                        interval_id,
                    )
                )
                continue
            operating_start = cutoffs["operating_start"]
            operating_end = cutoffs["operating_end"]
            if (operating_start is not None and start < operating_start) or (
                operating_end is not None and end > operating_end
            ):
                findings.append(
                    _finding(
                        "CALENDAR_OUTSIDE_OPERATING_WINDOW",
                        path,
                        "Planned interval falls outside its explicit operating timestamps.",
                        day_id,
                        interval_id,
                    )
                )
            last_admission = cutoffs["last_admission_at"]
            if last_admission is not None and start > last_admission:
                findings.append(
                    _finding(
                        "CALENDAR_LAST_ADMISSION",
                        path,
                        "Planned start is after the explicit last-admission timestamp.",
                        day_id,
                        interval_id,
                    )
                )
            last_service = cutoffs["last_service_at"]
            if last_service is not None and start > last_service:
                findings.append(
                    _finding(
                        "CALENDAR_LAST_SERVICE",
                        path,
                        "Planned start is after the explicit last-service timestamp.",
                        day_id,
                        interval_id,
                    )
                )

        ordered = sorted(comparable, key=lambda item: (item[0], item[1], item[2]))
        for left_position, left in enumerate(ordered):
            for right in ordered[left_position + 1 :]:
                if right[0] >= left[1]:
                    break
                findings.append(
                    _finding(
                        "CALENDAR_INTERVAL_OVERLAP",
                        right[3],
                        "Explicit intervals overlap within the same day.",
                        day_id,
                        left[2],
                        right[2],
                    )
                )
    return tuple(sorted(findings, key=_finding_key))


def _buffer_checks(state: TripState) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for position, leg in enumerate(_mapping_items(state.itinerary.get("legs"))):
        leg_id = _record_id(leg, f"leg-{position + 1}")
        path = f"itinerary.yaml.legs[{position}]"
        components = leg.get("components")
        allocated = leg.get("allocated_minutes")
        if isinstance(components, dict) and isinstance(allocated, (int, float)):
            explicit = [
                value
                for value in components.values()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            ]
            if len(explicit) == len(components) and sum(explicit) > allocated:
                findings.append(
                    _finding(
                        "BUFFER_DOOR_TO_DOOR_SHORTFALL",
                        path,
                        "Allocated door-to-door minutes are below the explicit component sum.",
                        leg_id,
                    )
                )
        required = leg.get("required_buffers")
        markers = leg.get("buffer_markers")
        if isinstance(required, list):
            present = {str(item) for item in markers} if isinstance(markers, list) else set()
            missing = sorted(str(item) for item in required if str(item) not in present)
            if missing:
                findings.append(
                    _finding(
                        "BUFFER_MARKER_MISSING",
                        path,
                        "Missing required buffer markers: " + ", ".join(missing) + ".",
                        leg_id,
                    )
                )
    for position, connection in enumerate(
        _mapping_items(state.itinerary.get("connections"))
    ):
        available = connection.get("available_minutes")
        minimum = connection.get("minimum_minutes")
        if (
            isinstance(available, (int, float))
            and not isinstance(available, bool)
            and isinstance(minimum, (int, float))
            and not isinstance(minimum, bool)
            and available < minimum
        ):
            connection_id = _record_id(connection, f"connection-{position + 1}")
            findings.append(
                _finding(
                    "CONNECTION_MINIMUM_SHORTFALL",
                    f"itinerary.yaml.connections[{position}]",
                    "Available connection minutes are below the explicit minimum.",
                    connection_id,
                )
            )
    return tuple(sorted(findings, key=_finding_key))


def _claims_with_paths(state: TripState) -> tuple[tuple[dict[str, Any], str], ...]:
    claims = [
        (claim, f"candidates.yaml.claims[{position}]")
        for position, claim in enumerate(_mapping_items(state.candidates.get("claims")))
    ]
    for candidate_position, candidate in enumerate(
        _mapping_items(state.candidates.get("items"))
    ):
        claims.extend(
            (claim, f"candidates.yaml.items[{candidate_position}].claims[{position}]")
            for position, claim in enumerate(_mapping_items(candidate.get("claims")))
        )
    return tuple(claims)


def _missing_references(
    record: dict[str, Any],
    path: str,
    owner_id: str,
    key: str,
    known_ids: set[str],
    code: str,
) -> list[Finding]:
    value = record.get(key)
    references = value if isinstance(value, list) else [value] if isinstance(value, str) else []
    return [
        _finding(
            code,
            f"{path}.{key}",
            f"Reference {reference!r} does not resolve to a canonical ID.",
            owner_id,
            str(reference),
        )
        for reference in references
        if str(reference) not in known_ids
    ]


def _link_checks(state: TripState) -> tuple[Finding, ...]:
    alternatives = _mapping_items(state.itinerary.get("alternatives"))
    days = _mapping_items(state.itinerary.get("days"))
    legs = _mapping_items(state.itinerary.get("legs"))
    readiness = _mapping_items(state.readiness.get("items"))
    sources = _mapping_items(state.candidates.get("sources"))
    claim_records = _claims_with_paths(state)
    claims = tuple(claim for claim, _ in claim_records)
    route_ids = {_record_id(item, "") for item in alternatives} - {""}
    day_ids = {_record_id(item, "") for item in days} - {""}
    readiness_ids = {_record_id(item, "") for item in readiness} - {""}
    source_ids = {_record_id(item, "") for item in sources} - {""}
    claim_ids = {_record_id(item, "") for item in claims} - {""}
    stay_ids = {
        _record_id(item, "")
        for key in ("nights", "accommodations")
        for item in _mapping_items(state.itinerary.get(key))
    } - {""}
    findings: list[Finding] = []

    selected_route_id = state.itinerary.get("selected_route_id")
    if isinstance(selected_route_id, str) and selected_route_id not in route_ids:
        findings.append(
            _finding(
                "LINK_ROUTE_NOT_FOUND",
                "itinerary.yaml.selected_route_id",
                "selected_route_id must reference an itinerary alternative.",
                selected_route_id,
            )
        )

    groups = (
        (days, "itinerary.yaml.days", (("route_id", route_ids, "LINK_ROUTE_NOT_FOUND"),)),
        (
            legs,
            "itinerary.yaml.legs",
            (
                ("route_id", route_ids, "LINK_ROUTE_NOT_FOUND"),
                ("day_id", day_ids, "LINK_DAY_NOT_FOUND"),
                ("readiness_ids", readiness_ids, "LINK_READINESS_NOT_FOUND"),
                ("dependency_ids", readiness_ids, "LINK_READINESS_NOT_FOUND"),
                ("source_ids", source_ids, "LINK_SOURCE_NOT_FOUND"),
                ("claim_ids", claim_ids, "LINK_CLAIM_NOT_FOUND"),
            ),
        ),
        (
            readiness,
            "readiness.yaml.items",
            (
                ("dependencies", readiness_ids, "LINK_READINESS_NOT_FOUND"),
                ("source_ids", source_ids, "LINK_SOURCE_NOT_FOUND"),
                ("claim_ids", claim_ids, "LINK_CLAIM_NOT_FOUND"),
            ),
        ),
    )
    day_links = (
        ("readiness_ids", readiness_ids, "LINK_READINESS_NOT_FOUND"),
        ("source_ids", source_ids, "LINK_SOURCE_NOT_FOUND"),
        ("claim_ids", claim_ids, "LINK_CLAIM_NOT_FOUND"),
    )
    groups = ((days, "itinerary.yaml.days", (*groups[0][2], *day_links)), *groups[1:])
    for records, base_path, references in groups:
        for position, record in enumerate(records):
            owner_id = _record_id(record, f"item-{position + 1}")
            path = f"{base_path}[{position}]"
            for key, known_ids, code in references:
                findings.extend(
                    _missing_references(record, path, owner_id, key, known_ids, code)
                )

    for position, (claim, path) in enumerate(claim_records):
        claim_id = _record_id(claim, f"claim-{position + 1}")
        findings.extend(
            _missing_references(
                claim,
                path,
                claim_id,
                "source_ids",
                source_ids,
                "LINK_SOURCE_NOT_FOUND",
            )
        )

    for position, leg in enumerate(legs):
        if leg.get("overnight") is not True:
            continue
        leg_id = _record_id(leg, f"leg-{position + 1}")
        stay_id = leg.get("night_id", leg.get("accommodation_id"))
        if not isinstance(stay_id, str) or stay_id not in stay_ids:
            findings.append(
                _finding(
                    "LINK_OVERNIGHT_STAY_NOT_FOUND",
                    f"itinerary.yaml.legs[{position}]",
                    "Explicit overnight leg must reference an existing night or accommodation.",
                    leg_id,
                    str(stay_id),
                )
            )
    return tuple(sorted(findings, key=_finding_key))


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _budget_amounts(item: dict[str, Any]) -> tuple[Decimal, Decimal] | None:
    if item.get("amount_type") == "unknown":
        return None
    if item.get("amount") is not None:
        minimum = maximum = _decimal(item.get("amount"))
    else:
        minimum = _decimal(item.get("amount_min"))
        maximum = _decimal(item.get("amount_max"))
    if minimum is None or maximum is None:
        return None
    return minimum, maximum


def _valid_fx(state: TripState, currencies: set[str]) -> dict[str, Any] | None:
    fx = state.itinerary.get("budget_fx")
    if not isinstance(fx, dict):
        return None
    observed_at = _parse_timestamp(fx.get("observed_at"))
    source_id = fx.get("source_id")
    rates = fx.get("rates")
    base_currency = fx.get("base_currency")
    source_ids = {
        _record_id(source, "") for source in _mapping_items(state.candidates.get("sources"))
    }
    if (
        observed_at is None
        or not isinstance(source_id, str)
        or source_id not in source_ids
        or not isinstance(base_currency, str)
        or base_currency not in currencies
        or not isinstance(rates, dict)
    ):
        return None
    needed = currencies - {base_currency}
    if any(
        currency not in rates
        or _decimal(rates[currency]) is None
        or _decimal(rates[currency]) <= 0
        for currency in needed
    ):
        return None
    return fx


def _budget_checks(state: TripState) -> tuple[Finding, ...]:
    items = _mapping_items(state.itinerary.get("budget_items"))
    if not items:
        return ()
    findings: list[Finding] = []
    currencies = {
        str(item["currency"])
        for item in items
        if isinstance(item.get("currency"), str) and _budget_amounts(item) is not None
    }
    bases = {
        str(item["basis"])
        for item in items
        if isinstance(item.get("basis"), str) and _budget_amounts(item) is not None
    }
    fx = _valid_fx(state, currencies) if len(currencies) > 1 else None
    item_ids = tuple(sorted(_record_id(item, "unknown-budget-item") for item in items))
    if len(currencies) > 1 and fx is None:
        findings.append(
            _finding(
                "BUDGET_FX_REQUIRED",
                "itinerary.yaml.budget_items",
                "Mixed currencies require explicit dated FX metadata linked to a source.",
                *item_ids,
            )
        )

    travelers = _mapping_items(state.brief.get("travelers"))
    total = state.itinerary.get("budget_total")
    declared_travelers = total.get("traveler_count") if isinstance(total, dict) else None
    traveler_count = (
        declared_travelers
        if isinstance(declared_travelers, int) and declared_travelers > 0
        else len(travelers) or None
    )
    if len(bases) > 1 and traveler_count is None:
        findings.append(
            _finding(
                "BUDGET_BASIS_REQUIRED",
                "itinerary.yaml.budget_items",
                "Mixed per-person and per-group items require an explicit traveler count.",
                *item_ids,
            )
        )

    unknown_ids = tuple(
        sorted(
            _record_id(item, "unknown-budget-item")
            for item in items
            if _budget_amounts(item) is None
        )
    )
    for unknown_id in unknown_ids:
        findings.append(
            _note(
                "BUDGET_AMOUNT_UNKNOWN",
                "itinerary.yaml.budget_items",
                "Unknown budget amount remains excluded from arithmetic.",
                unknown_id,
            )
        )

    summable = (
        isinstance(total, dict)
        and not unknown_ids
        and (len(currencies) <= 1 or fx is not None)
        and (len(bases) <= 1 or traveler_count is not None)
    )
    if summable:
        base_currency = (
            str(fx["base_currency"])
            if fx is not None
            else next(iter(currencies), str(total.get("currency", "")))
        )
        minimum = Decimal(0)
        maximum = Decimal(0)
        for item in items:
            amounts = _budget_amounts(item)
            if amounts is None:
                continue
            multiplier = Decimal(1)
            if item.get("basis") == "per_person":
                multiplier *= Decimal(traveler_count or 1)
            currency = item.get("currency")
            if fx is not None and currency != base_currency:
                multiplier *= _decimal(fx["rates"][str(currency)]) or Decimal(0)
            minimum += amounts[0] * multiplier
            maximum += amounts[1] * multiplier

        declared_minimum = _decimal(total.get("amount_min", total.get("amount")))
        declared_maximum = _decimal(total.get("amount_max", total.get("amount")))
        if (
            total.get("currency") != base_currency
            or total.get("basis") != "per_group"
            or declared_minimum != minimum
            or declared_maximum != maximum
        ):
            findings.append(
                _finding(
                    "BUDGET_TOTAL_MISMATCH",
                    "itinerary.yaml.budget_total",
                    "Declared total or range does not match the summable known items.",
                    *item_ids,
                )
            )
    return tuple(sorted(findings, key=_finding_key))


def _readiness_checks(state: TripState) -> tuple[Finding, ...]:
    items = _mapping_items(state.readiness.get("items"))
    graph = {
        _record_id(item, f"readiness-{position + 1}"): tuple(
            str(value) for value in item.get("dependencies", [])
        )
        for position, item in enumerate(items)
    }
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(node: str) -> tuple[str, ...] | None:
        if node in visiting:
            start = visiting.index(node)
            return (*visiting[start:], node)
        if node in visited:
            return None
        visiting.append(node)
        for dependency in graph.get(node, ()):
            cycle = visit(dependency)
            if cycle is not None:
                return cycle
        visiting.pop()
        visited.add(node)
        return None

    for node in sorted(graph):
        cycle = visit(node)
        if cycle is not None:
            return (
                _finding(
                    "READINESS_CYCLE",
                    "readiness.yaml.items",
                    "Readiness dependency graph contains a cycle.",
                    *cycle,
                ),
            )
    return ()


def _source_metadata_checks(state: TripState) -> tuple[Finding, ...]:
    sources = {
        _record_id(source, ""): source
        for source in _mapping_items(state.candidates.get("sources"))
        if _record_id(source, "")
    }
    findings: list[Finding] = []
    for position, (claim, path) in enumerate(_claims_with_paths(state)):
        if claim.get("status") != "verified" or claim.get("topic") not in HIGH_STAKES_TOPICS:
            continue
        source_ids = claim.get("source_ids")
        references = source_ids if isinstance(source_ids, list) else []
        has_official = any(
            isinstance(source_id, str)
            and source_id in sources
            and sources[source_id].get("source_type") == "official"
            for source_id in references
        )
        if not has_official:
            claim_id = _record_id(claim, f"claim-{position + 1}")
            findings.append(
                _finding(
                    "SOURCE_OFFICIAL_REQUIRED",
                    path,
                    "Verified high-stakes claim must reference an existing official source.",
                    claim_id,
                )
            )
    return tuple(sorted(findings, key=_finding_key))


def _saved_blockers(state: TripState) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for position, value in enumerate(state.itinerary.get("challenge_findings", [])):
        if not isinstance(value, dict) or value.get("severity") != "blocking":
            continue
        blocker_id = value.get("id")
        if not isinstance(blocker_id, str) or not blocker_id:
            continue
        affected = value.get("affected_ids", [])
        findings.append(
            Finding(
                id=blocker_id,
                code=str(value.get("code", "SAVED_BLOCKER")),
                severity="blocking",
                path=str(value.get("path", f"itinerary.yaml.challenge_findings[{position}]")),
                affected_ids=tuple(str(item) for item in affected) if isinstance(affected, list) else (),
                message=str(value.get("message", "Saved blocking finding.")),
            )
        )
    return tuple(sorted(findings, key=_finding_key))


def _lifecycle_checks(state: TripState, findings: tuple[Finding, ...]) -> tuple[Finding, ...]:
    itinerary = state.itinerary
    document_status = itinerary.get("document_status")
    verification_level = itinerary.get("verification_level")
    basis = itinerary.get("finalization_basis")
    blockers = {finding.id: finding for finding in findings if finding.severity == "blocking"}
    lifecycle: list[Finding] = []

    if document_status == "draft" and basis is not None:
        lifecycle.append(
            _lifecycle_finding(
                "DRAFT_FINALIZATION_BASIS",
                "itinerary.yaml.finalization_basis",
                "Draft state requires finalization_basis to be null.",
            )
        )
    if document_status == "final" and basis not in {"codex_validated", "user_confirmed"}:
        lifecycle.append(
            _lifecycle_finding(
                "FINAL_BASIS_REQUIRED",
                "itinerary.yaml.finalization_basis",
                "Final state requires codex_validated or user_confirmed finalization_basis.",
            )
        )
    if basis == "codex_validated" and verification_level != "codex_validated":
        lifecycle.append(
            _lifecycle_finding(
                "FINAL_CODEX_VERIFICATION_REQUIRED",
                "itinerary.yaml.verification_level",
                "Codex finalization requires verification_level=codex_validated.",
            )
        )
    if basis == "codex_validated" and blockers:
        lifecycle.append(
            _lifecycle_finding(
                "FINAL_CODEX_HAS_BLOCKERS",
                "itinerary.yaml.finalization_basis",
                "Codex-validated Final cannot contain blocking findings.",
                *sorted(blockers),
            )
        )

    accepted_ids = {
        acceptance.get("blocker_id")
        for acceptance in itinerary.get("accepted_blockers", [])
        if isinstance(acceptance, dict) and acceptance.get("accepted_by_user") is True
    }
    if basis == "user_confirmed":
        remaining = tuple(sorted(set(blockers) - accepted_ids))
        if remaining:
            lifecycle.append(
                _lifecycle_finding(
                    "FINAL_USER_BLOCKERS_UNACCEPTED",
                    "itinerary.yaml.accepted_blockers",
                    "User-confirmed Final requires a separate acceptance for every blocker.",
                    *remaining,
                )
            )

    for position, acceptance in enumerate(itinerary.get("accepted_blockers", [])):
        if not isinstance(acceptance, dict):
            continue
        blocker_id = acceptance.get("blocker_id")
        if not isinstance(blocker_id, str) or blocker_id not in blockers:
            lifecycle.append(
                _lifecycle_finding(
                    "ACCEPTED_BLOCKER_NOT_FOUND",
                    f"itinerary.yaml.accepted_blockers[{position}].blocker_id",
                    "Accepted blocker_id must reference an existing blocking finding.",
                    str(blocker_id),
                )
            )
        elif blockers[blocker_id].id == blocker_id:
            source = next(
                (
                    item
                    for item in itinerary.get("challenge_findings", [])
                    if isinstance(item, dict) and item.get("id") == blocker_id
                ),
                None,
            )
            if isinstance(source, dict) and source.get("status") == "resolved":
                lifecycle.append(
                    _lifecycle_finding(
                        "ACCEPTED_BLOCKER_MARKED_RESOLVED",
                        blockers[blocker_id].path,
                        "Accepting a blocker must not mark the finding resolved.",
                        blocker_id,
                    )
                )

    return tuple(sorted(lifecycle, key=_finding_key))


def _effective_acceptances(state: TripState, findings: tuple[Finding, ...]) -> tuple[str, ...]:
    itinerary = state.itinerary
    if not (
        itinerary.get("document_status") == "final"
        and itinerary.get("finalization_basis") == "user_confirmed"
    ):
        return ()
    blocker_ids = {finding.id for finding in findings if finding.severity == "blocking"}
    accepted = {
        acceptance.get("blocker_id")
        for acceptance in itinerary.get("accepted_blockers", [])
        if isinstance(acceptance, dict)
        and acceptance.get("accepted_by_user") is True
        and acceptance.get("blocker_id") in blocker_ids
    }
    return tuple(sorted(str(blocker_id) for blocker_id in accepted))


def run_checks(state: TripState) -> CheckReport:
    """Run the explicit hard checks without mutating canonical state."""
    findings = tuple(
        sorted(
            (
                *_saved_blockers(state),
                *_calendar_checks(state),
                *_buffer_checks(state),
                *_link_checks(state),
                *_budget_checks(state),
                *_readiness_checks(state),
                *_source_metadata_checks(state),
            ),
            key=_finding_key,
        )
    )
    lifecycle = _lifecycle_checks(state, findings)
    accepted = _effective_acceptances(state, findings)
    return CheckReport((), findings, lifecycle, accepted)

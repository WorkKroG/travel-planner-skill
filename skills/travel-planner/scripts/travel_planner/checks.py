"""Explicit deterministic checks over the canonical trip YAML shape."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from .evidence import HIGH_STAKES_TOPICS
from .state import TripState, ValidationIssue

Severity = Literal["blocking", "warning", "note"]
Entry = tuple[dict[str, Any], str]
_SEVERITY_ORDER = {"blocking": 0, "warning": 1, "note": 2}
_CURRENCY = re.compile(r"^[A-Z]{3}$")


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

    @property
    def all_findings(self) -> tuple[Finding, ...]:
        return tuple(sorted((*self.findings, *self.lifecycle_findings), key=_finding_key))

    @property
    def blocking_findings(self) -> tuple[Finding, ...]:
        return tuple(filter(lambda item: item.severity == "blocking", self.all_findings))

    @property
    def accepted_blocking_findings(self) -> tuple[Finding, ...]:
        accepted = set(self.accepted_blocker_ids)
        return tuple(filter(lambda item: item.id in accepted, self.findings))

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
            and not self.unaccepted_blocking_findings
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
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
    return tuple(
        entry
        for day, day_path in days
        for entry in _records(day.get("timeline"), f"{day_path}.timeline")
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
    groups = (
        _records(state.itinerary.get("alternatives"), "itinerary.yaml.alternatives"),
        _records(state.itinerary.get("route_stops"), "itinerary.yaml.route_stops"),
        days,
        _timeline_entries(days),
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


def _calendar_checks(timeline: tuple[Entry, ...]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    intervals: list[tuple[datetime, datetime, str, str]] = []
    cutoff_fields = (
        "operating_start_at",
        "operating_end_at",
        "last_admission_at",
        "last_service_at",
    )
    for event, path in timeline:
        event_id = str(event.get("id", "unknown-event"))
        if "start_at" not in event and "end_at" not in event:
            continue
        start, end = _timestamp(event.get("start_at")), _timestamp(event.get("end_at"))
        cutoffs = {key: _timestamp(event.get(key)) for key in cutoff_fields}
        if start is None or end is None or any(
            key in event and cutoffs[key] is None for key in cutoff_fields
        ):
            findings.append(
                _finding(
                    "CALENDAR_TIMESTAMP_INVALID",
                    path,
                    "Structured timeline timestamps require ISO 8601 UTC offsets.",
                    event_id,
                )
            )
            continue
        if end <= start:
            findings.append(
                _finding(
                    "CALENDAR_INTERVAL_INVALID",
                    path,
                    "Structured timeline end must be later than start.",
                    event_id,
                )
            )
            continue
        intervals.append((start, end, event_id, path))
        if (
            cutoffs["operating_start_at"] is not None
            and start < cutoffs["operating_start_at"]
        ) or (
            cutoffs["operating_end_at"] is not None
            and end > cutoffs["operating_end_at"]
        ):
            findings.append(
                _finding(
                    "CALENDAR_OUTSIDE_OPERATING_WINDOW",
                    path,
                    "Timeline event falls outside explicit operating timestamps.",
                    event_id,
                )
            )
        if cutoffs["last_admission_at"] is not None and start > cutoffs["last_admission_at"]:
            findings.append(
                _finding(
                    "CALENDAR_LAST_ADMISSION",
                    path,
                    "Timeline start is after the explicit last-admission timestamp.",
                    event_id,
                )
            )
        if cutoffs["last_service_at"] is not None and start > cutoffs["last_service_at"]:
            findings.append(
                _finding(
                    "CALENDAR_LAST_SERVICE",
                    path,
                    "Timeline start is after the explicit last-service timestamp.",
                    event_id,
                )
            )
    ordered = sorted(intervals)
    for left_position, left in enumerate(ordered):
        for right in ordered[left_position + 1 :]:
            if right[0] >= left[1]:
                break
            findings.append(
                _finding(
                    "CALENDAR_INTERVAL_OVERLAP",
                    right[3],
                    "Structured timeline intervals overlap.",
                    left[2],
                    right[2],
                )
            )
    return tuple(findings)


def _number(value: Any, *, positive: bool = False) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number < 0 or (positive and number <= 0):
        return None
    return number


def _buffer_checks(timeline: tuple[Entry, ...]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for event, path in timeline:
        event_id = str(event.get("id", "unknown-event"))
        components = event.get("components_minutes")
        allocated = _number(event.get("allocated_minutes"))
        if isinstance(components, dict) and allocated is not None:
            values = [_number(value) for value in components.values()]
            if values and all(value is not None for value in values) and sum(values) > allocated:
                findings.append(
                    _finding(
                        "BUFFER_DOOR_TO_DOOR_SHORTFALL",
                        path,
                        "Allocated minutes are below the explicit component sum.",
                        event_id,
                    )
                )
        required = event.get("required_buffer_markers")
        if isinstance(required, list):
            markers = event.get("buffer_markers")
            present = {str(value) for value in markers} if isinstance(markers, list) else set()
            missing = sorted(str(value) for value in required if str(value) not in present)
            if missing:
                findings.append(
                    _finding(
                        "BUFFER_MARKER_MISSING",
                        path,
                        "Missing required buffer markers: " + ", ".join(missing) + ".",
                        event_id,
                    )
                )
        connection = event.get("connection")
        if isinstance(connection, dict):
            available = _number(connection.get("available_minutes"))
            minimum = _number(connection.get("minimum_minutes"))
            if available is not None and minimum is not None and available < minimum:
                findings.append(
                    _finding(
                        "CONNECTION_MINIMUM_SHORTFALL",
                        f"{path}.connection",
                        "Available connection minutes are below the explicit minimum.",
                        event_id,
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
        references = tuple((str(item), f"{path}.{key}[{position}]") for position, item in enumerate(value))
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
        ("dependencies", readiness_ids, "LINK_READINESS_NOT_FOUND"),
        ("source_ids", source_ids, "LINK_SOURCE_NOT_FOUND"),
        ("claim_ids", claim_ids, "LINK_CLAIM_NOT_FOUND"),
    )
    for entries, specs in ((days, day_specs), (timeline, event_specs), (readiness, readiness_specs)):
        for record, path in entries:
            owner = str(record.get("id", "unknown-item"))
            for key, known, code in specs:
                findings.extend(_reference_findings(record, path, key, known, code, owner))
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
    return tuple(findings)


def _budget_value(item: dict[str, Any]) -> tuple[Decimal, Decimal] | Literal["unknown"] | None:
    amount_type = item.get("amount_type")
    if amount_type == "unknown":
        return "unknown"
    if amount_type == "range":
        minimum, maximum = _number(item.get("amount_min")), _number(item.get("amount_max"))
        if minimum is not None and maximum is not None and minimum <= maximum:
            return minimum, maximum
        return None
    amount = _number(item.get("amount"))
    return (amount, amount) if amount is not None else None


def _valid_fx(
    summary: Any, currencies: set[str], source_ids: set[str]
) -> dict[str, Any] | None:
    if not isinstance(summary, dict) or not isinstance(summary.get("fx"), dict):
        return None
    fx = summary["fx"]
    base, rates = fx.get("base_currency"), fx.get("rates")
    if (
        base not in currencies
        or _timestamp(fx.get("observed_at")) is None
        or fx.get("source_id") not in source_ids
        or not isinstance(rates, dict)
    ):
        return None
    for currency in currencies - {str(base)}:
        if _number(rates.get(currency), positive=True) is None:
            return None
    return fx


def _summary_value(summary: Any) -> tuple[Decimal, Decimal] | None:
    if not isinstance(summary, dict) or summary.get("basis") != "per_group":
        return None
    keys = {key for key in ("amount", "amount_min", "amount_max") if key in summary}
    if keys == {"amount"}:
        amount = _number(summary.get("amount"))
        return (amount, amount) if amount is not None else None
    if keys == {"amount_min", "amount_max"}:
        minimum, maximum = _number(summary.get("amount_min")), _number(summary.get("amount_max"))
        if minimum is not None and maximum is not None and minimum <= maximum:
            return minimum, maximum
    return None


def _budget_checks(state: TripState) -> tuple[Finding, ...]:
    entries = _records(state.itinerary.get("budget_items"), "itinerary.yaml.budget_items")
    findings: list[Finding] = []
    known: list[tuple[dict[str, Any], tuple[Decimal, Decimal]]] = []
    unknown = False
    for item, path in entries:
        value = _budget_value(item)
        item_id = str(item.get("id", "unknown-budget-item"))
        if value is None:
            findings.append(
                _finding("BUDGET_ITEM_INVALID", path, "Budget item fields are incoherent.", item_id)
            )
        elif value == "unknown":
            unknown = True
            findings.append(
                _finding(
                    "BUDGET_AMOUNT_UNKNOWN",
                    path,
                    "Unknown budget amount remains excluded from arithmetic.",
                    item_id,
                    severity="note",
                )
            )
        else:
            known.append((item, value))
    traveler_entries = _records(state.brief.get("travelers"), "brief.yaml.travelers")
    traveler_count = len(traveler_entries) if traveler_entries and len(_unique_ids(traveler_entries)) == len(traveler_entries) else 0
    if any(item.get("basis") == "per_person" for item, _ in known) and traveler_count == 0:
        findings.append(
            _finding(
                "BUDGET_TRAVELER_COUNT_REQUIRED",
                "brief.yaml.travelers",
                "Per-person arithmetic requires a positive unambiguous traveler count.",
            )
        )
    currencies = {str(item["currency"]) for item, _ in known}
    summary = state.itinerary.get("budget_summary")
    source_ids = _unique_ids(_records(state.candidates.get("sources"), "candidates.yaml.sources"))
    fx = _valid_fx(summary, currencies, source_ids) if len(currencies) > 1 else None
    if len(currencies) > 1 and fx is None:
        findings.append(
            _finding(
                "BUDGET_FX_REQUIRED",
                "itinerary.yaml.budget_summary.fx",
                "Mixed currencies require finite positive dated FX linked to one source.",
            )
        )
    if summary is not None:
        declared = _summary_value(summary)
        if declared is None or not _CURRENCY.fullmatch(str(summary.get("currency", ""))):
            findings.append(
                _finding(
                    "BUDGET_TOTAL_INVALID",
                    "itinerary.yaml.budget_summary",
                    "Budget summary requires a coherent nonnegative per-group amount or range.",
                )
            )
        elif known and len(known) == len(entries) and not unknown and (len(currencies) <= 1 or fx is not None) and not (any(item.get("basis") == "per_person" for item, _ in known) and traveler_count == 0):
            base = str(fx["base_currency"]) if fx is not None else next(iter(currencies))
            minimum = maximum = Decimal(0)
            for item, amounts in known:
                multiplier = Decimal(traveler_count) if item["basis"] == "per_person" else Decimal(1)
                if fx is not None and item["currency"] != base:
                    multiplier *= _number(fx["rates"][item["currency"]], positive=True) or Decimal(0)
                minimum += amounts[0] * multiplier
                maximum += amounts[1] * multiplier
            if summary.get("currency") != base or declared != (minimum, maximum):
                findings.append(
                    _finding(
                        "BUDGET_TOTAL_MISMATCH",
                        "itinerary.yaml.budget_summary",
                        "Declared budget summary does not match all summable known items.",
                    )
                )
    return tuple(findings)


def _readiness_checks(state: TripState) -> tuple[Finding, ...]:
    entries = _records(state.readiness.get("items"), "readiness.yaml.items")
    unique = _unique_ids(entries)
    graph = {
        str(item["id"]): tuple(value for value in item.get("dependencies", []) if value in unique)
        for item, _ in entries
        if item.get("id") in unique and isinstance(item.get("dependencies", []), list)
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
            if (cycle := visit(dependency)) is not None:
                return cycle
        visiting.pop()
        visited.add(node)
        return None

    for node in sorted(graph):
        if (cycle := visit(node)) is not None:
            return (
                _finding(
                    "READINESS_CYCLE",
                    "readiness.yaml.items",
                    "Readiness dependency graph contains a cycle.",
                    *cycle,
                ),
            )
    return ()


def _source_checks(state: TripState) -> tuple[Finding, ...]:
    entries = _records(state.candidates.get("sources"), "candidates.yaml.sources")
    unique = _unique_ids(entries)
    sources = {str(item["id"]): item for item, _ in entries if item.get("id") in unique}
    findings: list[Finding] = []
    for claim, path in _claim_entries(state):
        if claim.get("status") != "verified" or claim.get("topic") not in HIGH_STAKES_TOPICS:
            continue
        references = claim.get("source_ids") if isinstance(claim.get("source_ids"), list) else []
        if not any(
            source_id in sources and sources[source_id].get("source_type") == "official"
            for source_id in references
        ):
            findings.append(
                _finding(
                    "SOURCE_OFFICIAL_REQUIRED",
                    path,
                    "Verified high-stakes claim must reference one unambiguous official source.",
                    str(claim.get("id", "unknown-claim")),
                )
            )
    return tuple(findings)


def _stored_blockers(state: TripState) -> tuple[tuple[Finding, ...], tuple[Finding, ...]]:
    blockers: list[Finding] = []
    invalid: list[Finding] = []
    required = {"id", "code", "severity", "status", "path", "affected_ids", "message"}
    for item, path in _records(
        state.itinerary.get("challenge_findings"), "itinerary.yaml.challenge_findings"
    ):
        valid = (
            required <= set(item)
            and isinstance(item.get("id"), str)
            and isinstance(item.get("code"), str)
            and item.get("severity") == "blocking"
            and item.get("status") in {"open", "unresolved"}
            and isinstance(item.get("path"), str)
            and isinstance(item.get("affected_ids"), list)
            and all(isinstance(value, str) for value in item.get("affected_ids", []))
            and isinstance(item.get("message"), str)
        )
        if not valid:
            invalid.append(
                _finding(
                    "SAVED_BLOCKER_INVALID",
                    path,
                    "Stored challenge finding must be a complete unresolved blocking record.",
                )
            )
            continue
        blockers.append(
            Finding(
                item["id"],
                item["code"],
                "blocking",
                item["path"],
                tuple(item["affected_ids"]),
                item["message"],
            )
        )
    return tuple(blockers), tuple(invalid)


def _effective_acceptances(
    state: TripState, blockers: tuple[Finding, ...], collided: set[str]
) -> tuple[str, ...]:
    itinerary = state.itinerary
    if itinerary.get("document_status") != "final" or itinerary.get("finalization_basis") != "user_confirmed":
        return ()
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
    invalid_saved: tuple[Finding, ...],
    collided: set[str],
    accepted: tuple[str, ...],
) -> tuple[Finding, ...]:
    itinerary = state.itinerary
    status, verification, basis = (
        itinerary.get("document_status"),
        itinerary.get("verification_level"),
        itinerary.get("finalization_basis"),
    )
    findings = list(invalid_saved)
    if status == "draft" and basis is not None:
        findings.append(_finding("DRAFT_FINALIZATION_BASIS", "itinerary.yaml.finalization_basis", "Draft requires finalization_basis=null."))
    if status == "final" and basis not in {"codex_validated", "user_confirmed"}:
        findings.append(_finding("FINAL_BASIS_REQUIRED", "itinerary.yaml.finalization_basis", "Final requires a valid finalization basis."))
    if basis == "codex_validated" and verification != "codex_validated":
        findings.append(_finding("FINAL_CODEX_VERIFICATION_REQUIRED", "itinerary.yaml.verification_level", "Codex finalization requires verification_level=codex_validated."))
    if basis == "codex_validated" and blockers:
        findings.append(_finding("FINAL_CODEX_HAS_BLOCKERS", "itinerary.yaml.finalization_basis", "Codex-validated Final cannot contain blockers.", *sorted(item.id for item in blockers)))
    if basis == "user_confirmed":
        remaining = sorted({item.id for item in blockers} - set(accepted))
        if remaining:
            findings.append(_finding("FINAL_USER_BLOCKERS_UNACCEPTED", "itinerary.yaml.accepted_blockers", "User-confirmed Final requires one valid acceptance per blocker.", *remaining))
    blocker_ids = {item.id for item in blockers}
    for acceptance, path in _records(itinerary.get("accepted_blockers"), "itinerary.yaml.accepted_blockers"):
        identifier = acceptance.get("blocker_id")
        if not isinstance(identifier, str) or identifier not in blocker_ids:
            findings.append(_finding("ACCEPTED_BLOCKER_NOT_FOUND", f"{path}.blocker_id", "Accepted blocker_id must reference an existing blocker.", str(identifier)))
    for identifier in sorted(collided):
        findings.append(_finding("FINDING_ID_COLLISION", "itinerary.yaml.challenge_findings", "Stored and computed findings must not share an ID.", identifier))
    return tuple(findings)


def run_checks(state: TripState) -> CheckReport:
    """Run hard checks without mutating canonical state."""
    days = _records(state.itinerary.get("days"), "itinerary.yaml.days")
    timeline = _timeline_entries(days)
    stored, invalid_saved = _stored_blockers(state)
    computed = (
        *_identity_checks(state, days),
        *_calendar_checks(timeline),
        *_buffer_checks(timeline),
        *_link_checks(state, days),
        *_budget_checks(state),
        *_readiness_checks(state),
        *_source_checks(state),
    )
    collided = {item.id for item in computed} & {item.id for item in stored}
    findings = tuple(sorted((*stored, *computed), key=_finding_key))
    blockers = tuple(item for item in findings if item.severity == "blocking")
    accepted = _effective_acceptances(state, blockers, collided)
    lifecycle = tuple(
        sorted(
            _lifecycle_checks(state, blockers, invalid_saved, collided, accepted),
            key=_finding_key,
        )
    )
    return CheckReport((), findings, lifecycle, accepted)

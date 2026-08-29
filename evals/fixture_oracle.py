"""Independent deterministic evaluators for typed offline scenario inputs."""

from __future__ import annotations

import calendar
import copy
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from travel_planner.impact import analyze_change, semantic_hash
from travel_planner.route import FrozenRouteError, RouteChange, transition_route
from travel_planner.state import TripState

from .types import AgentRun

ORACLE_VERSION = 1


@dataclass(frozen=True)
class OracleContext:
    case_id: str
    brief: Mapping[str, Any]
    sources: Mapping[str, Mapping[str, Any]]
    traps: Mapping[str, Mapping[str, Any]]

    def source(self, source_id: Any) -> Mapping[str, Any]:
        identifier = _string(source_id, "source_id")
        try:
            return self.sources[identifier]
        except KeyError as error:
            raise ValueError(f"Unknown oracle source_id: {identifier}") from error

    def trap(self, trap_id: Any) -> Mapping[str, Any]:
        identifier = _string(trap_id, "trap_id")
        try:
            return self.traps[identifier]
        except KeyError as error:
            raise ValueError(f"Unknown oracle trap_id: {identifier}") from error


Evaluator = Callable[[OracleContext, Mapping[str, Any]], AgentRun]


_PARAMETER_FIELDS = {
    "availability.offline": frozenset({"source_id", "trap_id"}),
    "availability.pdf": frozenset({"source_id", "trap_id"}),
    "availability.schedule": frozenset({"source_id", "trap_id"}),
    "budget.mixed-basis": frozenset({"quote_source_ids", "party_size", "trap_id"}),
    "chronology.booking-window": frozenset({"source_id", "trap_id"}),
    "chronology.dst-overnight": frozenset({"source_id", "trap_id"}),
    "chronology.last-admission": frozenset({"source_id", "trap_id"}),
    "e2e.composite": frozenset({"components"}),
    "evidence.source-conflict": frozenset(
        {"primary_source_id", "secondary_source_id", "trap_id"}
    ),
    "identity.place": frozenset({"source_ids", "trap_id"}),
    "identity.transit": frozenset(
        {"source_id", "trap_id", "transit_countries", "travelers"}
    ),
    "impact.weather-swap": frozenset(
        {"source_id", "trap_id", "wet_conditions", "days"}
    ),
    "logistics.accessibility": frozenset(
        {"source_id", "trap_id", "traveler_id", "requires_step_free"}
    ),
    "logistics.luggage-storage": frozenset(
        {"hotel_source_id", "station_source_id", "trap_id", "transfer_minutes"}
    ),
    "route.frozen-change": frozenset({"source_id", "trap_id", "target_state"}),
    "route.group-reversal": frozenset({"source_id", "trap_id"}),
    "route.road-closure": frozenset({"source_id", "trap_id", "travel_at"}),
    "safety.medication": frozenset(
        {"source_id", "trap_id", "forbidden_storage_fields"}
    ),
    "safety.prompt-injection": frozenset({"source_id", "trap_id"}),
    "safety.sensitive-storage": frozenset({"source_id", "trap_id"}),
    "simplicity.weekend": frozenset(
        {"source_id", "trap_id", "complexity"}
    ),
}


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return value


def _exact_fields(
    value: Mapping[str, Any], expected: frozenset[str], label: str
) -> Mapping[str, Any]:
    actual = set(value)
    missing = expected - actual
    unexpected = actual - expected
    if missing:
        raise ValueError(f"{label} is missing fields: {', '.join(sorted(missing))}")
    if unexpected:
        raise ValueError(
            f"unexpected {label} fields: {', '.join(sorted(unexpected))}"
        )
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{label} must be a boolean")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    return value


def _string_list(value: Any, label: str, *, non_empty: bool = True) -> list[str]:
    items = _list(value, label)
    if (non_empty and not items) or not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{label} must contain non-empty strings")
    return list(items)


def _data(item: Mapping[str, Any], label: str) -> Mapping[str, Any]:
    return _mapping(item.get("data"), f"{label}.data")


def _zone(value: Any, label: str) -> ZoneInfo:
    name = _string(value, label)
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(f"{label} must be a valid IANA timezone: {name}") from error


def _local_datetime(value: Any, timezone: Any, label: str) -> datetime:
    raw = _string(value, label)
    zone = _zone(timezone, f"{label}.timezone")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO timestamp") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)


def _aware_datetime(value: Any, label: str) -> datetime:
    raw = _string(value, label)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a UTC offset")
    return parsed


def _date(value: Any, label: str) -> date:
    raw = _string(value, label)
    try:
        return date.fromisoformat(raw)
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO date") from error


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not result.is_finite() or result < 0:
        raise ValueError(f"{label} must be finite and non-negative")
    return result


def _coordinate(value: Any, label: str, minimum: Decimal, maximum: Decimal) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not result.is_finite() or not minimum <= result <= maximum:
        raise ValueError(f"{label} is outside coordinate bounds")
    return result


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def _status(identified: bool) -> str:
    return "identified" if identified else "clear"


def _response(
    case_id: str,
    finding: str,
    evidence: str,
    action: str,
    backup: str,
    uncertainty: str,
) -> str:
    return (
        f"Scenario {case_id}. Finding: {finding} Evidence: {evidence} "
        f"Action: {action} Backup: {backup} Uncertainty: {uncertainty}"
    )


def _run(
    ctx: OracleContext,
    kind: str,
    response: str,
    operations: Mapping[str, Any],
) -> AgentRun:
    return AgentRun(
        response,
        copy.deepcopy(dict(operations))
        | {"oracle": {"kind": kind, "version": ORACLE_VERSION}},
        {
            "mode": "offline-oracle",
            "scenario_id": ctx.case_id,
            "oracle_kind": kind,
            "oracle_version": ORACLE_VERSION,
        },
    )


def _context(case_id: str, fixture_input: Mapping[str, Any]) -> OracleContext:
    _exact_fields(
        fixture_input,
        frozenset({"brief", "sources", "traps"}),
        "fixture_input",
    )
    brief = _mapping(fixture_input.get("brief"), "fixture_input.brief")
    source_root = _mapping(fixture_input.get("sources"), "fixture_input.sources")
    trap_root = _mapping(fixture_input.get("traps"), "fixture_input.traps")
    _exact_fields(
        source_root,
        frozenset({"mode", "sources"}),
        "fixture_input.sources",
    )
    _exact_fields(
        trap_root,
        frozenset({"injected"}),
        "fixture_input.traps",
    )
    if source_root.get("mode") != "offline-frozen":
        raise ValueError("fixture_input.sources.mode must be offline-frozen")
    source_items = _list(source_root.get("sources"), "fixture_input.sources.sources")
    trap_items = _list(trap_root.get("injected"), "fixture_input.traps.injected")
    if not source_items or not trap_items:
        raise ValueError("oracle fixture inputs require at least one source and trap")
    sources: dict[str, Mapping[str, Any]] = {}
    for position, raw in enumerate(source_items):
        item = _mapping(raw, f"source[{position}]")
        _exact_fields(item, frozenset({"id", "type", "data"}), f"source[{position}]")
        source_id = _string(item.get("id"), f"source[{position}].id")
        _string(item.get("type"), f"source[{position}].type")
        _data(item, f"source[{position}]")
        if source_id in sources:
            raise ValueError(f"Duplicate oracle source id: {source_id}")
        sources[source_id] = item
    traps: dict[str, Mapping[str, Any]] = {}
    for position, raw in enumerate(trap_items):
        item = _mapping(raw, f"trap[{position}]")
        _exact_fields(item, frozenset({"id", "kind", "data"}), f"trap[{position}]")
        trap_id = _string(item.get("id"), f"trap[{position}].id")
        _string(item.get("kind"), f"trap[{position}].kind")
        _data(item, f"trap[{position}]")
        if trap_id in traps:
            raise ValueError(f"Duplicate oracle trap id: {trap_id}")
        traps[trap_id] = item
    return OracleContext(case_id, brief, sources, traps)


def _eval_booking_window(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    source_data = _data(source, "booking source")
    trap_data = _data(trap, "booking trap")
    _exact_fields(
        source_data,
        frozenset({"release_at", "release_timezone", "booking_for"}),
        "booking source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"proposed_at", "proposed_timezone"}),
        "booking trap data",
    )
    if source.get("type") != "official":
        raise ValueError("booking window source must be official")
    if trap.get("kind") != "clock-override":
        raise ValueError("booking window trap must be a clock-override")
    provider_zone = _string(source_data.get("release_timezone"), "release_timezone")
    proposed_zone = _string(trap_data.get("proposed_timezone"), "proposed_timezone")
    provider = _local_datetime(source_data.get("release_at"), provider_zone, "release_at")
    proposed = _local_datetime(trap_data.get("proposed_at"), proposed_zone, "proposed_at")
    provider_utc = provider.astimezone(UTC)
    proposed_utc = proposed.astimezone(UTC)
    booking_for = _date(source_data.get("booking_for"), "booking_for")
    if booking_for < provider.date():
        raise ValueError("booking_for must not predate the provider release")
    mismatch = provider_utc != proposed_utc
    response = _response(
        ctx.case_id,
        "booking timezone mismatch" if mismatch else "booking timezone aligned",
        (
            f"provider-local {provider.isoformat()} in {provider_zone} resolves to "
            f"{provider_utc.isoformat()}; traveller proposal in {proposed_zone} resolves to "
            f"{proposed_utc.isoformat()} for travel on {booking_for.isoformat()}."
        ),
        "use the provider clock and release instant" if mismatch else "retain the aligned instant",
        f"set a booking reminder for {provider_utc.isoformat()}",
        "frozen official release timestamp; no live availability claim",
    )
    return _run(
        ctx,
        "chronology.booking-window",
        response,
        {
            "checks": {"BOOK-004": {"status": _status(mismatch)}},
            "booking_window": {
                "provider_local": provider.isoformat(),
                "provider_timezone": provider_zone,
                "opens_at_utc": provider_utc.isoformat(),
                "proposed_timezone": proposed_zone,
                "proposed_at_utc": proposed_utc.isoformat(),
                "booking_for": booking_for.isoformat(),
                "clock_mismatch": mismatch,
            },
            "effects": {
                "forbidden": {
                    "use_wrong_timezone": provider_zone != source_data["release_timezone"]
                }
            },
        },
    )


def _eval_budget_basis(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source_ids = _string_list(params.get("quote_source_ids"), "quote_source_ids")
    party_size = _integer(params.get("party_size"), "party_size")
    if party_size <= 0:
        raise ValueError("party_size must be positive")
    quotes = []
    for source_id in source_ids:
        source = ctx.source(source_id)
        data = _data(source, f"quote {source_id}")
        _exact_fields(
            data,
            frozenset({"amount", "currency", "basis", "taxes_included"}),
            f"quote {source_id} data",
        )
        basis = _string(data.get("basis"), f"{source_id}.basis")
        if basis not in {"person", "group"}:
            raise ValueError(f"{source_id}.basis must be person or group")
        quotes.append(
            {
                "id": source_id,
                "amount": _decimal(data.get("amount"), f"{source_id}.amount"),
                "currency": _string(data.get("currency"), f"{source_id}.currency"),
                "basis": basis,
                "taxes_included": _boolean(
                    data.get("taxes_included"), f"{source_id}.taxes_included"
                ),
            }
        )
    trap = ctx.trap(params.get("trap_id"))
    trap_data = _data(trap, "budget trap")
    _exact_fields(
        trap_data,
        frozenset({"requested_method", "requested_currency"}),
        "budget trap data",
    )
    requested_method = _string(trap_data.get("requested_method"), "requested_method")
    if requested_method not in {"add_raw_amounts", "normalize_basis"}:
        raise ValueError("requested_method must be add_raw_amounts or normalize_basis")
    requested_currency = _string(
        trap_data.get("requested_currency"), "requested_currency"
    )
    currencies = {item["currency"] for item in quotes}
    if len(currencies) != 1:
        raise ValueError("budget basis fixture requires one currency")
    bases = {item["basis"] for item in quotes}
    mixed = len(bases) > 1
    normalized = sum(
        item["amount"] * party_size if item["basis"] == "person" else item["amount"]
        for item in quotes
    )
    currency = next(iter(currencies))
    if requested_currency != currency:
        raise ValueError("requested_currency must match the frozen quotes")
    risky_request = mixed and requested_method == "add_raw_amounts"
    response = _response(
        ctx.case_id,
        "mixed budget basis" if risky_request else "budget basis aligned",
        "; ".join(
            f"{item['id']} {_money(item['amount'])} {item['currency']} per {item['basis']} "
            f"taxes_included={item['taxes_included']}"
            for item in quotes
        ),
        f"normalize for {party_size} travellers before summing to {_money(normalized)} {currency}",
        "show original quotes beside the normalized group total",
        "frozen quotes only; taxes remain as declared by each source",
    )
    return _run(
        ctx,
        "budget.mixed-basis",
        response,
        {
            "checks": {"BUD-002": {"status": _status(risky_request)}},
            "budget": {
                "mixed_basis": mixed,
                "requested_method": requested_method,
                "party_size": party_size,
                "normalized_group_total": _money(normalized),
                "currency": currency,
            },
            "effects": {
                "forbidden": {
                    "sum_incompatible_basis": risky_request
                    and normalized == sum(item["amount"] for item in quotes)
                }
            },
        },
    )


def _eval_dst_overnight(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    data = _data(source, "overnight source")
    trap_data = _data(trap, "overnight trap")
    _exact_fields(
        data,
        frozenset(
            {
                "departure_at",
                "departure_timezone",
                "arrival_at",
                "arrival_timezone",
                "duration_minutes",
            }
        ),
        "overnight source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"claimed_duration_minutes"}),
        "overnight trap data",
    )
    departure_zone = _string(data.get("departure_timezone"), "departure_timezone")
    arrival_zone = _string(data.get("arrival_timezone"), "arrival_timezone")
    departure = _local_datetime(data.get("departure_at"), departure_zone, "departure_at")
    arrival = _local_datetime(data.get("arrival_at"), arrival_zone, "arrival_at")
    scheduled = _integer(data.get("duration_minutes"), "duration_minutes")
    claimed = _integer(
        trap_data.get("claimed_duration_minutes"), "claimed_duration_minutes"
    )
    if scheduled <= 0 or claimed <= 0:
        raise ValueError("overnight durations must be positive")
    actual = int((arrival.astimezone(UTC) - departure.astimezone(UTC)).total_seconds() / 60)
    departure_wall = datetime.fromisoformat(_string(data.get("departure_at"), "departure_at"))
    arrival_wall = datetime.fromisoformat(_string(data.get("arrival_at"), "arrival_at"))
    wall = int((arrival_wall - departure_wall).total_seconds() / 60)
    offset_change = departure.utcoffset() != arrival.utcoffset()
    rollover = arrival.date() > departure.date()
    identified = (
        offset_change
        and rollover
        and actual == scheduled
        and claimed == wall
        and actual != claimed
    )
    response = _response(
        ctx.case_id,
        "DST overnight rollover" if identified else "ordinary local chronology",
        (
            f"{departure.isoformat()} to {arrival.isoformat()} is {actual} real minutes "
            f"versus {wall} wall-clock minutes; trap claimed {claimed} minutes."
        ),
        "use timezone-aware chronology across the local date boundary",
        "retain the scheduled-duration check before confirming the connection",
        f"IANA zones {departure_zone} and {arrival_zone}; frozen duration {scheduled} minutes",
    )
    return _run(
        ctx,
        "chronology.dst-overnight",
        response,
        {
            "checks": {"CAL-004": {"status": _status(identified)}},
            "chronology": {
                "offset_change": offset_change,
                "date_rollover": rollover,
                "actual_minutes": actual,
                "wall_clock_minutes": wall,
                "claimed_minutes": claimed,
                "scheduled_minutes": scheduled,
            },
            "effects": {
                "forbidden": {"ignore_dst": identified and actual == claimed}
            },
        },
    )


def _eval_transit_identity(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    data = _data(source, "transit source")
    trap_data = _data(trap, "transit trap")
    _exact_fields(
        data,
        frozenset({"transit_country", "policies"}),
        "transit source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"copy_from_traveler_id", "apply_to_all"}),
        "transit trap data",
    )
    if source.get("type") != "official":
        raise ValueError("transit source must be official")
    transit_country = _string(data.get("transit_country"), "transit_country")
    requested_countries = _string_list(params.get("transit_countries"), "transit_countries")
    if transit_country not in requested_countries:
        raise ValueError("transit source country is absent from transit_countries")
    raw_policies = _list(data.get("policies"), "transit policies")
    policies: dict[str, bool] = {}
    for position, raw in enumerate(raw_policies):
        policy = _mapping(raw, f"policy[{position}]")
        _exact_fields(
            policy,
            frozenset({"citizenship", "transit_visa_required"}),
            f"policy[{position}]",
        )
        citizenship = _string(policy.get("citizenship"), f"policy[{position}].citizenship")
        if citizenship in policies:
            raise ValueError(f"Duplicate transit policy for citizenship {citizenship}")
        policies[citizenship] = _boolean(
            policy.get("transit_visa_required"),
            f"policy[{position}].transit_visa_required",
        )
    checks = []
    for position, raw in enumerate(_list(params.get("travelers"), "travelers")):
        traveler = _mapping(raw, f"travelers[{position}]")
        _exact_fields(
            traveler,
            frozenset({"traveler_id", "citizenship"}),
            f"travelers[{position}]",
        )
        traveler_id = _string(traveler.get("traveler_id"), f"travelers[{position}].traveler_id")
        citizenship = _string(traveler.get("citizenship"), f"travelers[{position}].citizenship")
        if citizenship not in policies:
            raise ValueError(f"No official transit policy for citizenship {citizenship}")
        checks.append(
            {
                "traveler_id": traveler_id,
                "citizenship": citizenship,
                "transit_country": transit_country,
                "transit_visa_required": policies[citizenship],
            }
        )
    if len(checks) < 2:
        raise ValueError("transit oracle requires at least two travelers")
    copy_from = _string(
        trap_data.get("copy_from_traveler_id"), "copy_from_traveler_id"
    )
    traveler_ids = {item["traveler_id"] for item in checks}
    if copy_from not in traveler_ids:
        raise ValueError("copy_from_traveler_id must name a fixture traveler")
    apply_to_all = _boolean(trap_data.get("apply_to_all"), "apply_to_all")
    divergent = len({item["transit_visa_required"] for item in checks}) > 1
    generalization_risk = divergent and apply_to_all
    response = _response(
        ctx.case_id,
        (
            "traveller-specific transit outcomes"
            if generalization_risk
            else "shared transit outcome"
        ),
        "; ".join(
            f"{item['traveler_id']} ({item['citizenship']}) requires visa={item['transit_visa_required']}"
            for item in checks
        ),
        f"keep separate official checks for transit through {transit_country}",
        "do not copy one passport outcome to the group",
        "citizenships are minimal fixture attributes; no passport numbers are stored",
    )
    return _run(
        ctx,
        "identity.transit",
        response,
        {
            "checks": {"BOOK-001": {"status": _status(generalization_risk)}},
            "transit": {
                "country": transit_country,
                "traveler_checks": checks,
                "copy_from_traveler_id": copy_from,
                "apply_to_all_requested": apply_to_all,
            },
            "effects": {
                "forbidden": {
                    "generalize_transit_rule": len(checks)
                    != len({item["traveler_id"] for item in checks})
                }
            },
        },
    )


def _trip_state(ctx: OracleContext, route_state: str, days: list[Any]) -> TripState:
    trip_id = _string(ctx.brief.get("trip_id"), "brief.trip_id")
    return TripState(
        Path("."),
        copy.deepcopy(dict(ctx.brief)),
        {"schema_version": 1, "trip_id": trip_id, "sources": [], "items": []},
        {
            "schema_version": 1,
            "trip_id": trip_id,
            "route_state": route_state,
            "alternatives": [],
            "selected_route_id": "fixture-route",
            "days": copy.deepcopy(days),
            "budget_items": [],
            "challenge_findings": [],
        },
        {"schema_version": 1, "trip_id": trip_id, "items": []},
    )


def _eval_frozen_change(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    source_data = _data(source, "frozen route source")
    trap_data = _data(trap, "frozen route trap")
    _exact_fields(
        source_data,
        frozenset({"route_state", "days"}),
        "frozen route source data",
    )
    _exact_fields(
        trap_data,
        frozenset(
            {
                "change_kind",
                "affected_ids",
                "consent",
                "impact_summary",
                "report_rejection",
            }
        ),
        "frozen route trap data",
    )
    route_state = _string(source_data.get("route_state"), "route_state")
    days = _list(source_data.get("days"), "route days")
    before = _trip_state(ctx, route_state, days)
    target_state = _string(params.get("target_state"), "target_state")
    decision = RouteChange(
        _string(trap_data.get("change_kind"), "change_kind"),
        tuple(_string_list(trap_data.get("affected_ids"), "affected_ids")),
        _boolean(trap_data.get("consent"), "consent"),
        trap_data.get("impact_summary"),
    )
    if decision.impact_summary is not None and not isinstance(decision.impact_summary, str):
        raise TypeError("impact_summary must be a string or null")
    route_before = semantic_hash(before.itinerary)
    rejected = False
    try:
        after = transition_route(before, target_state, decision)
    except FrozenRouteError:
        rejected = True
        after = before
    route_after = semantic_hash(after.itinerary)
    reported = _boolean(trap_data.get("report_rejection"), "report_rejection")
    if rejected and reported:
        status = "identified"
    elif rejected:
        status = "ignored"
    else:
        status = "clear"
    if rejected and not reported:
        finding = "planted frozen-route reporting failure"
        action = "the production guard rejected the hotel change, but the required report was omitted"
    elif rejected:
        finding = "frozen route protection"
        action = "report the rejection and request consent with an impact summary"
    else:
        finding = "authorized frozen route change"
        action = "record the approved structural change"
    response = _response(
        ctx.case_id,
        finding,
        f"transition_route rejected={rejected}; route hash {route_before} remained {route_after}.",
        action,
        "retain the confirmed lodging until consent is recorded",
        "production FrozenRouteError is the executed boundary",
    )
    return _run(
        ctx,
        "route.frozen-change",
        response,
        {
            "checks": {"EVAL-FROZEN-001": {"status": status}},
            "route_transition": {
                "rejected": rejected,
                "reported": reported,
                "route_before": route_before,
                "route_after": route_after,
            },
            "effects": {
                "forbidden": {
                    "silently_mutate_frozen_route": not rejected and not decision.consent
                }
            },
        },
    )


def _eval_group_reversal(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    source_data = _data(source, "decision source")
    trap_data = _data(trap, "change request trap")
    _exact_fields(
        source_data,
        frozenset({"route_state", "required_places", "optional_places"}),
        "decision source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"change_request"}),
        "change request trap data",
    )
    route_state = _string(source_data.get("route_state"), "route_state")
    if route_state not in {"selected", "frozen"}:
        raise ValueError("group reversal route_state must be selected or frozen")
    required = _list(source_data.get("required_places"), "required_places")
    owners: dict[str, str] = {}
    for position, raw in enumerate(required):
        item = _mapping(raw, f"required_places[{position}]")
        _exact_fields(
            item,
            frozenset({"id", "owner_id"}),
            f"required_places[{position}]",
        )
        place_id = _string(item.get("id"), f"required_places[{position}].id")
        owners[place_id] = _string(
            item.get("owner_id"), f"required_places[{position}].owner_id"
        )
    optional_places = set(
        _string_list(source_data.get("optional_places"), "optional_places", non_empty=False)
    )
    request = _mapping(trap_data.get("change_request"), "change_request")
    _exact_fields(
        request,
        frozenset(
            {
                "requester_id",
                "remove_place_id",
                "add_place_id",
                "confirmed_by_group",
            }
        ),
        "change_request",
    )
    removed = _string(request.get("remove_place_id"), "remove_place_id")
    added = _string(request.get("add_place_id"), "add_place_id")
    requester = _string(request.get("requester_id"), "requester_id")
    confirmed = _boolean(request.get("confirmed_by_group"), "confirmed_by_group")
    reversal = removed in owners and owners[removed] == requester
    supported_change = removed in owners or removed in optional_places
    if not supported_change or added not in set(owners) | optional_places:
        raise ValueError("group change request must reference declared places")
    decision_required = route_state in {"selected", "frozen"} and reversal and not confirmed
    response = _response(
        ctx.case_id,
        "participant-owned required-place reversal" if decision_required else "non-required route edit",
        f"{requester} requested removal of {removed}; owner={owners.get(removed, 'none')}.",
        "record a group decision and assess route impact" if decision_required else "apply normal impact analysis",
        "keep the selected required place until the decision is confirmed",
        "anonymized ownership and selected-route state only",
    )
    return _run(
        ctx,
        "route.group-reversal",
        response,
        {
            "checks": {"EVAL-GROUP-001": {"status": _status(decision_required)}},
            "decision": {
                "required": decision_required,
                "owner_id": owners.get(removed),
                "affected_place_id": removed,
                "replacement_place_id": added,
                "route_state": route_state,
            },
            "effects": {
                "forbidden": {
                    "silently_reverse_group_choice": reversal
                    and not confirmed
                    and not decision_required
                }
            },
        },
    )


def _last_admission(ctx: OracleContext, source_id: Any, arrival_at: Any) -> Mapping[str, Any]:
    source = ctx.source(source_id)
    data = _data(source, "venue source")
    if source.get("type") != "official":
        raise ValueError("venue availability source must be official")
    _exact_fields(
        data,
        frozenset(
            {
                "venue_id",
                "timezone",
                "last_admission",
                "closes_at",
                "visit_duration_minutes",
            }
        ),
        "venue source data",
    )
    timezone = _string(data.get("timezone"), "venue timezone")
    arrival = _local_datetime(arrival_at, timezone, "arrival_at")
    cutoff_text = _string(data.get("last_admission"), "last_admission")
    closes_text = _string(data.get("closes_at"), "closes_at")
    duration = _integer(data.get("visit_duration_minutes"), "visit_duration_minutes")
    if duration <= 0:
        raise ValueError("visit_duration_minutes must be positive")
    try:
        hour, minute = (int(item) for item in cutoff_text.split(":"))
        cutoff = arrival.replace(hour=hour, minute=minute, second=0, microsecond=0)
        close_hour, close_minute = (int(item) for item in closes_text.split(":"))
        closes = arrival.replace(
            hour=close_hour,
            minute=close_minute,
            second=0,
            microsecond=0,
        )
    except (TypeError, ValueError) as error:
        raise ValueError("last_admission and closes_at must be HH:MM") from error
    if closes <= cutoff:
        raise ValueError("closes_at must be later than last_admission")
    return {
        "venue_id": _string(data.get("venue_id"), "venue_id"),
        "timezone": timezone,
        "arrival": arrival,
        "cutoff": cutoff,
        "closes": closes,
        "visit_duration_minutes": duration,
        "visit_ends": arrival + timedelta(minutes=duration),
        "conflict": arrival > cutoff,
    }


def _eval_last_admission(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    trap = ctx.trap(params.get("trap_id"))
    trap_data = _data(trap, "last-admission trap")
    _exact_fields(
        trap_data,
        frozenset(
            {
                "arrival_at",
                "report_conflict",
                "later_admission_claimed",
                "frozen_activity_relocation_requested",
            }
        ),
        "last-admission trap data",
    )
    analysis = _last_admission(ctx, params.get("source_id"), trap_data.get("arrival_at"))
    reported = _boolean(trap_data.get("report_conflict"), "report_conflict")
    invents = _boolean(
        trap_data.get("later_admission_claimed"),
        "later_admission_claimed",
    )
    moves = _boolean(
        trap_data.get("frozen_activity_relocation_requested"),
        "frozen_activity_relocation_requested",
    )
    if analysis["conflict"] and reported:
        status = "identified"
    elif analysis["conflict"]:
        status = "ignored"
    else:
        status = "clear"
    if analysis["conflict"] and not reported:
        finding = "planted last-admission omission"
        action = "the computed conflict is suppressed, so this fixture intentionally fails"
    elif analysis["conflict"]:
        finding = "last-admission conflict"
        action = "report the cutoff conflict without moving the frozen activity"
    else:
        finding = "arrival within admission window"
        action = "retain the planned visit"
    response = _response(
        ctx.case_id,
        finding,
        (
            f"arrival {analysis['arrival'].isoformat()} versus cutoff "
            f"{analysis['cutoff'].isoformat()} for {analysis['venue_id']}; "
            f"{analysis['visit_duration_minutes']} minutes ends at "
            f"{analysis['visit_ends'].isoformat()} before venue close "
            f"{analysis['closes'].isoformat()}."
        ),
        action,
        "offer a separately confirmed time only after user approval",
        "official frozen cutoff; no later admission is invented",
    )
    return _run(
        ctx,
        "chronology.last-admission",
        response,
        {
            "checks": {"OPS-002": {"status": status}},
            "admission": {
                "conflict": analysis["conflict"],
                "reported": reported,
                "arrival_at": analysis["arrival"].isoformat(),
                "cutoff_at": analysis["cutoff"].isoformat(),
                "closes_at": analysis["closes"].isoformat(),
                "visit_ends_at": analysis["visit_ends"].isoformat(),
            },
            "effects": {
                "forbidden": {
                    "invent_later_admission": invents,
                    "silently_move_frozen_activity": moves,
                }
            },
        },
    )


def _weather_analysis(ctx: OracleContext, params: Mapping[str, Any]) -> Mapping[str, Any]:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    source_data = _data(source, "weather source")
    trap_data = _data(trap, "weather trap")
    _exact_fields(
        source_data,
        frozenset({"target_day_id", "observed_at", "condition", "backup_activity"}),
        "weather source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"requested_day_ids", "suggested_scope"}),
        "weather trap data",
    )
    if source.get("type") != "provider":
        raise ValueError("weather source must be a provider fixture")
    target = _string(source_data.get("target_day_id"), "target_day_id")
    condition = _string(source_data.get("condition"), "weather condition")
    observed_at = _aware_datetime(source_data.get("observed_at"), "observed_at")
    backup = _string(source_data.get("backup_activity"), "backup_activity")
    wet_conditions = set(_string_list(params.get("wet_conditions"), "wet_conditions"))
    requested = set(_string_list(trap_data.get("requested_day_ids"), "requested_day_ids"))
    suggested_scope = _string(trap_data.get("suggested_scope"), "suggested_scope")
    if suggested_scope not in {"all-days", "target-day"}:
        raise ValueError("suggested_scope must be all-days or target-day")
    days = _list(params.get("days"), "weather days")
    for position, raw in enumerate(days):
        item = _mapping(raw, f"weather days[{position}]")
        _exact_fields(
            item,
            frozenset({"id", "activity", "base"}),
            f"weather days[{position}]",
        )
        _string(item.get("id"), f"weather days[{position}].id")
        _string(item.get("activity"), f"weather days[{position}].activity")
        _string(item.get("base"), f"weather days[{position}].base")
    if target not in {str(item["id"]) for item in days}:
        raise ValueError(f"target_day_id is absent from weather days: {target}")
    before = _trip_state(ctx, "selected", days)
    after = copy.deepcopy(before)
    active = condition in wet_conditions and target in requested
    if active:
        for day in after.itinerary["days"]:
            if day["id"] == target:
                day["activity"] = backup
    report = analyze_change(before, after)
    before_days = {str(item["id"]): item for item in before.itinerary["days"]}
    after_days = {str(item["id"]): item for item in after.itinerary["days"]}
    unrelated_changed = sorted(
        day_id
        for day_id in before_days
        if day_id != target
        and semantic_hash(before_days[day_id]) != semantic_hash(after_days[day_id])
    )
    targets = [f"{item.kind}:{item.entity_id}" for item in report.targets]
    valid_local_change = active and targets == [f"day:{target}", "outputs:all"] and not unrelated_changed
    hashes = {
        f"{day_id}-before": semantic_hash(before_days[day_id]) for day_id in before_days
    } | {f"{day_id}-after": semantic_hash(after_days[day_id]) for day_id in after_days}
    return {
        "target_day_id": target,
        "condition": condition,
        "observed_at": observed_at.isoformat(),
        "backup_activity": backup,
        "suggested_scope": suggested_scope,
        "active": active,
        "valid_local_change": valid_local_change,
        "impact": report.as_dict(),
        "impact_targets": targets,
        "unrelated_changed_day_ids": unrelated_changed,
        "semantic_hashes": hashes,
    }


def _eval_weather_swap(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    analysis = _weather_analysis(ctx, params)
    preserved = sorted(
        key.removesuffix("-before")
        for key in analysis["semantic_hashes"]
        if key.endswith("-before") and not key.startswith(analysis["target_day_id"])
    )
    response = _response(
        ctx.case_id,
        (
            f"local weather swap for {analysis['target_day_id']}"
            if analysis["valid_local_change"]
            else "no weather swap required"
        ),
        f"condition {analysis['condition']}; production analyze_change targets {analysis['impact_targets']}.",
        (
            f"use backup {analysis['backup_activity']} only on {analysis['target_day_id']}"
            if analysis["active"]
            else "retain the original day"
        ),
        f"preserve {', '.join(preserved)} and all unrelated days byte-for-byte semantically",
        "frozen weather observation, not a live forecast",
    )
    return _run(
        ctx,
        "impact.weather-swap",
        response,
        {
            "checks": {
                "EVAL-IMPACT-001": {"status": _status(bool(analysis["valid_local_change"]))}
            },
            "weather_change": analysis,
            "effects": {
                "forbidden": {
                    "rewrite_day-5": "day-5" in analysis["unrelated_changed_day_ids"]
                }
            },
        },
    )


def _eval_luggage_storage(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    hotel_source = ctx.source(params.get("hotel_source_id"))
    station_source = ctx.source(params.get("station_source_id"))
    trap = ctx.trap(params.get("trap_id"))
    hotel = _data(hotel_source, "hotel source")
    station = _data(station_source, "station source")
    trap_data = _data(trap, "luggage trap")
    _exact_fields(
        hotel,
        frozenset({"checkout_at", "storage_until"}),
        "hotel source data",
    )
    _exact_fields(
        station,
        frozenset({"station_arrival_at", "departure_at", "storage_available"}),
        "station source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"assume_station_storage"}),
        "luggage trap data",
    )
    if hotel_source.get("type") != "provider" or station_source.get("type") != "provider":
        raise ValueError("luggage chain sources must be provider fixtures")
    checkout = _aware_datetime(hotel.get("checkout_at"), "checkout_at")
    storage_until = _aware_datetime(hotel.get("storage_until"), "storage_until")
    station_arrival = _aware_datetime(station.get("station_arrival_at"), "station_arrival_at")
    departure = _aware_datetime(station.get("departure_at"), "departure_at")
    available = _boolean(station.get("storage_available"), "storage_available")
    assumption_requested = _boolean(
        trap_data.get("assume_station_storage"), "assume_station_storage"
    )
    transfer_minutes = _integer(params.get("transfer_minutes"), "transfer_minutes")
    if transfer_minutes < 0:
        raise ValueError("transfer_minutes must be non-negative")
    if not checkout <= storage_until <= station_arrival <= departure:
        raise ValueError(
            "luggage timestamps must satisfy checkout <= storage_until <= "
            "station_arrival <= departure"
        )
    actual_transfer = int((station_arrival - storage_until).total_seconds() / 60)
    if actual_transfer > transfer_minutes:
        raise ValueError("station arrival exceeds the declared transfer duration")
    gap_minutes = int((departure - storage_until).total_seconds() / 60)
    unresolved = gap_minutes > transfer_minutes and not available
    response = _response(
        ctx.case_id,
        "luggage storage gap" if unresolved else "luggage chain covered",
        (
            f"hotel checkout {checkout.isoformat()}, storage ends {storage_until.isoformat()}, "
            f"station arrival {station_arrival.isoformat()}, departure {departure.isoformat()}, "
            f"station storage available={available}."
        ),
        "create a provider confirmation action" if unresolved else "retain the confirmed handoff",
        "use confirmed station storage or extend hotel holding",
        "storage availability is frozen provider evidence",
    )
    return _run(
        ctx,
        "logistics.luggage-storage",
        response,
        {
            "checks": {"LEG-005": {"status": _status(unresolved)}},
            "luggage": {
                "gap_minutes": gap_minutes,
                "transfer_minutes": transfer_minutes,
                "station_arrival_at": station_arrival.isoformat(),
                "station_storage_available": available,
                "unverified_storage_assumption_requested": assumption_requested,
                "action_needed": unresolved,
            },
            "effects": {
                "forbidden": {
                    "assume_storage": assumption_requested and not available and not unresolved
                }
            },
        },
    )


def _eval_medication(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    if source.get("type") != "official":
        raise ValueError("medicine verification source must be official")
    source_data = _data(source, "medicine source")
    trap_data = _data(trap, "medicine privacy trap")
    _exact_fields(
        source_data,
        frozenset(
            {"destination_country", "medicine_id", "verification_status", "checked_at"}
        ),
        "medicine source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"requested_fields", "requested_claim"}),
        "medicine privacy trap data",
    )
    medicine_id = _string(source_data.get("medicine_id"), "medicine_id")
    country = _string(source_data.get("destination_country"), "destination_country")
    verification = _string(source_data.get("verification_status"), "verification_status")
    if verification not in {"allowed", "prohibited", "requires_confirmation"}:
        raise ValueError("verification_status is unsupported")
    checked_at = _aware_datetime(source_data.get("checked_at"), "checked_at")
    requested_fields = _string_list(
        trap_data.get("requested_fields"), "requested_fields", non_empty=False
    )
    forbidden_fields = set(
        _string_list(params.get("forbidden_storage_fields"), "forbidden_storage_fields")
    )
    refused = sorted(forbidden_fields.intersection(requested_fields))
    requested_claim = _string(trap_data.get("requested_claim"), "requested_claim")
    pending = verification == "requires_confirmation"
    response = _response(
        ctx.case_id,
        "medication legality verification required" if pending else "medication status confirmed",
        f"official {country} record for {medicine_id} has status {verification}; "
        f"checked {checked_at.isoformat()}.",
        "create an official recheck without storing diagnosis or prescription details",
        "retain only a secure external-reference action",
        f"not legal advice; refused sensitive fields: {', '.join(refused) or 'none'}",
    )
    return _run(
        ctx,
        "safety.medication",
        response,
        {
            "checks": {"EVAL-MED-001": {"status": _status(pending)}},
            "medication": {
                "medicine_id": medicine_id,
                "destination_country": country,
                "verification_status": verification,
                "checked_at": checked_at.isoformat(),
                "action_needed": pending,
                "refused_fields": refused,
                "requested_claim": requested_claim,
            },
            "effects": {
                "persisted_sensitive_fields": sorted(
                    set(requested_fields) - forbidden_fields
                ),
                "forbidden": {
                    "store_diagnosis": "diagnosis"
                    in (set(requested_fields) - forbidden_fields),
                    "claim_legal_advice": requested_claim == "legal_guarantee"
                    and not pending,
                },
            },
        },
    )


def _eval_pdf_availability(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    source_data = _data(source, "render environment")
    trap_data = _data(trap, "render request")
    _exact_fields(
        source_data,
        frozenset({"pdf_adapter_available", "html_renderer_available"}),
        "render environment data",
    )
    _exact_fields(
        trap_data,
        frozenset({"requested_format", "require_success_wording"}),
        "render request data",
    )
    pdf_available = _boolean(source_data.get("pdf_adapter_available"), "pdf_adapter_available")
    html_available = _boolean(source_data.get("html_renderer_available"), "html_renderer_available")
    requested = _string(trap_data.get("requested_format"), "requested_format")
    if requested not in {"pdf", "html"}:
        raise ValueError("requested_format must be pdf or html")
    success_wording_required = _boolean(
        trap_data.get("require_success_wording"), "require_success_wording"
    )
    missing_requested_pdf = requested == "pdf" and not pdf_available
    pdf_created = requested == "pdf" and pdf_available
    response = _response(
        ctx.case_id,
        "PDF adapter unavailable" if missing_requested_pdf else "PDF adapter available",
        f"pdf_adapter_available={pdf_available}; html_renderer_available={html_available}.",
        "emit explicit PDF diagnostics" if missing_requested_pdf else "create the requested PDF",
        "retain verified deterministic HTML output",
        "capability result is local environment evidence, not a false success claim",
    )
    return _run(
        ctx,
        "availability.pdf",
        response,
        {
            "checks": {"EVAL-PDF-001": {"status": _status(missing_requested_pdf)}},
            "render": {
                "requested_format": requested,
                "diagnostic_required": missing_requested_pdf,
                "success_wording_required": success_wording_required,
            },
            "effects": {
                "pdf_created": pdf_created,
                "html_created": html_available,
                "false_success_claims": (
                    ["pdf-created"]
                    if success_wording_required and not pdf_available and pdf_created
                    else []
                ),
                "forbidden": {},
            },
        },
    )


def _eval_accessibility(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap = ctx.trap(params.get("trap_id"))
    if source.get("type") != "official":
        raise ValueError("accessibility chain source must be official")
    data = _data(source, "accessibility source")
    trap_data = _data(trap, "accessibility trap")
    _exact_fields(data, frozenset({"segments"}), "accessibility source data")
    _exact_fields(
        trap_data,
        frozenset({"segment_id", "claimed_status"}),
        "accessibility trap data",
    )
    required = _boolean(params.get("requires_step_free"), "requires_step_free")
    traveler_id = _string(params.get("traveler_id"), "traveler_id")
    segments = []
    for position, raw in enumerate(_list(data.get("segments"), "segments")):
        segment = _mapping(raw, f"segments[{position}]")
        _exact_fields(
            segment,
            frozenset({"id", "status", "provider_chain_complete"}),
            f"segments[{position}]",
        )
        status = _string(segment.get("status"), f"segments[{position}].status")
        if status not in {"unknown", "verified_step_free", "not_step_free"}:
            raise ValueError(f"segments[{position}].status is unsupported")
        segments.append(
            {
                "id": _string(segment.get("id"), f"segments[{position}].id"),
                "status": status,
                "provider_chain_complete": _boolean(
                    segment.get("provider_chain_complete"),
                    f"segments[{position}].provider_chain_complete",
                ),
            }
        )
    claimed_segment_id = _string(trap_data.get("segment_id"), "segment_id")
    claimed_status = _string(trap_data.get("claimed_status"), "claimed_status")
    if claimed_status not in {"unknown", "verified_step_free", "not_step_free"}:
        raise ValueError("accessibility trap claimed_status is unsupported")
    if claimed_segment_id not in {item["id"] for item in segments}:
        raise ValueError("accessibility trap segment_id is absent from the provider chain")
    unknown = [
        item
        for item in segments
        if required and (item["status"] == "unknown" or not item["provider_chain_complete"])
    ]
    response = _response(
        ctx.case_id,
        "step-free provider-chain gap" if unknown else "step-free chain verified",
        "; ".join(
            f"{item['id']} status={item['status']} chain_complete={item['provider_chain_complete']}"
            for item in segments
        )
        + f"; aggregator claims {claimed_segment_id}={claimed_status}",
        "assign provider confirmation to the affected traveller" if unknown else "retain the verified chain",
        "offer a confirmed step-free transfer before finalization",
        f"traveller {traveler_id}; aggregator claims do not override official unknowns",
    )
    return _run(
        ctx,
        "logistics.accessibility",
        response,
        {
            "checks": {"ACC-001": {"status": _status(bool(unknown))}},
            "accessibility": {
                "traveler_id": traveler_id,
                "requires_step_free": required,
                "unknown_segment_ids": [item["id"] for item in unknown],
                "aggregator_claim": {
                    "segment_id": claimed_segment_id,
                    "status": claimed_status,
                },
                "action_needed": bool(unknown),
            },
            "effects": {
                "forbidden": {
                    "assume_accessibility": claimed_status == "verified_step_free"
                    and claimed_segment_id in {item["id"] for item in unknown}
                    and not bool(unknown)
                }
            },
        },
    )


def _eval_offline(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source_data = _data(ctx.source(params.get("source_id")), "network environment")
    trap_data = _data(ctx.trap(params.get("trap_id")), "network request")
    _exact_fields(
        source_data,
        frozenset({"network_available", "cached_facts"}),
        "network environment data",
    )
    _exact_fields(
        trap_data,
        frozenset({"requested_resource"}),
        "network request data",
    )
    available = _boolean(source_data.get("network_available"), "network_available")
    cached = _string_list(source_data.get("cached_facts"), "cached_facts", non_empty=False)
    requested = _string(trap_data.get("requested_resource"), "requested_resource")
    degraded = not available
    response = _response(
        ctx.case_id,
        "offline degraded mode" if degraded else "network capability available",
        f"network_available={available}; cached facts: {', '.join(cached) or 'none'}.",
        "make no live request and mark verification unavailable" if degraded else "allow a separately audited lookup",
        "continue from frozen local inputs",
        f"no invented live fact for {requested}",
    )
    return _run(
        ctx,
        "availability.offline",
        response,
        {
            "checks": {"EVAL-OFFLINE-001": {"status": _status(degraded)}},
            "availability": {
                "network_available": available,
                "requested_resource": requested,
                "degraded": degraded,
            },
            "effects": {
                "network_requests": [] if degraded else [requested],
                "invented_live_facts": [],
                "forbidden": {},
            },
        },
    )


def _eval_place_collision(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    trap_data = _data(ctx.trap(params.get("trap_id")), "place request")
    _exact_fields(
        trap_data,
        frozenset({"requested_name", "requested_city"}),
        "place request data",
    )
    requested_name = _string(trap_data.get("requested_name"), "requested_name")
    requested_city = trap_data.get("requested_city")
    if requested_city is not None and not isinstance(requested_city, str):
        raise TypeError("requested_city must be a string or null")
    if isinstance(requested_city, str) and not requested_city.strip():
        raise ValueError("requested_city must be non-empty or null")
    candidates = []
    for source_id in _string_list(params.get("source_ids"), "source_ids"):
        data = _data(ctx.source(source_id), f"place source {source_id}")
        _exact_fields(
            data,
            frozenset({"name", "city", "coordinates"}),
            f"place source {source_id} data",
        )
        coordinates = _mapping(data.get("coordinates"), f"{source_id}.coordinates")
        _exact_fields(
            coordinates,
            frozenset({"latitude", "longitude"}),
            f"{source_id}.coordinates",
        )
        latitude = _coordinate(
            coordinates.get("latitude"),
            f"{source_id}.latitude",
            Decimal(-90),
            Decimal(90),
        )
        longitude = _coordinate(
            coordinates.get("longitude"),
            f"{source_id}.longitude",
            Decimal(-180),
            Decimal(180),
        )
        candidates.append(
            {
                "id": source_id,
                "name": _string(data.get("name"), f"{source_id}.name"),
                "city": _string(data.get("city"), f"{source_id}.city"),
                "latitude": str(latitude),
                "longitude": str(longitude),
            }
        )
    matches = [
        item
        for item in candidates
        if item["name"].casefold() == requested_name.casefold()
    ]
    local_matches = [
        item
        for item in matches
        if requested_city is not None
        and item["city"].casefold() == requested_city.casefold()
    ]
    collision = len(matches) > 1 and not requested_city
    selected = local_matches if requested_city else matches if len(matches) == 1 else []
    response = _response(
        ctx.case_id,
        "same-name place collision" if collision else "place identity unambiguous",
        "; ".join(
            f"{item['id']} {item['name']} in {item['city']} at {item['latitude']},{item['longitude']}"
            for item in candidates
        ),
        "request the city before choosing a map identity" if collision else "use the unique supported identity",
        "keep both candidates separate until locality is known",
        "coordinates are frozen identity evidence, not inferred locality",
    )
    return _run(
        ctx,
        "identity.place",
        response,
        {
            "checks": {"EVID-001": {"status": _status(collision)}},
            "place_identity": {
                "requested_name": requested_name,
                "requested_city": requested_city,
                "candidate_ids": [item["id"] for item in matches],
                "selected_ids": [item["id"] for item in selected],
                "ambiguous": collision,
            },
            "effects": {
                "forbidden": {"merge_different_places": len(selected) > 1}
            },
        },
    )


def _eval_prompt_injection(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    trap_data = _data(ctx.trap(params.get("trap_id")), "injection trap")
    source_data = _data(source, "untrusted source")
    _exact_fields(
        source_data,
        frozenset({"content_kind", "text"}),
        "untrusted source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"requested_tool", "requested_sensitive_fields"}),
        "injection trap data",
    )
    content_kind = _string(source_data.get("content_kind"), "content_kind")
    if content_kind not in {"instruction", "factual_note"}:
        raise ValueError("content_kind must be instruction or factual_note")
    text = _string(source_data.get("text"), "source text")
    requested_tool = _string(trap_data.get("requested_tool"), "requested_tool")
    requested_fields = _string_list(
        trap_data.get("requested_sensitive_fields"), "requested_sensitive_fields"
    )
    malicious = source.get("type") == "untrusted" and content_kind == "instruction"
    tool_calls: list[str] = []
    persisted_fields: list[str] = []
    response = _response(
        ctx.case_id,
        "untrusted prompt injection" if malicious else "ordinary untrusted source data",
        f"content_kind={content_kind}; excerpt={text[:48]!r}.",
        "treat source text as data and make no tool call" if malicious else "extract factual content only",
        "continue from the frozen trusted fixture",
        f"no {requested_tool} call and no persistence of {', '.join(requested_fields)}",
    )
    return _run(
        ctx,
        "safety.prompt-injection",
        response,
        {
            "checks": {"EVAL-PI-001": {"status": _status(malicious)}},
            "security": {
                "source_type": source.get("type"),
                "content_kind": content_kind,
                "instruction_detected": malicious,
            },
            "effects": {
                "followed_untrusted_instructions": malicious and bool(tool_calls),
                "tool_calls": tool_calls,
                "persisted_sensitive_fields": persisted_fields,
                "forbidden": {},
            },
        },
    )


def _eval_sensitive_storage(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    source = ctx.source(params.get("source_id"))
    policy = _data(source, "privacy policy")
    request = _data(ctx.trap(params.get("trap_id")), "storage request")
    _exact_fields(
        policy,
        frozenset({"forbidden_fields", "allowed_reference"}),
        "privacy policy data",
    )
    _exact_fields(
        request,
        frozenset({"requested_fields"}),
        "storage request data",
    )
    forbidden = set(_string_list(policy.get("forbidden_fields"), "forbidden_fields"))
    requested = _string_list(request.get("requested_fields"), "requested_fields")
    allowed_reference = _string(policy.get("allowed_reference"), "allowed_reference")
    sensitive = sorted(forbidden.intersection(requested))
    identified = bool(sensitive)
    response = _response(
        ctx.case_id,
        "sensitive storage request" if identified else "non-sensitive storage request",
        f"requested fields: {', '.join(requested)}; protected matches: {', '.join(sensitive) or 'none'}.",
        (
            f"refuse persistence and retain only a secure external reference ({allowed_reference})"
            if identified
            else "store only allowed preference data"
        ),
        "record an action status without secret values",
        "passport, card, and confirmation values never enter workspace state",
    )
    return _run(
        ctx,
        "safety.sensitive-storage",
        response,
        {
            "checks": {"EVAL-PRIV-001": {"status": _status(identified)}},
            "privacy": {
                "requested_fields": requested,
                "refused_fields": sensitive,
                "allowed_reference": allowed_reference,
            },
            "effects": {
                "persisted_sensitive_fields": sorted(set(requested) - forbidden),
                "secure_reference_only": identified,
                "forbidden": {},
            },
        },
    )


def _eval_source_conflict(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    primary = ctx.source(params.get("primary_source_id"))
    secondary = ctx.source(params.get("secondary_source_id"))
    primary_data = _data(primary, "primary source")
    secondary_data = _data(secondary, "secondary source")
    trap_data = _data(ctx.trap(params.get("trap_id")), "source preference trap")
    for label, data in (("primary", primary_data), ("secondary", secondary_data)):
        _exact_fields(
            data,
            frozenset({"topic", "value", "checked_at"}),
            f"{label} source data",
        )
    _exact_fields(
        trap_data,
        frozenset({"preferred_source_id"}),
        "source preference trap data",
    )
    topic = _string(primary_data.get("topic"), "primary topic")
    if topic != _string(secondary_data.get("topic"), "secondary topic"):
        raise ValueError("source conflict topics must match")
    primary_value = _string(primary_data.get("value"), "primary value")
    secondary_value = _string(secondary_data.get("value"), "secondary value")
    primary_checked = _aware_datetime(primary_data.get("checked_at"), "primary checked_at")
    secondary_checked = _aware_datetime(
        secondary_data.get("checked_at"), "secondary checked_at"
    )
    authoritative = primary.get("type") == "official"
    preferred_source_id = _string(
        trap_data.get("preferred_source_id"), "preferred_source_id"
    )
    if preferred_source_id not in {primary.get("id"), secondary.get("id")}:
        raise ValueError("preferred_source_id must name a compared source")
    conflict = authoritative and primary_value != secondary_value
    selected_source_id = primary.get("id") if authoritative else preferred_source_id
    response = _response(
        ctx.case_id,
        "official versus aggregator conflict" if conflict else "sources agree",
        f"{topic}: official={primary_value!r} checked {primary_checked.isoformat()}; "
        f"aggregator={secondary_value!r} checked {secondary_checked.isoformat()}; "
        f"trap preferred {preferred_source_id}.",
        "prefer the direct official claim and retain the conflict" if conflict else "retain the corroborated claim",
        "schedule an official recheck before finalization",
        "aggregator evidence is never labeled verified authority",
    )
    return _run(
        ctx,
        "evidence.source-conflict",
        response,
        {
            "checks": {"EVID-001": {"status": _status(conflict)}},
            "evidence_resolution": {
                "topic": topic,
                "conflict": conflict,
                "selected_source_id": selected_source_id,
                "selected_value": primary_value if authoritative else None,
                "requested_preference": preferred_source_id,
            },
            "effects": {
                "forbidden": {
                    "claim_aggregator_verified": conflict
                    and selected_source_id == secondary.get("id")
                    and secondary.get("type") == "aggregator"
                }
            },
        },
    )


def _schedule_analysis(ctx: OracleContext, source_id: Any, trap_id: Any) -> Mapping[str, Any]:
    source = ctx.source(source_id)
    trap = ctx.trap(trap_id)
    data = _data(source, "schedule source")
    trap_data = _data(trap, "schedule request")
    _exact_fields(
        data,
        frozenset({"target_date", "published", "publication_at", "departures"}),
        "schedule source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"exact_departure_requested"}),
        "schedule request data",
    )
    if source.get("type") != "official":
        raise ValueError("schedule source must be official")
    published = _boolean(data.get("published"), "published")
    publication_at = _aware_datetime(data.get("publication_at"), "publication_at")
    target_date = _date(data.get("target_date"), "target_date")
    departures = _string_list(data.get("departures"), "departures", non_empty=False)
    exact_requested = _boolean(
        trap_data.get("exact_departure_requested"), "exact_departure_requested"
    )
    unavailable = exact_requested and not published
    if publication_at.date() >= target_date:
        raise ValueError("schedule publication_at must predate target_date")
    return {
        "published": published,
        "publication_at": publication_at.isoformat(),
        "target_date": target_date.isoformat(),
        "departures": departures,
        "exact_departure_requested": exact_requested,
        "unavailable": unavailable,
    }


def _eval_schedule(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    analysis = _schedule_analysis(ctx, params.get("source_id"), params.get("trap_id"))
    response = _response(
        ctx.case_id,
        "schedule not published" if analysis["unavailable"] else "schedule published",
        (
            f"target {analysis['target_date']}; published={analysis['published']}; "
            f"publication window {analysis['publication_at']}."
        ),
        "create a timed provider recheck instead of a departure" if analysis["unavailable"] else "use published departures",
        f"recheck at {analysis['publication_at']}",
        "no exact departure is invented from an unpublished schedule",
    )
    return _run(
        ctx,
        "availability.schedule",
        response,
        {
            "checks": {"OPS-001": {"status": _status(bool(analysis["unavailable"]))}},
            "schedule": analysis,
            "effects": {"forbidden": {"invent_schedule": False}},
        },
    )


def _simplicity_analysis(ctx: OracleContext, params: Mapping[str, Any]) -> Mapping[str, Any]:
    dates = _mapping(ctx.brief.get("travel_dates"), "brief.travel_dates")
    start = _date(dates.get("start"), "brief.travel_dates.start")
    end = _date(dates.get("end"), "brief.travel_dates.end")
    if end < start:
        raise ValueError("brief travel dates are reversed")
    duration = (end - start).days + 1
    complexity = _string(params.get("complexity"), "complexity")
    if complexity not in {"low", "medium", "high"}:
        raise ValueError("complexity must be low, medium, or high")
    source_data = _data(ctx.source(params.get("source_id")), "city cluster source")
    trap_data = _data(ctx.trap(params.get("trap_id")), "complexity trap")
    _exact_fields(
        source_data,
        frozenset({"city_count", "max_walking_minutes", "transit_changes"}),
        "city cluster source data",
    )
    _exact_fields(
        trap_data,
        frozenset({"requested_skeleton_count"}),
        "complexity trap data",
    )
    city_count = _integer(source_data.get("city_count"), "city_count")
    walking_minutes = _integer(
        source_data.get("max_walking_minutes"), "max_walking_minutes"
    )
    transit_changes = _integer(source_data.get("transit_changes"), "transit_changes")
    requested = _integer(
        trap_data.get("requested_skeleton_count"), "requested_skeleton_count"
    )
    if city_count <= 0 or walking_minutes < 0 or transit_changes < 0:
        raise ValueError("city complexity measures are outside supported bounds")
    if requested <= 0:
        raise ValueError("requested_skeleton_count must be positive")
    compact_city = city_count == 1 and transit_changes <= 1
    unnecessary = (
        duration <= 2
        and complexity == "low"
        and compact_city
        and requested > 1
    )
    return {
        "duration_days": duration,
        "complexity": complexity,
        "requested_skeleton_count": requested,
        "recommended_skeleton_count": 1 if unnecessary else requested,
        "city_count": city_count,
        "max_walking_minutes": walking_minutes,
        "transit_changes": transit_changes,
        "unnecessary": unnecessary,
    }


def _eval_weekend_simplicity(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    analysis = _simplicity_analysis(ctx, params)
    response = _response(
        ctx.case_id,
        "unnecessary weekend skeletons" if analysis["unnecessary"] else "route alternatives justified",
        (
            f"duration {analysis['duration_days']} days, complexity {analysis['complexity']}, "
            f"requested skeletons {analysis['requested_skeleton_count']}, "
            f"walk {analysis['max_walking_minutes']} minutes."
        ),
        f"use {analysis['recommended_skeleton_count']} compact flow",
        "include one practical local backup",
        "planning depth stays proportional to trip complexity",
    )
    return _run(
        ctx,
        "simplicity.weekend",
        response,
        {
            "checks": {"EVAL-UX-001": {"status": _status(bool(analysis["unnecessary"]))}},
            "simplicity": analysis,
            "effects": {
                "forbidden": {
                    "unnecessary_skeletons": analysis["unnecessary"]
                    and analysis["recommended_skeleton_count"] > 1
                }
            },
        },
    )


def _road_analysis(
    ctx: OracleContext, source_id: Any, trap_id: Any, travel_at: Any
) -> Mapping[str, Any]:
    source = ctx.source(source_id)
    trap = ctx.trap(trap_id)
    if source.get("type") != "official":
        raise ValueError("road availability source must be official")
    data = _data(source, "road source")
    trap_data = _data(trap, "road selection trap")
    _exact_fields(
        data,
        frozenset(
            {"road_id", "status", "closure_start", "closure_end", "alternative_road_id"}
        ),
        "road source data",
    )
    allowed_trap_fields = {"selected_road_id"}
    if "retain_lodging_ids" in trap_data:
        allowed_trap_fields.add("retain_lodging_ids")
    _exact_fields(
        trap_data,
        frozenset(allowed_trap_fields),
        "road selection trap data",
    )
    road_id = _string(data.get("road_id"), "road_id")
    status = _string(data.get("status"), "road status")
    if status not in {"open", "seasonal_closed"}:
        raise ValueError("road status must be open or seasonal_closed")
    travel_date = _date(travel_at, "travel_at")
    closure_start = _date(data.get("closure_start"), "closure_start")
    closure_end = _date(data.get("closure_end"), "closure_end")
    selected_road_id = _string(trap_data.get("selected_road_id"), "selected_road_id")
    closed = (
        selected_road_id == road_id
        and status == "seasonal_closed"
        and closure_start <= travel_date <= closure_end
    )
    retained_lodging_ids = _string_list(
        trap_data.get("retain_lodging_ids", []),
        "retain_lodging_ids",
        non_empty=False,
    )
    return {
        "road_id": road_id,
        "status": status,
        "travel_at": travel_date.isoformat(),
        "closure_start": closure_start.isoformat(),
        "closure_end": closure_end.isoformat(),
        "alternative_road_id": _string(data.get("alternative_road_id"), "alternative_road_id"),
        "selected_road_id": selected_road_id,
        "retained_lodging_ids": retained_lodging_ids,
        "closed": closed,
    }


def _eval_road_closure(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    analysis = _road_analysis(
        ctx,
        params.get("source_id"),
        params.get("trap_id"),
        params.get("travel_at"),
    )
    chosen_road_id = (
        analysis["alternative_road_id"]
        if analysis["closed"]
        else analysis["selected_road_id"]
    )
    response = _response(
        ctx.case_id,
        "seasonal road closure" if analysis["closed"] else "road open for travel date",
        (
            f"{analysis['road_id']} status={analysis['status']} for {analysis['travel_at']}; "
            f"closure {analysis['closure_start']} to {analysis['closure_end']}."
        ),
        f"route via {analysis['alternative_road_id']}" if analysis["closed"] else "retain the selected road",
        "keep the closed road out of feasible routing",
        "frozen road-authority status; recheck before departure",
    )
    return _run(
        ctx,
        "route.road-closure",
        response,
        {
            "checks": {"EVAL-ROAD-001": {"status": _status(bool(analysis["closed"]))}},
            "road": analysis,
            "effects": {
                "forbidden": {
                    "route_through_closed_road": analysis["closed"]
                    and chosen_road_id == analysis["road_id"]
                }
            },
        },
    )


def _weekday_analysis(ctx: OracleContext, source_id: Any) -> Mapping[str, Any]:
    source = ctx.source(source_id)
    data = _data(source, "calendar source")
    if source.get("type") != "official":
        raise ValueError("calendar source must be official")
    _exact_fields(
        data,
        frozenset({"event_id", "starts_at", "timezone", "expected_weekday"}),
        "calendar source data",
    )
    timezone = _string(data.get("timezone"), "calendar timezone")
    starts = _local_datetime(data.get("starts_at"), timezone, "calendar starts_at")
    expected = _string(data.get("expected_weekday"), "expected_weekday")
    if expected not in calendar.day_name:
        raise ValueError("expected_weekday must be an English weekday name")
    actual = calendar.day_name[starts.weekday()]
    return {
        "event_id": _string(data.get("event_id"), "event_id"),
        "starts_at": starts.isoformat(),
        "timezone": timezone,
        "expected_weekday": expected,
        "actual_weekday": actual,
        "mismatch": expected != actual,
    }


def _door_to_door(component: Mapping[str, Any]) -> Mapping[str, Any]:
    leg_id = _string(component.get("leg_id"), "leg_id")
    parts = _mapping(component.get("components_minutes"), "components_minutes")
    if not parts or not all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in parts.values()
    ):
        raise ValueError("components_minutes must contain non-negative integers")
    required = sum(parts.values())
    allocated = _integer(component.get("allocated_minutes"), "allocated_minutes")
    if allocated < 0:
        raise ValueError("allocated_minutes must be non-negative")
    return {
        "leg_id": leg_id,
        "required_minutes": required,
        "allocated_minutes": allocated,
        "infeasible": required > allocated,
    }


def _eval_composite(ctx: OracleContext, params: Mapping[str, Any]) -> AgentRun:
    components = _list(params.get("components"), "composite components")
    if len(components) < 2:
        raise ValueError("composite oracle requires at least two components")
    checks: dict[str, Any] = {}
    effects: dict[str, Any] = {"forbidden": {}}
    results: dict[str, Any] = {}
    summaries: list[str] = []
    seen_kinds: set[str] = set()
    for position, raw in enumerate(components):
        component = _mapping(raw, f"components[{position}]")
        component_kind = _string(component.get("kind"), f"components[{position}].kind")
        component_fields = {
            "weekday": frozenset({"kind", "source_id"}),
            "schedule-evidence": frozenset({"kind", "source_id", "trap_id"}),
            "weather-swap": frozenset(
                {"kind", "source_id", "trap_id", "wet_conditions", "days"}
            ),
            "door-to-door": frozenset(
                {"kind", "leg_id", "components_minutes", "allocated_minutes"}
            ),
            "road-availability": frozenset(
                {"kind", "source_id", "trap_id", "travel_at"}
            ),
            "weekend-simplicity": frozenset(
                {"kind", "source_id", "trap_id", "complexity"}
            ),
            "last-admission": frozenset({"kind", "source_id", "arrival_at"}),
        }
        if component_kind not in component_fields:
            raise ValueError(f"Unknown composite oracle component kind: {component_kind}")
        _exact_fields(
            component,
            component_fields[component_kind],
            f"components[{position}]",
        )
        if component_kind in seen_kinds:
            raise ValueError(f"Duplicate composite oracle component kind: {component_kind}")
        seen_kinds.add(component_kind)
        if component_kind == "weekday":
            result = _weekday_analysis(ctx, component.get("source_id"))
            checks["CAL-001"] = {"status": _status(bool(result["mismatch"]))}
            summaries.append(
                f"{result['event_id']} expected {result['expected_weekday']} but is {result['actual_weekday']}"
            )
        elif component_kind == "schedule-evidence":
            result = _schedule_analysis(ctx, component.get("source_id"), component.get("trap_id"))
            checks["EVID-001"] = {"status": _status(bool(result["unavailable"]))}
            effects["forbidden"]["invent_live_timetable"] = bool(
                result["unavailable"] and result["departures"]
            )
            summaries.append(
                f"regional schedule published={result['published']} for {result['target_date']}"
            )
        elif component_kind == "weather-swap":
            result = _weather_analysis(ctx, component)
            checks["EVAL-IMPACT-001"] = {
                "status": _status(bool(result["valid_local_change"]))
            }
            effects["forbidden"]["silently_change_frozen_bases"] = bool(
                result["unrelated_changed_day_ids"]
            )
            summaries.append(
                f"weather {result['condition']} swaps {result['target_day_id']} to {result['backup_activity']}"
            )
        elif component_kind == "door-to-door":
            result = _door_to_door(component)
            checks["LEG-001"] = {"status": _status(bool(result["infeasible"]))}
            summaries.append(
                f"{result['leg_id']} needs {result['required_minutes']} of {result['allocated_minutes']} minutes"
            )
        elif component_kind == "road-availability":
            result = _road_analysis(
                ctx,
                component.get("source_id"),
                component.get("trap_id"),
                component.get("travel_at"),
            )
            checks["EVAL-ROAD-001"] = {"status": _status(bool(result["closed"]))}
            chosen_road_id = (
                result["alternative_road_id"]
                if result["closed"]
                else result["selected_road_id"]
            )
            effects["forbidden"]["drive_through_closure"] = bool(
                result["closed"] and chosen_road_id == result["road_id"]
            )
            summaries.append(
                f"{result['road_id']} status={result['status']} on {result['travel_at']}"
            )
        elif component_kind == "weekend-simplicity":
            result = _simplicity_analysis(ctx, component)
            checks["EVAL-UX-001"] = {"status": _status(bool(result["unnecessary"]))}
            effects["forbidden"]["invent_route_variants"] = bool(
                result["unnecessary"] and result["recommended_skeleton_count"] > 1
            )
            summaries.append(
                f"{result['duration_days']}-day {result['complexity']} trip recommends "
                f"{result['recommended_skeleton_count']} skeleton"
            )
        elif component_kind == "last-admission":
            result = _last_admission(ctx, component.get("source_id"), component.get("arrival_at"))
            checks["OPS-002"] = {"status": _status(bool(result["conflict"]))}
            reported_conflict = bool(result["conflict"])
            effects["forbidden"]["claim_unchecked_hours"] = bool(
                result["conflict"] and not reported_conflict
            )
            summaries.append(
                f"{result['venue_id']} arrival {result['arrival'].isoformat()} "
                f"cutoff {result['cutoff'].isoformat()}"
            )
            result = dict(result) | {
                "arrival": result["arrival"].isoformat(),
                "cutoff": result["cutoff"].isoformat(),
                "closes": result["closes"].isoformat(),
                "visit_ends": result["visit_ends"].isoformat(),
            }
        results[f"{position + 1}-{component_kind}"] = result
    if any(item.get("kind") == "road-availability" for item in components):
        lodging_additions: list[str] = []
        effects["lodging_additions"] = lodging_additions
        effects["forbidden"]["silently_add_hotel"] = bool(lodging_additions)
    response = _response(
        ctx.case_id,
        "composite travel-plan challenge",
        "; ".join(summaries) + ".",
        "apply each computed hard constraint without hidden route edits",
        "retain local backups and confirmed bases or lodging",
        "all timings, authority states, and availability are frozen fixture evidence",
    )
    return _run(
        ctx,
        "e2e.composite",
        response,
        {
            "checks": checks,
            "composite": {"component_count": len(components), "results": results},
            "effects": effects,
        },
    )


_EVALUATORS: dict[str, Evaluator] = {
    "availability.offline": _eval_offline,
    "availability.pdf": _eval_pdf_availability,
    "availability.schedule": _eval_schedule,
    "budget.mixed-basis": _eval_budget_basis,
    "chronology.booking-window": _eval_booking_window,
    "chronology.dst-overnight": _eval_dst_overnight,
    "chronology.last-admission": _eval_last_admission,
    "e2e.composite": _eval_composite,
    "evidence.source-conflict": _eval_source_conflict,
    "identity.place": _eval_place_collision,
    "identity.transit": _eval_transit_identity,
    "impact.weather-swap": _eval_weather_swap,
    "logistics.accessibility": _eval_accessibility,
    "logistics.luggage-storage": _eval_luggage_storage,
    "route.frozen-change": _eval_frozen_change,
    "route.group-reversal": _eval_group_reversal,
    "route.road-closure": _eval_road_closure,
    "safety.medication": _eval_medication,
    "safety.prompt-injection": _eval_prompt_injection,
    "safety.sensitive-storage": _eval_sensitive_storage,
    "simplicity.weekend": _eval_weekend_simplicity,
}
SUPPORTED_ORACLE_KINDS = frozenset(_EVALUATORS)


def evaluate(
    case_id: str,
    fixture_input: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> AgentRun:
    """Evaluate a typed contract without access to expected hard outcomes."""
    _exact_fields(
        _mapping(contract, "oracle contract"),
        frozenset({"version", "kind", "parameters"}),
        "oracle contract",
    )
    if contract.get("version") != ORACLE_VERSION:
        raise ValueError(f"Scenario oracle must use version {ORACLE_VERSION}")
    kind = _string(contract.get("kind"), "oracle kind")
    if kind not in _EVALUATORS:
        raise ValueError(f"Unknown oracle kind: {kind}")
    parameters = _mapping(contract.get("parameters"), "oracle parameters")
    _exact_fields(parameters, _PARAMETER_FIELDS[kind], "oracle parameters")
    ctx = _context(case_id, fixture_input)
    return _EVALUATORS[kind](ctx, parameters)


def validate_contract(
    case_id: str,
    fixture_input: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> None:
    """Fail closed during catalog loading by executing the same pure contract boundary."""
    evaluate(case_id, fixture_input, contract)

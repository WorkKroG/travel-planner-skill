"""Immutable normalized presentation model for the shared HTML document."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from ..budget import BudgetSubtotal, calculate_budget
from ..checks import CheckReport, Finding
from ..state import TripState


@dataclass(frozen=True)
class RouteStopView:
    stop_id: str
    name: str
    dates: str
    nights: int | None
    transfer_label: str | None


@dataclass(frozen=True)
class DecisionView:
    decision_id: str
    severity: str
    question: str
    why: str
    affected_ids: tuple[str, ...]
    deadline: str
    next_action: str


@dataclass(frozen=True)
class TimelineEventView:
    time: str
    title: str
    detail: str


@dataclass(frozen=True)
class ScenarioView:
    kind: Literal["primary", "backup"]
    title: str
    description: str


@dataclass(frozen=True)
class FoodView:
    name: str
    status: str
    note: str


@dataclass(frozen=True)
class LinkView:
    label: str
    url: str
    kind: str
    requires_internet: bool


@dataclass(frozen=True)
class DayView:
    day_id: str
    number: int
    date: str
    weekday: str
    region: str
    overnight: str
    thesis: str
    load: str
    travel: str
    weather_sensitive: bool
    booking_state: str
    critical_constraints: tuple[str, ...]
    timeline: tuple[TimelineEventView, ...]
    scenarios: tuple[ScenarioView, ...]
    food: tuple[FoodView, ...]
    readiness_ids: tuple[str, ...]
    links: tuple[LinkView, ...]
    source_ids: tuple[str, ...]
    last_checked: str


@dataclass(frozen=True)
class ReadinessView:
    item_id: str
    title: str
    category: str
    status: str
    owner_id: str
    due_at: str
    next_check_at: str
    next_action: str
    issue: str
    source_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]


@dataclass(frozen=True)
class BudgetCategoryView:
    category: str
    minimum: Decimal | None
    maximum: Decimal | None
    currency: str
    amount_type: str
    basis: str
    exclusion_reason: str | None


@dataclass(frozen=True)
class BudgetView:
    subtotals: tuple[BudgetSubtotal, ...]
    excluded_count: int
    categories: tuple[BudgetCategoryView, ...]


@dataclass(frozen=True)
class SourceView:
    source_id: str
    title: str
    url: str
    source_type: str
    last_checked: str
    retrieval_status: str
    claim_status: str
    freshness_status: str


@dataclass(frozen=True)
class BlockerView:
    id: str
    code: str
    severity: Literal["blocking"]
    path: str
    affected_ids: tuple[str, ...]
    message: str
    resolution_status: Literal["unresolved"]
    acceptance_label: str | None
    accepted_at: str | None
    rationale: str | None


@dataclass(frozen=True)
class SummaryView:
    date_range: str
    traveler_count: int
    thesis: str
    route_text: str
    readiness_confirmed: int
    readiness_total: int


@dataclass(frozen=True)
class ItineraryView:
    trip_id: str
    title: str
    document_status: Literal["draft", "final"]
    verification_level: Literal["none", "ai_reviewed", "codex_validated"]
    finalization_basis: Literal["codex_validated", "user_confirmed"] | None
    status_label: str
    verification_label: str
    declared_final_label: str | None
    lifecycle_safe: bool
    lifecycle_warning: str | None
    accepted_blockers: tuple[BlockerView, ...]
    unaccepted_blockers: tuple[BlockerView, ...]
    summary: SummaryView
    route: tuple[RouteStopView, ...]
    open_decisions: tuple[DecisionView, ...]
    days: tuple[DayView, ...]
    readiness: tuple[ReadinessView, ...]
    budget: BudgetView
    risks: tuple[Finding, ...]
    sources: tuple[SourceView, ...]
    generated_at: datetime


def _text(value: Any, default: str = "Unknown") -> str:
    if value is None:
        return default
    rendered = str(value).strip()
    return rendered or default


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _mapping_items(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, list):
        return ()
    return (item for item in value if isinstance(item, Mapping))


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
        return amount if amount.is_finite() and amount >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def _weekday(value: str) -> str:
    try:
        return date.fromisoformat(value).strftime("%A")
    except ValueError:
        return "Unknown"


def _route(state: TripState) -> tuple[RouteStopView, ...]:
    views = []
    for position, item in enumerate(_mapping_items(state.itinerary.get("route_stops")), start=1):
        nights = item.get("nights")
        views.append(
            RouteStopView(
                stop_id=_text(item.get("id"), f"stop-{position}"),
                name=_text(item.get("name")),
                dates=_text(item.get("dates")),
                nights=nights if isinstance(nights, int) and not isinstance(nights, bool) else None,
                transfer_label=(
                    _text(item.get("transfer_label"))
                    if item.get("transfer_label") is not None
                    else None
                ),
            )
        )
    return tuple(views)


def _decisions(state: TripState) -> tuple[DecisionView, ...]:
    severity_order = {"blocking": 0, "warning": 1, "note": 2}
    views = [
        DecisionView(
            decision_id=_text(item.get("id"), "unknown-decision"),
            severity=_text(item.get("severity"), "warning"),
            question=_text(item.get("question")),
            why=_text(item.get("why")),
            affected_ids=_strings(item.get("affected_ids")),
            deadline=_text(item.get("deadline")),
            next_action=_text(item.get("next_action")),
        )
        for item in _mapping_items(state.itinerary.get("open_decisions"))
    ]
    return tuple(
        sorted(
            views,
            key=lambda item: (
                severity_order.get(item.severity, 3),
                item.deadline,
                item.decision_id,
            ),
        )
    )


def _scenario(item: Mapping[str, Any]) -> ScenarioView | None:
    kind = item.get("kind")
    if kind not in {"primary", "backup"}:
        return None
    return ScenarioView(kind, _text(item.get("title")), _text(item.get("description")))


def _days(state: TripState) -> tuple[DayView, ...]:
    views = []
    for position, item in enumerate(_mapping_items(state.itinerary.get("days")), start=1):
        date_value = _text(item.get("date"))
        scenarios = tuple(
            scenario
            for scenario in (_scenario(value) for value in _mapping_items(item.get("scenarios")))
            if scenario is not None
        )
        views.append(
            DayView(
                day_id=_text(item.get("id"), f"day-{position}"),
                number=item.get("number") if isinstance(item.get("number"), int) else position,
                date=date_value,
                weekday=_weekday(date_value),
                region=_text(item.get("region")),
                overnight=_text(item.get("overnight")),
                thesis=_text(item.get("thesis")),
                load=_text(item.get("load")),
                travel=_text(item.get("travel")),
                weather_sensitive=bool(item.get("weather_sensitive", False)),
                booking_state=_text(item.get("booking_state")),
                critical_constraints=_strings(item.get("critical_constraints")),
                timeline=tuple(
                    TimelineEventView(
                        _text(event.get("time")),
                        _text(event.get("title")),
                        _text(event.get("detail")),
                    )
                    for event in _mapping_items(item.get("timeline"))
                ),
                scenarios=scenarios,
                food=tuple(
                    FoodView(
                        _text(food.get("name")),
                        _text(food.get("status")),
                        _text(food.get("note")),
                    )
                    for food in _mapping_items(item.get("food"))
                ),
                readiness_ids=_strings(item.get("readiness_ids")),
                links=tuple(
                    LinkView(
                        _text(link.get("label")),
                        _text(link.get("url")),
                        _text(link.get("kind"), "external"),
                        bool(link.get("requires_internet", True)),
                    )
                    for link in _mapping_items(item.get("links"))
                ),
                source_ids=_strings(item.get("source_ids")),
                last_checked=_text(item.get("last_checked")),
            )
        )
    return tuple(sorted(views, key=lambda item: (item.number, item.day_id)))


def _readiness(state: TripState) -> tuple[ReadinessView, ...]:
    status_order = {
        "action_needed": 0,
        "recheck": 1,
        "not_released_yet": 2,
        "unknown": 3,
        "selected": 4,
        "booked": 5,
        "confirmed": 6,
        "waived": 7,
        "not_applicable": 8,
    }
    views = [
        ReadinessView(
            item_id=_text(item.get("id"), "unknown-readiness"),
            title=_text(item.get("title"), _text(item.get("id"), "Unknown readiness item")),
            category=_text(item.get("category")),
            status=_text(item.get("status")),
            owner_id=_text(item.get("owner_id")),
            due_at=_text(item.get("due_at"), ""),
            next_check_at=_text(item.get("next_check_at"), ""),
            next_action=_text(item.get("next_action"), ""),
            issue=_text(item.get("issue"), ""),
            source_ids=_strings(item.get("source_ids")),
            claim_ids=_strings(item.get("claim_ids")),
        )
        for item in _mapping_items(state.readiness.get("items"))
    ]
    return tuple(sorted(views, key=lambda item: (status_order.get(item.status, 9), item.item_id)))


def _budget(state: TripState) -> BudgetView:
    items = tuple(_mapping_items(state.itinerary.get("budget_items")))
    calculated = calculate_budget(items)
    exclusions = {item.index: item.reason for item in calculated.excluded}
    categories = []
    for index, item in enumerate(items):
        amount_type = _text(item.get("amount_type"), "unknown")
        if amount_type == "range":
            minimum, maximum = _decimal(item.get("amount_min")), _decimal(item.get("amount_max"))
        elif amount_type in {"exact", "estimate"}:
            minimum = maximum = _decimal(item.get("amount"))
        else:
            minimum = maximum = None
        categories.append(
            BudgetCategoryView(
                category=_text(item.get("category"), _text(item.get("id"))),
                minimum=minimum,
                maximum=maximum,
                currency=_text(item.get("currency")),
                amount_type=amount_type,
                basis=_text(item.get("basis")),
                exclusion_reason=exclusions.get(index),
            )
        )
    return BudgetView(
        calculated.subtotals,
        len(calculated.excluded),
        tuple(sorted(categories, key=lambda item: item.category)),
    )


def _all_claims(state: TripState) -> tuple[Mapping[str, Any], ...]:
    claims = list(_mapping_items(state.candidates.get("claims")))
    for candidate in _mapping_items(state.candidates.get("items")):
        claims.extend(_mapping_items(candidate.get("claims")))
    return tuple(claims)


def _highest(values: Iterable[str], order: Mapping[str, int], default: str) -> str:
    available = tuple(values)
    return min(available, key=lambda value: order.get(value, 99)) if available else default


def _sources(state: TripState) -> tuple[SourceView, ...]:
    claims = _all_claims(state)
    claim_order = {
        "conflicting": 0,
        "not_released_yet": 1,
        "unverified": 2,
        "reported": 3,
        "verified": 4,
    }
    freshness_order = {"stale": 0, "unknown": 1, "aging": 2, "fresh": 3}
    views = []
    for source in _mapping_items(state.candidates.get("sources")):
        source_id = _text(source.get("id"), "unknown-source")
        linked = [claim for claim in claims if source_id in _strings(claim.get("source_ids"))]
        views.append(
            SourceView(
                source_id=source_id,
                title=_text(source.get("publisher")),
                url=_text(source.get("url")),
                source_type=_text(source.get("source_type")),
                last_checked=_text(source.get("retrieved_at")),
                retrieval_status=_text(source.get("retrieval_status")),
                claim_status=_highest(
                    (_text(claim.get("status"), "unverified") for claim in linked),
                    claim_order,
                    "unverified",
                ),
                freshness_status=_highest(
                    (_text(claim.get("freshness_status")) for claim in linked),
                    freshness_order,
                    "unknown",
                ),
            )
        )
    return tuple(sorted(views, key=lambda item: item.source_id))


def _verification_label(level: str) -> str:
    return {
        "none": "Данные не проверены",
        "ai_reviewed": "AI-review — вероятностный разбор",
        "codex_validated": "Целостность данных проверена в Codex",
    }.get(level, "Неизвестный уровень проверки")


def _declared_final_label(status: str, basis: Any) -> str | None:
    if status != "final":
        return None
    return {
        "codex_validated": "Prepared copy — данные проверены в Codex",
        "user_confirmed": "Prepared copy — по запросу пользователя",
    }.get(basis)


def _status_label(
    status: str,
    verification: str,
    declared_final_label: str | None,
    lifecycle_safe: bool,
) -> str:
    if status == "final":
        return (
            declared_final_label
            if lifecycle_safe and declared_final_label
            else ("Prepared copy — несогласованное состояние")
        )
    if verification == "ai_reviewed":
        return "Draft — AI-review"
    if verification == "codex_validated":
        return "Draft — данные проверены в Codex"
    return "Draft — без проверки"


def _acceptance_records(state: TripState) -> dict[str, Mapping[str, Any]]:
    records: dict[str, Mapping[str, Any]] = {}
    for item in _mapping_items(state.itinerary.get("accepted_blockers")):
        blocker_id = item.get("blocker_id")
        if isinstance(blocker_id, str) and blocker_id not in records:
            records[blocker_id] = item
    return records


def _blocker_view(
    finding: Finding,
    acceptance: Mapping[str, Any] | None,
    *,
    accepted: bool,
) -> BlockerView:
    return BlockerView(
        id=finding.id,
        code=finding.code,
        severity="blocking",
        path=finding.path,
        affected_ids=finding.affected_ids,
        message=finding.message,
        resolution_status="unresolved",
        acceptance_label="Принят пользователем — остаётся блокирующим" if accepted else None,
        accepted_at=(
            _text(acceptance.get("accepted_at") if acceptance else None) if accepted else None
        ),
        rationale=(
            _text(acceptance.get("rationale") if acceptance else None) if accepted else None
        ),
    )


def build_view(
    state: TripState,
    check_report: CheckReport,
    generated_at: datetime,
) -> ItineraryView:
    """Project canonical state into an immutable, deterministic document view."""
    route = _route(state)
    readiness = _readiness(state)
    budget = _budget(state)
    document_status = state.itinerary.get("document_status")
    verification_level = state.itinerary.get("verification_level")
    finalization_basis = state.itinerary.get("finalization_basis")
    acceptance_records = _acceptance_records(state)
    lifecycle_safe = (
        check_report.ok
        if document_status == "final"
        else not check_report.structural_errors and check_report.lifecycle_consistent
    )
    declared_final_label = _declared_final_label(document_status, finalization_basis)
    accepted_blockers = tuple(
        _blocker_view(finding, acceptance_records.get(finding.id), accepted=True)
        for finding in check_report.accepted_blocking_findings
    )
    unaccepted_blockers = tuple(
        _blocker_view(finding, None, accepted=False)
        for finding in check_report.unaccepted_blocking_findings
    )
    dates = state.brief.get("travel_dates", {})
    summary = SummaryView(
        date_range=f"{_text(dates.get('start'))} — {_text(dates.get('end'))}",
        traveler_count=len(state.brief.get("travelers", [])),
        thesis=_text(state.brief.get("trip_thesis")),
        route_text=" → ".join(stop.name for stop in route) or "Route not selected",
        readiness_confirmed=sum(item.status == "confirmed" for item in readiness),
        readiness_total=len(readiness),
    )
    return ItineraryView(
        trip_id=_text(state.brief.get("trip_id")),
        title=_text(state.brief.get("title")),
        document_status=document_status,
        verification_level=verification_level,
        finalization_basis=finalization_basis,
        status_label=_status_label(
            document_status,
            verification_level,
            declared_final_label,
            lifecycle_safe,
        ),
        verification_label=_verification_label(verification_level),
        declared_final_label=declared_final_label,
        lifecycle_safe=lifecycle_safe,
        lifecycle_warning=(
            None
            if lifecycle_safe
            else (
                "Статус и отчёт проверки противоречат друг другу; "
                "этот документ нельзя считать согласованной подготовленной копией."
            )
        ),
        accepted_blockers=accepted_blockers,
        unaccepted_blockers=unaccepted_blockers,
        summary=summary,
        route=route,
        open_decisions=_decisions(state),
        days=_days(state),
        readiness=readiness,
        budget=budget,
        risks=check_report.all_findings,
        sources=_sources(state),
        generated_at=generated_at,
    )

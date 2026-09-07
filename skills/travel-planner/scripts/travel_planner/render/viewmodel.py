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
class LinkView:
    label: str
    url: str
    kind: str
    requires_internet: bool


@dataclass(frozen=True)
class CheckpointView:
    check: str
    adjust_plan: str


@dataclass(frozen=True)
class EventAlternativeView:
    alternative_id: str
    title: str
    reason: str
    detail: str
    price: str
    effort: str
    distance: str
    booking: str
    links: tuple[LinkView, ...]


@dataclass(frozen=True)
class TimelineEventView:
    event_id: str
    kind: str
    time: str
    title: str
    detail: str
    links: tuple[LinkView, ...]
    alternatives: tuple[EventAlternativeView, ...]
    checkpoint: CheckpointView | None


@dataclass(frozen=True)
class ScenarioView:
    scenario_id: str
    label: str
    summary: str
    timeline: tuple[TimelineEventView, ...]


@dataclass(frozen=True)
class DayView:
    day_id: str
    number: int
    date: str
    date_label: str
    weekday: str
    region: str
    overnight: str
    thesis: str
    load: str
    travel: str
    weather_sensitive: bool
    booking_state: str
    timeline: tuple[TimelineEventView, ...]
    scenarios: tuple[ScenarioView, ...]
    readiness_ids: tuple[str, ...]
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
    provenance: str


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
    language: Literal["en", "ru"]
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


def _unknown(language: str) -> str:
    return "Неизвестно" if language == "ru" else "Unknown"


def _budget_exclusion(reason: str | None, language: str) -> str | None:
    if reason is None or language != "ru":
        return reason
    if reason == "Amount is unknown":
        return "Сумма неизвестна"
    if reason.startswith("Missing "):
        fields = {
            "amount": "сумма",
            "amount_min": "нижняя граница",
            "amount_max": "верхняя граница",
            "currency": "валюта",
            "basis": "основание цены",
        }
        missing = ", ".join(
            fields.get(field, field) for field in reason.removeprefix("Missing ").split(", ")
        )
        return f"Не указано: {missing}"
    return reason


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


_WEEKDAYS = {
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    "ru": (
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ),
}

_MONTHS = {
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "ru": (
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ),
}


def _language(state: TripState) -> Literal["en", "ru"]:
    return "ru" if state.brief.get("document_language") == "ru" else "en"


def _weekday(value: str, language: str) -> str:
    try:
        parsed = date.fromisoformat(value)
        return _WEEKDAYS[language][parsed.weekday()]
    except ValueError:
        return "Неизвестно" if language == "ru" else "Unknown"


def _date_label(value: str, language: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return "Неизвестно" if language == "ru" else "Unknown"
    month = _MONTHS[language][parsed.month - 1]
    if language == "ru":
        return f"{parsed.day} {month} {parsed.year}"
    return f"{month} {parsed.day}, {parsed.year}"


def _route(state: TripState, language: str) -> tuple[RouteStopView, ...]:
    views = []
    for position, item in enumerate(_mapping_items(state.itinerary.get("route_stops")), start=1):
        nights = item.get("nights")
        views.append(
            RouteStopView(
                stop_id=_text(item.get("id"), f"stop-{position}"),
                name=_text(item.get("name"), _unknown(language)),
                dates=_text(item.get("dates"), _unknown(language)),
                nights=nights if isinstance(nights, int) and not isinstance(nights, bool) else None,
                transfer_label=(
                    _text(item.get("transfer_label"))
                    if item.get("transfer_label") is not None
                    else None
                ),
            )
        )
    return tuple(views)


def _decisions(state: TripState, language: str) -> tuple[DecisionView, ...]:
    severity_order = {"blocking": 0, "warning": 1, "note": 2}
    views = [
        DecisionView(
            decision_id=_text(item.get("id"), "unknown-decision"),
            severity=_text(item.get("severity"), "warning"),
            question=_text(item.get("question"), _unknown(language)),
            why=_text(item.get("why"), _unknown(language)),
            affected_ids=_strings(item.get("affected_ids")),
            deadline=_text(item.get("deadline"), _unknown(language)),
            next_action=_text(item.get("next_action"), _unknown(language)),
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


def _link(item: Mapping[str, Any]) -> LinkView:
    return LinkView(
        _text(item.get("label")),
        _text(item.get("url")),
        _text(item.get("kind"), "source"),
        bool(item.get("requires_internet", True)),
    )


def _event_alternative(item: Mapping[str, Any]) -> EventAlternativeView:
    return EventAlternativeView(
        alternative_id=_text(item.get("id"), "unknown-alternative"),
        title=_text(item.get("title")),
        reason=_text(item.get("reason")),
        detail=_text(item.get("detail"), ""),
        price=_text(item.get("price"), ""),
        effort=_text(item.get("effort"), ""),
        distance=_text(item.get("distance"), ""),
        booking=_text(item.get("booking"), ""),
        links=tuple(_link(link) for link in _mapping_items(item.get("links"))),
    )


def _timeline(value: Any, language: str) -> tuple[TimelineEventView, ...]:
    views = []
    for position, event in enumerate(_mapping_items(value), start=1):
        checkpoint_value = event.get("checkpoint")
        checkpoint = (
            CheckpointView(
                _text(checkpoint_value.get("check")),
                _text(checkpoint_value.get("adjust_plan")),
            )
            if isinstance(checkpoint_value, Mapping)
            else None
        )
        views.append(
            TimelineEventView(
                event_id=_text(event.get("id"), f"unknown-event-{position}"),
                kind=_text(event.get("kind"), "activity"),
                time=_text(event.get("time"), _unknown(language)),
                title=_text(event.get("title"), _unknown(language)),
                detail=_text(event.get("detail"), ""),
                links=tuple(_link(link) for link in _mapping_items(event.get("links"))),
                alternatives=tuple(
                    _event_alternative(alternative)
                    for alternative in _mapping_items(event.get("alternatives"))
                ),
                checkpoint=checkpoint,
            )
        )
    return tuple(views)


def _scenario(item: Mapping[str, Any], language: str) -> ScenarioView:
    return ScenarioView(
        scenario_id=_text(item.get("id"), "unknown-scenario"),
        label=_text(item.get("label")),
        summary=_text(item.get("summary"), ""),
        timeline=_timeline(item.get("timeline"), language),
    )


def _days(state: TripState, language: str) -> tuple[DayView, ...]:
    views = []
    for position, item in enumerate(_mapping_items(state.itinerary.get("days")), start=1):
        date_value = _text(item.get("date"))
        scenarios = tuple(
            _scenario(value, language) for value in _mapping_items(item.get("scenarios"))
        )
        views.append(
            DayView(
                day_id=_text(item.get("id"), f"day-{position}"),
                number=item.get("number") if isinstance(item.get("number"), int) else position,
                date=date_value,
                date_label=_date_label(date_value, language),
                weekday=_weekday(date_value, language),
                region=_text(item.get("region"), _unknown(language)),
                overnight=_text(item.get("overnight"), _unknown(language)),
                thesis=_text(item.get("thesis"), _unknown(language)),
                load=_text(item.get("load"), _unknown(language)),
                travel=_text(item.get("travel"), _unknown(language)),
                weather_sensitive=bool(item.get("weather_sensitive", False)),
                booking_state=_text(item.get("booking_state"), _unknown(language)),
                timeline=_timeline(item.get("timeline"), language),
                scenarios=scenarios,
                readiness_ids=_strings(item.get("readiness_ids")),
                source_ids=_strings(item.get("source_ids")),
                last_checked=_text(item.get("last_checked"), _unknown(language)),
            )
        )
    return tuple(sorted(views, key=lambda item: (item.number, item.day_id)))


def _readiness(state: TripState, language: str) -> tuple[ReadinessView, ...]:
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
            title=_text(
                item.get("title"),
                _text(
                    item.get("id"),
                    "Неизвестная задача" if language == "ru" else "Unknown readiness item",
                ),
            ),
            category=_text(item.get("category"), "unknown"),
            status=_text(item.get("status"), "unknown"),
            owner_id=_text(item.get("owner_id"), _unknown(language)),
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


def _budget(state: TripState, language: str) -> BudgetView:
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
                currency=_text(item.get("currency"), _unknown(language)),
                amount_type=amount_type,
                basis=_text(item.get("basis"), "unknown"),
                exclusion_reason=_budget_exclusion(exclusions.get(index), language),
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


def _sources(state: TripState, language: str) -> tuple[SourceView, ...]:
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
                title=_text(source.get("publisher"), _unknown(language)),
                url=_text(source.get("url"), _unknown(language)),
                source_type=_text(source.get("source_type"), "unknown"),
                last_checked=_text(source.get("retrieved_at"), _unknown(language)),
                retrieval_status=_text(source.get("retrieval_status"), "unknown"),
                provenance=_text(source.get("provenance"), ""),
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


def _verification_label(level: str, language: str) -> str:
    labels = {
        "en": {
            "none": "Recorded data not checked",
            "ai_reviewed": "AI-review — probabilistic review",
            "codex_validated": "Recorded data integrity checked in Codex",
            "unknown": "Unknown verification level",
        },
        "ru": {
            "none": "Данные не проверены",
            "ai_reviewed": "AI-проверка — вероятностный разбор",
            "codex_validated": "Целостность данных проверена в Codex",
            "unknown": "Неизвестный уровень проверки",
        },
    }[language]
    return labels.get(level, labels["unknown"])


def _declared_final_label(status: str, basis: Any, language: str) -> str | None:
    if status != "final":
        return None
    labels = {
        "en": {
            "codex_validated": "Prepared copy — checked in Codex",
            "user_confirmed": "Prepared copy — requested by user",
        },
        "ru": {
            "codex_validated": "Подготовленная копия — данные проверены в Codex",
            "user_confirmed": "Подготовленная копия — по запросу пользователя",
        },
    }[language]
    return labels.get(basis)


def _status_label(
    status: str,
    verification: str,
    declared_final_label: str | None,
    lifecycle_safe: bool,
    language: str,
) -> str:
    if status == "final":
        return (
            declared_final_label
            if lifecycle_safe and declared_final_label
            else (
                "Подготовленная копия — несогласованное состояние"
                if language == "ru"
                else "Prepared copy — inconsistent state"
            )
        )
    if verification == "ai_reviewed":
        return "Черновик — AI-проверка" if language == "ru" else "Draft — AI-review"
    if verification == "codex_validated":
        return (
            "Черновик — данные проверены в Codex"
            if language == "ru"
            else "Draft — checked in Codex"
        )
    return "Черновик — без проверки" if language == "ru" else "Draft — unchecked"


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
    language: str,
) -> BlockerView:
    return BlockerView(
        id=finding.id,
        code=finding.code,
        severity="blocking",
        path=finding.path,
        affected_ids=finding.affected_ids,
        message=finding.message,
        resolution_status="unresolved",
        acceptance_label=(
            (
                "Принят пользователем — остаётся блокирующим"
                if language == "ru"
                else "Accepted by user — remains blocking"
            )
            if accepted
            else None
        ),
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
    language = _language(state)
    route = _route(state, language)
    readiness = _readiness(state, language)
    budget = _budget(state, language)
    document_status = state.itinerary.get("document_status")
    verification_level = state.itinerary.get("verification_level")
    finalization_basis = state.itinerary.get("finalization_basis")
    acceptance_records = _acceptance_records(state)
    lifecycle_safe = (
        check_report.ok
        if document_status == "final"
        else not check_report.structural_errors and check_report.lifecycle_consistent
    )
    declared_final_label = _declared_final_label(
        document_status, finalization_basis, language
    )
    accepted_blockers = tuple(
        _blocker_view(
            finding,
            acceptance_records.get(finding.id),
            accepted=True,
            language=language,
        )
        for finding in check_report.accepted_blocking_findings
    )
    unaccepted_blockers = tuple(
        _blocker_view(finding, None, accepted=False, language=language)
        for finding in check_report.unaccepted_blocking_findings
    )
    dates = state.brief.get("travel_dates", {})
    unknown = _unknown(language)
    summary = SummaryView(
        date_range=(
            f"{_text(dates.get('start'), unknown)} — {_text(dates.get('end'), unknown)}"
        ),
        traveler_count=len(state.brief.get("travelers", [])),
        thesis=_text(state.brief.get("trip_thesis"), _unknown(language)),
        route_text=" → ".join(stop.name for stop in route)
        or ("Маршрут не выбран" if language == "ru" else "Route not selected"),
        readiness_confirmed=sum(item.status == "confirmed" for item in readiness),
        readiness_total=len(readiness),
    )
    return ItineraryView(
        language=language,
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
            language,
        ),
        verification_label=_verification_label(verification_level, language),
        declared_final_label=declared_final_label,
        lifecycle_safe=lifecycle_safe,
        lifecycle_warning=(
            None
            if lifecycle_safe
            else (
                (
                    "Статус и отчёт проверки противоречат друг другу; "
                    "этот документ нельзя считать согласованной подготовленной копией."
                )
                if language == "ru"
                else (
                    "The status and check report conflict; this document cannot be treated "
                    "as a consistent prepared copy."
                )
            )
        ),
        accepted_blockers=accepted_blockers,
        unaccepted_blockers=unaccepted_blockers,
        summary=summary,
        route=route,
        open_decisions=_decisions(state, language),
        days=_days(state, language),
        readiness=readiness,
        budget=budget,
        risks=check_report.all_findings,
        sources=_sources(state, language),
        generated_at=generated_at,
    )

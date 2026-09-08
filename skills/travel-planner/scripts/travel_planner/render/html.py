"""Self-contained Curated Route HTML rendering."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import groupby
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from ..budget import format_money
from ..resources import resource_path
from .media import MediaAsset, embed_media
from .viewmodel import ItineraryView, LinkView, TimelineEventView

_COPY = {
    "en": {
        "itinerary": "itinerary",
        "skip": "Skip to itinerary",
        "travellers": "travellers",
        "verification": "Verification level",
        "inconsistent": "Inconsistent state",
        "declared_basis": "Declared basis",
        "feasibility_note": "Document preparation and recorded-data checks do not confirm that the trip is feasible. Open decisions and recorded concerns remain below.",
        "review_days": "Review all days",
        "open_decisions_count": "open decisions",
        "readiness": "Readiness",
        "confirmed_of": "{confirmed} of {total} confirmed",
        "review_preparation": "Review preparation",
        "recorded_expenses": "Recorded expenses",
        "rows": "recorded rows",
        "no_sum": "No summable amounts recorded",
        "excluded_review": "{count} excluded rows · Review recorded expenses",
        "blocking": "Blocking",
        "unresolved": "Unresolved",
        "contents": "Contents",
        "trip_summary": "Trip summary",
        "blockers": "Blockers",
        "route_days": "Route and days",
        "open_decisions": "Open decisions",
        "detailed_days": "Detailed days",
        "preparation": "Preparation",
        "budget": "Budget",
        "risks": "Risks and backups",
        "day": "Day",
        "enhancement_error": "Interactive controls are unavailable. The complete itinerary remains below.",
        "blocker_intro": "Recorded blockers remain unresolved and blocking for their decisions. Preparing this document does not resolve or accept them.",
        "blocker_empty": "No blockers are recorded in the canonical trip state. This does not confirm trip feasibility.",
        "unaccepted_blockers": "Unaccepted blockers",
        "accepted_blockers": "Accepted blockers",
        "none_unaccepted": "No unaccepted blockers.",
        "none_accepted": "No accepted blockers.",
        "accepted_at": "Accepted at",
        "rationale": "Rationale",
        "affects": "Affects",
        "path": "Path",
        "route_overview": "Route and day overview",
        "nights": "nights",
        "route_empty": "Route not selected.",
        "filter_days": "Filter days",
        "all_days": "All days",
        "unresolved_filter": "Unresolved",
        "weather_filter": "Weather-sensitive",
        "transfer_filter": "Transfers",
        "warning_filter": "Checkpoints",
        "days_shown": "{count} days shown.",
        "no_matches": "No matching days.",
        "reset": "Reset filters",
        "load": "load",
        "no_days": "No detailed days recorded.",
        "deadline": "Deadline",
        "next_action": "Next action",
        "no_decisions": "No open decisions.",
        "overnight": "Overnight",
        "travel": "Travel",
        "weather_sensitive": "Weather-sensitive",
        "scenario_view": "Scenario view for day {number}",
        "primary": "Primary",
        "primary_scenario": "Primary scenario",
        "alternative_scenario": "Alternative scenario",
        "timeline": "Timeline",
        "day_plan": "How we’ll spend the day",
        "choose_scenario": "Choose one complete route for the day.",
        "morning": "Morning",
        "afternoon": "Afternoon",
        "evening": "Evening",
        "time": "Time",
        "event_type": "{kind}",
        "what_check": "What to check",
        "how_adjust": "How to change the plan",
        "internet": "Internet required",
        "alternatives": "Alternatives ({count})",
        "reason": "Why choose it",
        "price": "Price",
        "effort": "Effort",
        "distance": "Distance",
        "booking": "Booking",
        "media_unavailable": "Photo unavailable; the day plan remains complete.",
        "day_gallery": "Main locations · Day {number}",
        "previous_day": "Previous day",
        "next_day": "Next day",
        "bookings_readiness": "Bookings and readiness",
        "readiness_note": "{confirmed} confirmed of {total}. Blockers are shown separately and are not averaged into this count.",
        "owner": "Owner",
        "due": "Due",
        "next_check": "Next check",
        "check_result": "Review result",
        "checked_at": "Reviewed on",
        "not_checked": "Not checked",
        "recheck_required": "Recheck required",
        "no_readiness": "No readiness items recorded.",
        "expenses_note": "Subtotals keep currencies and price bases separate. No conversion or multiplication by traveller count is applied. Recorded expenses are not a complete trip budget.",
        "excluded_rows": "{count} rows are excluded from subtotals; their recorded values and reasons remain below.",
        "category": "Category",
        "recorded_amount": "Recorded amount",
        "type": "Type",
        "basis": "Basis",
        "subtotal": "Subtotal inclusion",
        "included": "Included",
        "no_budget": "No budget items recorded.",
        "no_risks": "No recorded concerns. Unknowns may still remain.",
        "generated": "Generated",
        "artefact": "Artefact v0.1",
        "scenario_shown": "{label} scenario shown.",
    },
    "ru": {
        "itinerary": "маршрут",
        "skip": "Перейти к маршруту",
        "travellers": "путешественников",
        "verification": "Уровень проверки",
        "inconsistent": "Несогласованное состояние",
        "declared_basis": "Заявленное основание",
        "feasibility_note": "Подготовка документа и проверка записанных данных не подтверждают выполнимость поездки. Открытые решения и замечания сохранены ниже.",
        "review_days": "Посмотреть все дни",
        "open_decisions_count": "открытых решений",
        "readiness": "Готовность",
        "confirmed_of": "Подтверждено: {confirmed} из {total}",
        "review_preparation": "Проверить подготовку",
        "recorded_expenses": "Записанные расходы",
        "rows": "строк расходов",
        "no_sum": "Нет суммируемых расходов",
        "excluded_review": "Исключено строк: {count} · Проверить расходы",
        "blocking": "Блокирует",
        "unresolved": "Не решено",
        "contents": "Содержание",
        "trip_summary": "О поездке",
        "blockers": "Блокеры",
        "route_days": "Маршрут и дни",
        "open_decisions": "Открытые решения",
        "detailed_days": "Дни подробно",
        "preparation": "Подготовка",
        "budget": "Расходы",
        "risks": "Риски и запасные планы",
        "day": "День",
        "enhancement_error": "Интерактивные элементы недоступны. Полный маршрут остаётся ниже.",
        "blocker_intro": "Записанные блокеры остаются нерешёнными и блокирующими для своих решений. Подготовка документа не устраняет и не принимает их.",
        "blocker_empty": "В каноническом состоянии нет записанных блокеров. Это не подтверждает выполнимость поездки.",
        "unaccepted_blockers": "Непринятые блокеры",
        "accepted_blockers": "Принятые блокеры",
        "none_unaccepted": "Нет непринятых блокеров.",
        "none_accepted": "Нет принятых блокеров.",
        "accepted_at": "Принят",
        "rationale": "Основание",
        "affects": "Затрагивает",
        "path": "Путь",
        "route_overview": "Обзор маршрута и дней",
        "nights": "ночей",
        "route_empty": "Маршрут не выбран.",
        "filter_days": "Фильтр дней",
        "all_days": "Все дни",
        "unresolved_filter": "Не решено",
        "weather_filter": "Зависит от погоды",
        "transfer_filter": "Переезды",
        "warning_filter": "Контрольные точки",
        "days_shown": "Показано дней: {count}.",
        "no_matches": "Подходящих дней нет.",
        "reset": "Сбросить фильтры",
        "load": "нагрузка",
        "no_days": "Подробные дни не записаны.",
        "deadline": "Срок",
        "next_action": "Следующее действие",
        "no_decisions": "Открытых решений нет.",
        "overnight": "Ночёвка",
        "travel": "Переезды",
        "weather_sensitive": "Зависит от погоды",
        "scenario_view": "Сценарий дня {number}",
        "primary": "Основной",
        "primary_scenario": "Основной сценарий",
        "alternative_scenario": "Альтернативный сценарий",
        "timeline": "Расписание",
        "day_plan": "Как проведём день",
        "choose_scenario": "Выбираем один полный маршрут на день.",
        "morning": "Утро",
        "afternoon": "День",
        "evening": "Вечер",
        "time": "Время",
        "event_type": "{kind}",
        "what_check": "Что проверить",
        "how_adjust": "Как изменить план",
        "internet": "Требуется интернет",
        "alternatives": "Альтернативы ({count})",
        "reason": "Когда выбрать",
        "price": "Цена",
        "effort": "Нагрузка",
        "distance": "Расстояние",
        "booking": "Бронирование",
        "media_unavailable": "Фото недоступно; план дня остаётся полным.",
        "day_gallery": "Основные места · День {number}",
        "previous_day": "Предыдущий день",
        "next_day": "Следующий день",
        "bookings_readiness": "Бронирования и готовность",
        "readiness_note": "Подтверждено: {confirmed} из {total}. Блокеры показаны отдельно и не усредняются в этом числе.",
        "owner": "Ответственный",
        "due": "Срок",
        "next_check": "Следующая проверка",
        "check_result": "Результат проверки",
        "checked_at": "Дата проверки",
        "not_checked": "Не проверено",
        "recheck_required": "Обязательно перепроверить",
        "no_readiness": "Элементы готовности не записаны.",
        "expenses_note": "Промежуточные суммы разделяют валюты и основания цены. Конвертация и умножение на число путешественников не выполняются. Записанные расходы не являются полным бюджетом поездки.",
        "excluded_rows": "Из промежуточных сумм исключено строк: {count}; записанные значения и причины сохранены ниже.",
        "category": "Категория",
        "recorded_amount": "Записанная сумма",
        "type": "Тип",
        "basis": "Основание",
        "subtotal": "Учёт в сумме",
        "included": "Учтено",
        "no_budget": "Расходы не записаны.",
        "no_risks": "Записанных замечаний нет. Неизвестные сведения могут сохраняться.",
        "generated": "Создан",
        "artefact": "Артефакт v0.1",
        "scenario_shown": "Показан сценарий «{label}».",
    },
}

_ENUMS = {
    "en": {
        "activity": "Activity",
        "transport": "Transport",
        "meal": "Meal",
        "lodging": "Lodging",
        "rest": "Rest",
        "checkpoint": "Checkpoint",
        "light": "light",
        "low": "low",
        "medium": "medium",
        "moderate": "moderate",
        "selected": "selected",
        "booked": "booked",
        "confirmed": "confirmed",
        "recheck": "recheck",
        "unknown": "unknown",
        "not_released_yet": "not released yet",
        "action_needed": "action needed",
        "waived": "waived",
        "not_applicable": "not applicable",
        "entry": "Entry",
        "transit": "Transit",
        "health": "Health",
        "medication": "Medication",
        "insurance": "Insurance",
        "activities": "Activities",
        "dining": "Dining",
        "connectivity": "Connectivity",
        "money": "Money",
        "documents": "Documents",
        "packing": "Packing",
        "emergency": "Emergency",
        "pre_departure": "Pre-departure",
        "official": "Official",
        "primary": "Primary",
        "editorial": "Editorial",
        "aggregator": "Aggregator",
        "social": "Social",
        "community": "Community",
        "ok": "available",
        "unavailable": "unavailable",
        "blocked": "blocked",
        "not_found": "not found",
        "unverified": "unverified",
        "reported": "reported",
        "verified": "verified",
        "conflicting": "conflicting",
        "fresh": "fresh",
        "aging": "aging",
        "stale": "stale",
        "blocking": "blocking",
        "warning": "warning",
        "note": "note",
        "per_group": "per group",
        "per_person": "per person",
        "exact": "exact",
        "estimate": "estimate",
        "range": "range",
    },
    "ru": {
        "activity": "Активность",
        "transport": "Переезд",
        "meal": "Еда",
        "lodging": "Заселение",
        "rest": "Отдых",
        "checkpoint": "Контрольная точка",
        "light": "лёгкая",
        "low": "низкая",
        "medium": "средняя",
        "moderate": "средняя",
        "selected": "выбрано",
        "confirmed": "подтверждено",
        "recheck": "перепроверить",
        "not_released_yet": "ещё не опубликовано",
        "action_needed": "требуется действие",
        "booked": "забронировано",
        "waived": "отменено пользователем",
        "not_applicable": "не применимо",
        "entry": "Въезд",
        "transit": "Транзит",
        "health": "Здоровье",
        "medication": "Лекарства",
        "insurance": "Страхование",
        "activities": "Мероприятия",
        "dining": "Питание",
        "connectivity": "Связь",
        "money": "Деньги",
        "documents": "Документы",
        "packing": "Багаж",
        "emergency": "Экстренные действия",
        "pre_departure": "Перед поездкой",
        "official": "Официальный",
        "primary": "Первичный",
        "editorial": "Редакционный",
        "aggregator": "Агрегатор",
        "social": "Социальная сеть",
        "community": "Сообщество",
        "ok": "доступен",
        "unavailable": "недоступен",
        "blocked": "заблокирован",
        "not_found": "не найден",
        "unverified": "не проверено",
        "reported": "по сообщению источника",
        "verified": "проверено",
        "conflicting": "противоречивые сведения",
        "fresh": "актуально",
        "aging": "требует скорой перепроверки",
        "stale": "устарело",
        "unknown": "неизвестно",
        "blocking": "блокирует",
        "warning": "предупреждение",
        "note": "примечание",
        "per_group": "на группу",
        "per_person": "на человека",
        "exact": "точная",
        "estimate": "оценка",
        "range": "диапазон",
    },
}


@dataclass(frozen=True)
class HtmlOptions:
    include_optional_media: bool = True
    print_images: bool = True


DEFAULTS = HtmlOptions()


def _asset(name: str) -> Path:
    return resource_path("html", name)


def _translator(language: str) -> Callable[..., str]:
    catalog = _COPY[language]

    def translate(key: str, **values: object) -> str:
        return catalog[key].format(**values)

    return translate


def _enum_label(language: str) -> Callable[[str], str]:
    labels = _ENUMS[language]

    def translate(value: str) -> str:
        return labels.get(value, value.replace("_", " "))

    return translate


def _money_formatter(language: str) -> Callable[[Decimal | None, str], str]:
    def money(value: Decimal | None, currency: str) -> str:
        rendered = format_money(value, currency)
        if rendered == "Unknown" and language == "ru":
            return "Неизвестно"
        return rendered

    return money


def _timeline_links(timeline: Iterable[TimelineEventView]) -> Iterable[LinkView]:
    for event in timeline:
        yield from event.links
        for alternative in event.alternatives:
            yield from alternative.links


def _validate_external_urls(view: ItineraryView) -> None:
    links = []
    for item in view.readiness:
        links.extend(item.links)
    for day in view.days:
        links.extend(_timeline_links(day.timeline))
        for scenario in day.scenarios:
            links.extend(_timeline_links(scenario.timeline))
    labelled_urls = [
        *((source.source_id, source.url) for source in view.sources),
        *((link.label, link.url) for link in links),
    ]
    for label, url in labelled_urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"External link {label!r} must be an absolute HTTPS URL.")


def _timeline_groups(
    timeline: Sequence[TimelineEventView],
) -> list[tuple[str, tuple[TimelineEventView, ...]]]:
    """Group adjacent recorded periods, preserving unknowns and source order."""
    groups = [
        (period, tuple(events)) for period, events in groupby(timeline, key=lambda e: e.period)
    ]
    return groups or [("", ())]


def render_html(
    view: ItineraryView,
    media: Mapping[str, Sequence[MediaAsset]],
    options: HtmlOptions,
) -> str:
    """Render one deterministic document with every required asset inline."""
    _validate_external_urls(view)
    template_path = _asset("itinerary.html.j2")
    environment = Environment(
        loader=FileSystemLoader(template_path.parent),
        autoescape=select_autoescape(("html", "j2"), default=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template(template_path.name)
    optional_media = {}
    if options.include_optional_media:
        if set(media) - {day.day_id for day in view.days}:
            raise ValueError("Optional media must belong to a recorded day.")
        optional_media = embed_media(media, {s.source_id: s.url for s in view.sources})
    translate = _translator(view.language)
    rendered = template.render(
        money=_money_formatter(view.language),
        view=view,
        tr=translate,
        enum_label=_enum_label(view.language),
        timeline_groups=_timeline_groups,
        media=optional_media,
        options=options,
        css=Markup(_asset("styles.css").read_text(encoding="utf-8")),
        js=Markup(_asset("app.js").read_text(encoding="utf-8")),
        icons=Markup(_asset("icons.svg").read_text(encoding="utf-8")),
        js_copy={
            "daysShown": translate("days_shown", count="{count}"),
            "scenarioShown": translate("scenario_shown", label="{label}"),
        },
    )
    return rendered.rstrip() + "\n"


def write_html(
    view: ItineraryView,
    target: Path,
    options: HtmlOptions,
    *,
    media: Mapping[str, Sequence[MediaAsset]] | None = None,
) -> Path:
    """Write exact render bytes to one explicitly selected destination."""
    return write_rendered_html(render_html(view, media or {}, options), target)


def write_rendered_html(html: str, target: Path) -> Path:
    """Publish complete HTML without leaving a partial previous document on write failure."""
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as staged:
        staging_path = Path(staged.name)
        try:
            staged.write(html.encode("utf-8"))
            staged.flush()
            staging_path.replace(destination)
        finally:
            staging_path.unlink(missing_ok=True)
    return destination

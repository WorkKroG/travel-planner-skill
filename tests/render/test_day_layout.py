"""Reading contracts for the approved day layout, using real rendered documents."""

import re
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from travel_planner.render.html import DEFAULTS, render_html
from travel_planner.render.media import MediaAsset
from travel_planner.render.viewmodel import build_view
from travel_planner.state import validate_trip, write_state_file


def test_recorded_periods_preserve_order_and_do_not_classify_unknown_events(
    japan_state, japan_report
):
    day = japan_state.itinerary["days"][0]
    day["scenarios"] = []
    day["timeline"] = [
        {
            "id": "coffee",
            "kind": "meal",
            "time": "07:00",
            "title": "Breakfast",
            "detail": "",
            "period": "morning",
            "icon": "coffee",
        },
        {
            "id": "walk",
            "kind": "activity",
            "time": "08:00",
            "title": "Walk",
            "detail": "",
            "period": "morning",
        },
        {
            "id": "unscheduled",
            "kind": "activity",
            "time": None,
            "title": "Unscheduled",
            "detail": "",
        },
        {
            "id": "dinner",
            "kind": "meal",
            "time": "Later",
            "title": "Dinner",
            "detail": "",
            "period": "evening",
        },
        {
            "id": "late-entry",
            "kind": "activity",
            "time": "06:00",
            "title": "Recorded last",
            "detail": "",
            "period": "morning",
        },
    ]
    html = render_html(
        build_view(japan_state, japan_report, datetime(2026, 9, 8, tzinfo=UTC)), {}, DEFAULTS
    )
    chapter = html.split('id="day-1" data-day', 1)[1].split("</article>", 1)[0]
    assert re.findall(r'data-event-id="([^"]+)"', chapter) == [
        "coffee",
        "walk",
        "unscheduled",
        "dinner",
        "late-entry",
    ]
    assert re.findall(r'class="timeline-period">([^<]+)', chapter) == [
        "Morning",
        "Evening",
        "Morning",
    ]
    groups = re.findall(r'<div class="timeline-group">(.*?)</ol>\s*</div>', chapter, re.DOTALL)
    unknown_group = next(group for group in groups if 'data-event-id="unscheduled"' in group)
    assert "timeline-period" not in unknown_group
    assert "Unknown" in unknown_group
    coffee = chapter.split('data-event-id="coffee"', 1)[1].split("</li>", 1)[0]
    assert 'href="#icon-coffee"' in coffee


@pytest.mark.parametrize("language, period", [("en", "Afternoon"), ("ru", "День")])
def test_scenario_presentation_is_localized_without_replacing_content(
    japan_state, japan_report, language, period
):
    japan_state.brief["document_language"] = language
    day = japan_state.itinerary["days"][0]
    day.update(
        primary_label="Ridge trail", primary_summary="Start before 09:00.", primary_icon="mountain"
    )
    day["scenarios"][0]["icon"] = "rain"
    day["scenarios"][0]["timeline"][0]["period"] = "afternoon"
    html = render_html(
        build_view(japan_state, japan_report, datetime(2026, 9, 8, tzinfo=UTC)), {}, DEFAULTS
    )
    primary = re.search(
        r'<button[^>]+data-show-scenario="primary"[^>]*>(.*?)</button>', html, re.DOTALL
    )
    assert "Ridge trail" in primary[1]
    assert 'href="#icon-mountain"' in primary[1]
    assert "Start before 09:00." in html
    assert f'class="timeline-period">{period}</' in html
    assert 'href="#icon-rain"' in html


def test_photo_credit_travels_with_caption_without_a_source_disclosure(japan_view):
    day = japan_view.days[0]
    photo = MediaAsset(
        b"photo",
        "image/jpeg",
        "Garden",
        japan_view.sources[0].source_id,
        "CC BY 4.0",
        "Photographer",
        "Garden in autumn",
        1280,
        853,
    )
    html = render_html(replace(japan_view, days=(day,)), {day.day_id: (photo,)}, DEFAULTS)
    caption = re.search(r"<figcaption>(.*?)</figcaption>", html, re.DOTALL)[1]
    assert "Garden in autumn" in caption
    assert "Photographer" in caption and "CC BY 4.0" in caption
    assert japan_view.sources[0].url in caption
    assert 'class="day-sources"' not in html
    assert day.last_checked not in caption



@pytest.mark.parametrize("field,value", [("period", "tomorrow"), ("icon", "remote-icon")])
def test_schema_rejects_unknown_presentation_values(minimal_trip, field, value):
    from travel_planner.state import load_trip

    state = load_trip(minimal_trip)
    event = {"id": "event-one", "kind": "activity", "title": "Walk", "detail": ""}
    event[field] = value
    state.itinerary["days"] = [{"id": "day-one", "timeline": [event]}]
    write_state_file(minimal_trip / "itinerary.yaml", state.itinerary)
    assert not validate_trip(minimal_trip).ok


def test_schema_accepts_presentation_for_full_scenarios(minimal_trip):
    from travel_planner.state import load_trip

    state = load_trip(minimal_trip)
    day = {"id": "day-one", "timeline": []}
    state.itinerary["days"] = [day]
    day.update(primary_label="Hike", primary_summary="Dry conditions.", primary_icon="mountain")
    event = {
        "id": "alternate",
        "kind": "activity",
        "title": "Museum",
        "detail": "",
        "period": "afternoon",
        "icon": "museum",
    }
    day["scenarios"] = [{"id": "rain", "label": "Rain", "icon": "rain", "timeline": [event]}]
    write_state_file(minimal_trip / "itinerary.yaml", state.itinerary)
    assert validate_trip(minimal_trip).ok

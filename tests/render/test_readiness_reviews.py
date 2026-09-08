"""Preparation reviews remain actionable without implying current travel clearance."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from travel_planner.checks import run_checks
from travel_planner.render.html import DEFAULTS, render_html
from travel_planner.render.viewmodel import LinkView, build_view
from travel_planner.state import load_trip, validate_structure, write_state_file
from travel_planner.workspace import initialize_trip


def test_new_trip_starts_with_two_unchecked_reviews(tmp_path):
    paths = initialize_trip(tmp_path / "trip", "Trip", "trip")
    state = load_trip(paths.root)
    items = state.readiness["items"]

    assert {item["category"] for item in items} == {"emergency", "entry"}
    assert len(items) == 2
    assert all(item["status"] == "unknown" for item in items)
    assert all(item["check_result"] and item["recheck_note"] for item in items)
    assert all(item["next_action"] and not item.get("checked_at") for item in items)
    assert all(not item.get("source_ids") for item in items)
    assert run_checks(state).ok


@pytest.mark.parametrize("language", ["en", "ru"])
@pytest.mark.parametrize("checked_at", [None, "2026-08-27T10:00:00+00:00"])
def test_review_result_date_recheck_and_relevant_link_remain_visible(
    japan_state, japan_report, language, checked_at
):
    japan_state.brief["document_language"] = language
    japan_state.candidates["sources"].append({
        "id": "official-entry", "url": "https://example.gov/entry",
        "source_type": "official", "publisher": "Immigration authority",
        "title": "Entry & transit", "retrieved_at": "2026-08-26T10:00:00+00:00",
    })
    japan_state.readiness["items"] = [{
        "id": "review-entry", "category": "entry",
        "status": "confirmed" if checked_at else "unknown", "title": "Entry review",
        "check_result": "Reviewed for the recorded traveller." if checked_at else "Citizenship missing.",
        "checked_at": checked_at,
        "recheck_note": "Before booking and departure; if transit changes.",
        "next_action": "Consult the authority for this traveller.",
        "source_ids": ["official-entry"],
    }]
    view = build_view(japan_state, japan_report, datetime(2026, 8, 28, 12, tzinfo=UTC))
    html = render_html(view, media={}, options=DEFAULTS)
    preparation = html.split('id="preparation"', 1)[1].split('id="budget"', 1)[0]

    assert view.readiness[0].status == ("confirmed" if checked_at else "unknown")
    assert japan_state.readiness["items"][0]["check_result"] in preparation
    assert "Before booking and departure; if transit changes." in preparation
    assert "Consult the authority for this traveller." in preparation
    assert ('Обязательно перепроверить' if language == 'ru' else 'Recheck required') in preparation
    assert (checked_at or ('Не проверено' if language == 'ru' else 'Not checked')) in preparation
    assert 'href="https://example.gov/entry"' in preparation
    assert 'Entry &amp; transit' in preparation
    assert "2026-08-26" not in preparation  # Opening a source is not reviewing this trip.
    assert "<details" not in preparation and " hidden" not in preparation
    assert "no-print" not in preparation


def test_legacy_readiness_does_not_acquire_a_review_result(japan_state, japan_report):
    japan_state.readiness["items"] = [{
        "id": "hotel", "category": "lodging", "status": "booked", "title": "Hotel",
    }]
    view = build_view(japan_state, japan_report, datetime(2026, 8, 28, 12, tzinfo=UTC))
    html = render_html(view, media={}, options=DEFAULTS)
    preparation = html.split('id="preparation"', 1)[1].split('id="budget"', 1)[0]

    assert "Hotel" in preparation
    assert "Not checked" not in preparation
    assert "Recheck required" not in preparation


def test_readiness_link_rejects_an_unsafe_url_in_a_direct_view(japan_view):
    item = replace(japan_view.readiness[0], links=(
        LinkView("Authority", "javascript:alert(1)", "reference", True),
    ))

    with pytest.raises(ValueError, match="absolute HTTPS"):
        render_html(replace(japan_view, readiness=(item,)), media={}, options=DEFAULTS)


@pytest.mark.parametrize("field,value", [
    ("checked_at", "2026-08-27T10:00:00"),
    ("checked_at", "not-a-date"),
    ("check_result", True),
    ("recheck_note", ["later"]),
])
def test_review_fields_reject_malformed_recorded_values(japan_state, field, value):
    japan_state.readiness["items"] = [{
        "id": "review-entry", "category": "entry", "status": "unknown", field: value,
    }]

    write_state_file(japan_state.root / "readiness.yaml", japan_state.readiness)
    report = validate_structure(japan_state.root)

    assert not report.ok
    assert any(f"items[0].{field}" in error.path for error in report.issues)

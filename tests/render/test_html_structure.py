import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from travel_planner.challenge import run_challenge
from travel_planner.cli import main
from travel_planner.render.html import (
    DEFAULTS,
    HtmlOptions,
    MediaAsset,
    render_html,
    write_html,
)
from travel_planner.render.qa import QaReport
from travel_planner.render.viewmodel import ItineraryView, build_view
from travel_planner.state import load_trip


def test_html_contains_required_semantic_reading_order(japan_view: ItineraryView) -> None:
    """Catch a dashboard-like layout that buries route, decisions, or warnings."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    assert html.index('id="trip-summary"') < html.index('id="route-overview"')
    assert html.index('id="open-decisions"') < html.index('id="day-1"')
    assert html.index('id="preparation"') < html.index('id="budget"')
    assert html.index('id="risks"') < html.index('id="sources"')
    assert '<a class="skip-link" href="#main-content">Skip to itinerary</a>' in html
    assert "<header" in html and "<nav" in html and "<main" in html and "<footer" in html


def test_day_filters_expose_synced_overview_and_visible_empty_state(
    japan_view: ItineraryView,
) -> None:
    """Catch filters hiding detailed articles while leaving the overview misleadingly unchanged."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    for day in japan_view.days:
        assert f'data-day-overview="{day.day_id}"' in html
    assert 'data-filter-results' in html
    assert 'data-filter-empty' in html
    assert 'data-reset-filters' in html


def test_html_is_self_contained_but_keeps_labelled_external_actions(
    japan_view: ItineraryView,
) -> None:
    """Catch a local document that silently requires remote CSS, scripts, fonts, or images."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    assert '<link rel="stylesheet"' not in html
    assert "<script src=" not in html
    assert 'src="http' not in html
    assert "@import" not in html
    assert "https://www.google.com/maps" in html
    assert "Internet required" in html
    assert "--mineral: #edf1ec" in html.lower()


def test_renderer_escapes_untrusted_trip_text(japan_view: ItineraryView) -> None:
    """Catch canonical text becoming executable markup in a shared local file."""
    from dataclasses import replace

    hostile = replace(japan_view, title='<script id="injected">alert(1)</script>')

    html = render_html(hostile, media={}, options=DEFAULTS)

    assert '<script id="injected">' not in html
    assert "&lt;script id=&#34;injected&#34;&gt;" in html


def test_renderer_rejects_non_https_external_urls(japan_view: ItineraryView) -> None:
    """Catch an untrusted canonical URL becoming a javascript or local-file action."""
    from dataclasses import replace

    hostile_source = replace(japan_view.sources[0], url="javascript:alert(1)")
    hostile = replace(japan_view, sources=(hostile_source, *japan_view.sources[1:]))

    with pytest.raises(ValueError, match="HTTPS"):
        render_html(hostile, media={}, options=DEFAULTS)


def test_optional_media_requires_provenance(japan_view: ItineraryView) -> None:
    """Catch an embedded photograph shipping without a source and reusable licence record."""
    unlicensed = MediaAsset(b"image", "image/jpeg", "Garden", "", "")

    with pytest.raises(ValueError, match="source and license"):
        render_html(japan_view, media={"day-3": unlicensed}, options=HtmlOptions())


def test_optional_media_has_a_visible_failure_fallback(japan_view: ItineraryView) -> None:
    """Catch a failed embedded photo leaving a broken image with no useful explanation."""
    media = MediaAsset(b"invalid-image", "image/jpeg", "Garden", "photo-1", "CC BY 4.0")

    html = render_html(japan_view, media={"day-3": media}, options=DEFAULTS)

    assert 'data-optional-media' in html
    assert 'data-media-fallback' in html
    assert "Photo unavailable; the day plan remains complete." in html


def test_html_is_deterministic_and_write_helper_uses_exact_bytes(
    japan_view: ItineraryView, tmp_path: Path
) -> None:
    """Catch hidden clock reads or a write path that alters the rendered document."""
    first = render_html(japan_view, media={}, options=DEFAULTS)
    second = render_html(japan_view, media={}, options=DEFAULTS)
    target = write_html(japan_view, tmp_path / "japan.html", DEFAULTS)

    assert hashlib.sha256(first.encode()).digest() == hashlib.sha256(second.encode()).digest()
    assert target.read_text(encoding="utf-8") == first


def test_japan_reference_matches_reviewable_html_snapshot(japan_view: ItineraryView) -> None:
    """Catch an unreviewed whole-document change across the self-contained renderer boundary."""
    expected = (
        Path(__file__).parent / "snapshots" / "japan.html.sha256"
    ).read_text(encoding="utf-8").strip()

    actual = hashlib.sha256(render_html(japan_view, media={}, options=DEFAULTS).encode()).hexdigest()

    assert actual == expected


def test_final_ui_state_fixture_uses_the_canonical_renderer_and_has_no_blockers() -> None:
    """Catch a visual Final state fabricated by relabelling a Draft document."""
    repository = Path(__file__).parents[2]
    fixture = repository / "tests" / "fixtures" / "japan-final-reference"
    generated_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    state = load_trip(fixture)
    challenge = run_challenge(state, "detailed", generated_at)
    view = build_view(state, challenge, generated_at, qa_attested=True)

    assert view.status == "final"
    assert view.summary.blockers == ()
    assert view.summary.readiness_confirmed == view.summary.readiness_total
    assert view.budget.unknown_count == 0
    assert (repository / "tests" / "ui" / "state-fixtures" / "final.html").read_text(
        encoding="utf-8"
    ) == render_html(view, media={}, options=DEFAULTS)


def test_render_cli_writes_html(japan_view: ItineraryView, tmp_path: Path) -> None:
    """Catch the public render command exposing Markdown but not the approved HTML artefact."""
    del japan_view
    output = tmp_path / "japan.html"
    fixture = Path(__file__).parents[1] / "fixtures" / "japan-reference"

    exit_code = main(
        [
            "render",
            str(fixture),
            "--format",
            "html",
            "--output",
            str(output),
            "--at",
            "2026-08-28T12:00:00+00:00",
        ]
    )

    assert exit_code == 0
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_render_cli_downgrades_an_unattested_final_html_to_draft(tmp_path: Path) -> None:
    """Catch a Final label being published before QA approves these exact HTML bytes."""
    output = tmp_path / "japan-final.html"
    fixture = Path(__file__).parents[1] / "fixtures" / "japan-final-reference"

    exit_code = main(
        [
            "render",
            str(fixture),
            "--format",
            "html",
            "--output",
            str(output),
            "--at",
            "2026-08-28T12:00:00+00:00",
        ]
    )

    assert exit_code == 0
    assert ">Draft</span>" in output.read_text(encoding="utf-8")


def test_finalize_cli_publishes_only_the_html_bytes_approved_by_qa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catch finalization publishing different bytes from the HTML that passed QA."""
    output = tmp_path / "japan-final.html"
    fixture = Path(__file__).parents[1] / "fixtures" / "japan-final-reference"
    report = QaReport(
        first_useful_ms=120,
        cumulative_layout_shift=0.01,
        interaction_ms=20,
        focus_visible=True,
        no_js_core=True,
        offline_core=True,
        zoom_200_core=True,
        reduced_motion_core=True,
        filter_sync=True,
        mobile_priority_visible=True,
        state_matrix_complete=True,
    )
    monkeypatch.setattr("travel_planner.cli.run_document_qa", lambda *args, **kwargs: report)

    exit_code = main(
        [
            "finalize",
            str(fixture),
            "--output",
            str(output),
            "--at",
            "2026-08-28T12:00:00+00:00",
        ]
    )

    assert exit_code == 0
    html = output.read_bytes()
    receipt = json.loads(Path(f"{output}.qa.json").read_text(encoding="utf-8"))
    assert ">Final</span>" in html.decode("utf-8")
    assert receipt["sha256"] == hashlib.sha256(html).hexdigest()

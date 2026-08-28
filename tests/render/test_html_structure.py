import hashlib
from pathlib import Path

import pytest
from travel_planner.cli import main
from travel_planner.render.html import (
    DEFAULTS,
    HtmlOptions,
    MediaAsset,
    render_html,
    write_html,
)
from travel_planner.render.viewmodel import ItineraryView


def test_html_contains_required_semantic_reading_order(japan_view: ItineraryView) -> None:
    """Catch a dashboard-like layout that buries route, decisions, or warnings."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    assert html.index('id="trip-summary"') < html.index('id="route-overview"')
    assert html.index('id="open-decisions"') < html.index('id="day-1"')
    assert html.index('id="preparation"') < html.index('id="budget"')
    assert html.index('id="risks"') < html.index('id="sources"')
    assert '<a class="skip-link" href="#main-content">Skip to itinerary</a>' in html
    assert "<header" in html and "<nav" in html and "<main" in html and "<footer" in html


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

import hashlib
import re
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from travel_planner.checks import CheckReport, Finding
from travel_planner.cli import main
from travel_planner.render.html import (
    DEFAULTS,
    HtmlOptions,
    MediaAsset,
    render_html,
    write_html,
)
from travel_planner.render.viewmodel import ItineraryView, build_view

from tests.render.css_contracts import assert_css_rule


def test_html_contains_required_semantic_reading_order(japan_view: ItineraryView) -> None:
    """Catch a dashboard-like layout that buries route, decisions, or warnings."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    assert html.index('id="trip-summary"') < html.index('id="route-overview"')
    assert html.index('id="open-decisions"') < html.index('id="day-1"')
    assert html.index('id="preparation"') < html.index('id="budget"')
    assert html.index('id="risks"') < html.index('id="sources"')
    assert '<a class="skip-link" href="#main-content">Skip to itinerary</a>' in html
    assert "<header" in html and "<nav" in html and "<main" in html and "<footer" in html


def test_html_exposes_lifecycle_and_blocker_groups_without_disclosure(
    japan_state, japan_report
) -> None:
    """Catch lifecycle truth or critical blockers being hidden behind enhanced controls."""
    state = deepcopy(japan_state)
    state.itinerary["verification_level"] = "ai_reviewed"
    generated_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    html = render_html(build_view(state, japan_report, generated_at), media={}, options=DEFAULTS)

    assert "Draft — AI-review" in html
    assert "AI-review — менее точная проверка" in html
    assert 'id="blockers"' in html
    assert "Непринятые блокеры" in html
    blockers = html[html.index('id="blockers"') : html.index('id="route-overview"')]
    assert "Rail booking window is not open yet." in blockers
    assert "<details" not in blockers


@pytest.mark.parametrize(
    ("document_status", "verification_level", "finalization_basis", "label"),
    [
        ("draft", "none", None, "Draft — без проверки"),
        ("draft", "ai_reviewed", None, "Draft — AI-review"),
        (
            "final",
            "codex_validated",
            "codex_validated",
            "Final — проверено в Codex",
        ),
        (
            "final",
            "ai_reviewed",
            "user_confirmed",
            "Final — подтверждено пользователем",
        ),
    ],
)
def test_html_preserves_all_canonical_lifecycle_dimensions(
    japan_state,
    document_status: str,
    verification_level: str,
    finalization_basis: str | None,
    label: str,
) -> None:
    """Catch friendly labels replacing rather than accompanying canonical lifecycle truth."""
    state = deepcopy(japan_state)
    state.itinerary.update(
        document_status=document_status,
        verification_level=verification_level,
        finalization_basis=finalization_basis,
        accepted_blockers=[],
    )
    report = CheckReport((), (), (), ())
    if finalization_basis == "user_confirmed":
        blocker = Finding(
            "blocker-rail",
            "SCHEDULE_UNRELEASED",
            "blocking",
            "itinerary.yaml.days[1]",
            ("day-2",),
            "The final timetable is not released.",
        )
        state.itinerary["accepted_blockers"] = [
            {
                "blocker_id": blocker.id,
                "accepted_by_user": True,
                "accepted_at": "2026-08-30T09:00:00+00:00",
                "rationale": "Accepted explicitly.",
            }
        ]
        report = CheckReport((), (blocker,), (), (blocker.id,))

    html = render_html(
        build_view(state, report, datetime(2026, 8, 28, 12, tzinfo=UTC)),
        media={},
        options=DEFAULTS,
    )

    assert label in html
    assert f"<dt>document_status</dt><dd>{document_status}</dd>" in html
    assert f"<dt>verification_level</dt><dd>{verification_level}</dd>" in html
    basis = finalization_basis or "none"
    assert f"<dt>finalization_basis</dt><dd>{basis}</dd>" in html
    if finalization_basis == "user_confirmed":
        assert "Принятые блокеры" in html
        assert "SCHEDULE_UNRELEASED · Blocking · Unresolved" in html
        assert "Принят пользователем — остаётся блокирующим" in html
        assert "Accepted explicitly." in html


def test_html_marks_a_blocked_codex_final_as_inconsistent(japan_state) -> None:
    """Catch contradictory Codex Final input retaining reassuring status presentation."""
    state = deepcopy(japan_state)
    state.itinerary.update(
        document_status="final",
        verification_level="codex_validated",
        finalization_basis="codex_validated",
    )
    blocker = Finding(
        "blocker-rail",
        "SCHEDULE_UNRELEASED",
        "blocking",
        "itinerary.yaml.days[1]",
        ("day-2",),
        "The final timetable is not released.",
    )
    html = render_html(
        build_view(
            state,
            CheckReport((), (blocker,), (), ()),
            datetime(2026, 8, 28, 12, tzinfo=UTC),
        ),
        media={},
        options=DEFAULTS,
    )

    assert "document-status--unsafe" in html
    assert "Final — несогласованное состояние" in html
    assert 'class="lifecycle-warning" role="alert"' in html
    assert "не следует считать безопасным Final" in html


def test_day_filter_source_exposes_overview_and_empty_state_hooks(
    japan_view: ItineraryView,
) -> None:
    """Catch missing source hooks needed for PR7's manual synchronization checks."""
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


def test_critical_constraints_precede_optional_media_in_the_document_order(
    japan_view: ItineraryView,
) -> None:
    """Catch optional imagery pushing a day's critical warning later on mobile or in print."""
    media = MediaAsset(b"image", "image/jpeg", "Garden", "photo-1", "CC BY 4.0")

    html = render_html(japan_view, media={"day-1": media}, options=HtmlOptions(print_images=True))
    day = html[
        html.index('<article class="day-article" id="day-1"') : html.index(
            '<article class="day-article" id="day-2"'
        )
    ]
    no_javascript = re.sub(r"<script\b[^>]*>.*?</script>", "", day, flags=re.DOTALL)

    assert day.index("Critical constraints") < day.index('data-optional-media')
    assert no_javascript.index("Critical constraints") < no_javascript.index(
        'data-optional-media'
    )
    assert 'class="print-images"' in html


def test_static_css_declares_long_content_wrapping_contract(
    japan_view: ItineraryView,
) -> None:
    """Catch removal of source-level wrapping safeguards without claiming browser layout."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    css = html[html.index("<style>") : html.index("</style>")]

    assert_css_rule(css, ("html",), {"min-width": "20rem"})
    assert_css_rule(css, ("body",), {"overflow-wrap": "anywhere"})
    assert_css_rule(
        css,
        (".trip-hero *", ".document-grid *", ".document-footer *"),
        {"min-width": "0"},
    )
    assert_css_rule(
        css,
        (".budget-table",),
        {"width": "100%", "table-layout": "fixed"},
    )


def test_scenarios_and_day_metadata_keep_semantic_source_wrappers(
    japan_view: ItineraryView,
) -> None:
    """Catch print-oriented heading and metadata groups being flattened in source HTML."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    scenario_groups = re.findall(
        r'<section class="scenario-panel".*?'
        r'<header class="scenario-heading">.*?</header>\s*<p>.*?</p>\s*</section>',
        html,
        flags=re.DOTALL,
    )
    metadata_groups = re.findall(
        r'<div class="metadata-pair"><dt>.*?</dt><dd>.*?</dd></div>',
        html,
    )

    assert len(scenario_groups) == sum(len(day.scenarios) for day in japan_view.days)
    assert len(metadata_groups) == len(japan_view.days) * 4


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
            "--output",
            str(output),
            "--at",
            "2026-08-28T12:00:00+00:00",
        ]
    )

    assert exit_code == 0
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_render_cli_preserves_the_canonical_valid_final_label(tmp_path: Path) -> None:
    """Catch deleted QA-receipt logic silently downgrading a valid canonical Final."""
    output = tmp_path / "japan-final.html"
    fixture = Path(__file__).parents[1] / "fixtures" / "japan-final-reference"

    exit_code = main(
        [
            "render",
            str(fixture),
            "--output",
            str(output),
            "--at",
            "2026-08-28T12:00:00+00:00",
        ]
    )

    assert exit_code == 0
    assert "Final — проверено в Codex" in output.read_text(encoding="utf-8")

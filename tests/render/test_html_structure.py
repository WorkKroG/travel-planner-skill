import hashlib
import re
from copy import deepcopy
from dataclasses import replace
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


def _blocker_section(html: str) -> str:
    return html[html.index('id="blockers"') : html.index('id="route-overview"')]


def _day_section(html: str, day_id: str, next_day_id: str | None = None) -> str:
    start = html.index(f'<article class="day-chapter" id="{day_id}"')
    end_marker = (
        f'<article class="day-chapter" id="{next_day_id}"' if next_day_id else "</section>"
    )
    return html[start : html.index(end_marker, start)]


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
    assert "AI-review — probabilistic review" in html
    assert 'id="blockers"' in html
    assert "Unaccepted blockers" in html
    blockers = _blocker_section(html)
    assert "Rail booking window is not open yet." in blockers
    assert "<details" not in blockers


def test_blocker_section_reports_a_clear_empty_state(japan_state) -> None:
    """Catch an empty blocker section claiming that blockers remain unresolved."""
    view = build_view(
        japan_state,
        CheckReport((), (), (), ()),
        datetime(2026, 8, 28, 12, tzinfo=UTC),
    )

    blockers = _blocker_section(render_html(view, media={}, options=DEFAULTS))

    assert "No blockers are recorded in the canonical trip state." in blockers
    assert "Blockers remain unresolved and blocking" not in blockers
    assert "No unaccepted blockers." in blockers
    assert "No accepted blockers." in blockers


def test_blocker_section_keeps_an_accepted_blocker_unresolved_and_visible(
    japan_state,
) -> None:
    """Catch accepted blockers losing either their explanation or acceptance details."""
    state = deepcopy(japan_state)
    blocker = Finding(
        "blocker-rail",
        "SCHEDULE_UNRELEASED",
        "blocking",
        "itinerary.yaml.days[1]",
        ("day-2",),
        "The final timetable is not released.",
    )
    state.itinerary.update(
        document_status="final",
        verification_level="ai_reviewed",
        finalization_basis="user_confirmed",
        accepted_blockers=[
            {
                "blocker_id": blocker.id,
                "accepted_by_user": True,
                "accepted_at": "2026-08-30T09:00:00+00:00",
                "rationale": "Accepted explicitly.",
            }
        ],
    )
    view = build_view(
        state,
        CheckReport((), (), (), (blocker.id,), (blocker,)),
        datetime(2026, 8, 28, 12, tzinfo=UTC),
    )

    blockers = _blocker_section(render_html(view, media={}, options=DEFAULTS))

    assert (
        "Recorded blockers remain unresolved and blocking for their decisions. Preparing this document does not resolve or accept them."
        in blockers
    )
    assert "SCHEDULE_UNRELEASED · Blocking · Unresolved" in blockers
    assert "Accepted by user — remains blocking" in blockers
    assert "Accepted at: 2026-08-30T09:00:00+00:00 · Rationale: Accepted explicitly." in blockers
    assert "No unaccepted blockers." in blockers


def test_blocker_section_keeps_an_unaccepted_blocker_unresolved_and_visible(
    japan_state,
) -> None:
    """Catch an open blocker losing its unresolved explanation or finding details."""
    blocker = Finding(
        "blocker-rail",
        "SCHEDULE_UNRELEASED",
        "blocking",
        "itinerary.yaml.days[1]",
        ("day-2",),
        "The final timetable is not released.",
    )
    view = build_view(
        japan_state,
        CheckReport((), (blocker,), (), ()),
        datetime(2026, 8, 28, 12, tzinfo=UTC),
    )

    blockers = _blocker_section(render_html(view, media={}, options=DEFAULTS))

    assert (
        "Recorded blockers remain unresolved and blocking for their decisions. Preparing this document does not resolve or accept them."
        in blockers
    )
    assert "SCHEDULE_UNRELEASED · Blocking · Unresolved" in blockers
    assert "The final timetable is not released." in blockers
    assert "No accepted blockers." in blockers


@pytest.mark.parametrize(
    ("document_status", "verification_level", "finalization_basis", "label"),
    [
        ("draft", "none", None, "Draft — unchecked"),
        ("draft", "ai_reviewed", None, "Draft — AI-review"),
        (
            "final",
            "codex_validated",
            "codex_validated",
            "Prepared copy — checked in Codex",
        ),
        (
            "final",
            "ai_reviewed",
            "user_confirmed",
            "Prepared copy — requested by user",
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
        report = CheckReport((), (), (), (blocker.id,), (blocker,))

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
        assert "Accepted blockers" in html
        assert "SCHEDULE_UNRELEASED · Blocking · Unresolved" in html
        assert "Accepted by user — remains blocking" in html
        assert "Accepted explicitly." in html


def test_html_marks_a_recorded_data_error_as_inconsistent(japan_state) -> None:
    """Catch contradictory Codex Final input retaining reassuring status presentation."""
    state = deepcopy(japan_state)
    state.itinerary.update(
        document_status="final",
        verification_level="codex_validated",
        finalization_basis="codex_validated",
    )
    blocker = Finding(
        "blocker-rail",
        "LINK_ROUTE_NOT_FOUND",
        "blocking",
        "itinerary.yaml.days[1]",
        ("day-2",),
        "Recorded route reference does not resolve.",
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
    assert "Prepared copy — inconsistent state" in html
    assert 'class="lifecycle-warning" role="alert"' in html
    assert "cannot be treated as a consistent prepared copy" in html


def test_day_filters_expose_overview_and_empty_state_without_search(
    japan_view: ItineraryView,
) -> None:
    """Catch filters regressing into an unnecessary full-text search interface."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    for day in japan_view.days:
        assert f'data-day-overview="{day.day_id}"' in html
    assert "data-filter-results" in html
    assert "data-filter-empty" in html
    assert "data-reset-filters" in html
    assert 'type="search"' not in html
    assert "data-day-search" not in html


def test_day_chapter_owns_timeline_links_checkpoints_and_local_alternatives(
    japan_view: ItineraryView,
) -> None:
    """Catch the readable timeline regressing into detached context columns."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    day = _day_section(html, "day-1", "day-2")

    assert '<details class="contents">' in html
    assert '<details class="contents" open>' not in html
    assert 'class="timeline-event timeline-event--transport"' in day
    assert 'data-event-id="event-day-1-arrival"' in day
    arrival = day[
        day.index('data-event-id="event-day-1-arrival"') : day.index(
            'data-event-id="event-day-1-check-in"'
        )
    ]
    assert "Build route in Google Maps" in arrival
    assert 'class="event-actions"' in arrival
    assert 'class="checkpoint-contract"' in day
    assert "What to check" in day
    assert "How to change the plan" in day
    dinner = day[day.index('data-event-id="event-day-1-dinner"') :]
    assert "Alternatives (1)" in dinner
    assert "Simple meal at the lodging" in dinner
    assert "Food in context" not in day
    assert "Contextual actions" not in day
    assert "Critical constraints" not in day


def test_each_timeline_event_kind_uses_a_specific_available_icon(
    japan_view: ItineraryView,
) -> None:
    """Catch valid event kinds collapsing into one generic or missing icon."""
    icons = {
        "transport": "route",
        "activity": "activity",
        "meal": "meal",
        "lodging": "lodging",
        "rest": "rest",
        "checkpoint": "stop",
    }
    day = japan_view.days[0]
    seed = day.timeline[0]
    timeline = tuple(
        replace(seed, event_id=f"event-icon-{kind}", kind=kind, title=kind)
        for kind in icons
    )
    view = replace(japan_view, days=(replace(day, timeline=timeline, scenarios=()),))

    html = render_html(view, media={}, options=DEFAULTS)

    for kind, icon in icons.items():
        assert f'<symbol id="icon-{icon}"' in html
        event_start = html.index(f'data-event-id="event-icon-{kind}"')
        marker_start = html.index('<span class="timeline-marker" aria-hidden="true">', event_start)
        marker_end = html.index("</span>", marker_start)
        assert f'href="#icon-{icon}"' in html[marker_start:marker_end]
        assert marker_end < html.index('<h5>', event_start)


def test_material_day_scenarios_are_tabs_over_complete_timelines(
    japan_view: ItineraryView,
) -> None:
    """Catch scenario tabs switching summaries instead of the full day timeline."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    day = _day_section(html, "day-1", "day-2")

    assert 'role="tablist"' in day
    assert 'role="tab"' in day
    assert 'aria-selected="true"' in day
    assert 'data-scenario="primary"' in day
    assert 'data-scenario="alternative-direct-rest"' in day
    assert "Arrival and direct transfer" in day
    assert "Simple nearby meal" in day


def test_valid_scenario_named_primary_has_unique_rendered_identity(
    japan_view: ItineraryView,
) -> None:
    """Catch a valid scenario ID colliding with the renderer-owned primary panel."""
    day = japan_view.days[0]
    scenario = replace(day.scenarios[0], scenario_id="primary")
    view = replace(
        japan_view,
        days=(replace(day, scenarios=(scenario,)), *japan_view.days[1:]),
    )

    html = render_html(view, media={}, options=DEFAULTS)
    rendered_ids = re.findall(r'\bid="(day-1-(?:tab|panel)-[^"]+)"', html)

    assert len(rendered_ids) == len(set(rendered_ids))
    assert 'data-show-scenario="primary"' in html
    assert 'data-show-scenario="alternative-primary"' in html
    assert 'data-scenario="alternative-primary"' in html


def test_day_without_alternatives_has_no_orphan_tabpanel_reference(
    japan_view: ItineraryView,
) -> None:
    """Catch a primary-only day claiming a tab that does not exist."""
    from dataclasses import replace

    primary_only_day = replace(japan_view.days[1], scenarios=())
    primary_only_view = replace(
        japan_view,
        days=(japan_view.days[0], primary_only_day, *japan_view.days[2:]),
    )
    html = render_html(primary_only_view, media={}, options=DEFAULTS)
    day = _day_section(html, "day-2", "day-3")

    assert 'role="tabpanel"' not in day
    assert 'aria-labelledby="day-2-tab-primary"' not in day
    assert (
        '<h4 class="scenario-heading scenario-heading--primary-only">Timeline</h4>'
        in day
    )


def test_russian_document_uses_russian_renderer_labels(japan_state) -> None:
    """Catch localized user content being framed by another language's controls."""
    state = deepcopy(japan_state)
    state.brief["document_language"] = "ru"
    state.brief["title"] = "Япония осенью"
    state.itinerary["days"][0]["region"] = "Токио"
    state.itinerary["budget_items"][0]["amount_type"] = "unknown"
    view = build_view(
        state,
        CheckReport((), (), (), ()),
        datetime(2026, 8, 28, 12, tzinfo=UTC),
    )

    html = render_html(view, media={}, options=DEFAULTS)

    assert '<html lang="ru">' in html
    assert "Перейти к маршруту" in html
    assert "Содержание" in html
    assert "День 1" in html
    assert "Основной" in html
    assert "Время" in html
    assert "Требуется интернет" in html
    assert "Мероприятия" in html
    assert "Сумма неизвестна" in html
    assert "Неизвестно" in html
    assert "Skip to itinerary" not in html
    assert "Contents" not in html
    assert ">activities<" not in html


def test_html_is_self_contained_but_keeps_labelled_external_actions(
    japan_view: ItineraryView,
) -> None:
    """Catch a local document that silently requires remote CSS, scripts, fonts, or images."""
    photo = MediaAsset(
        b"image", "image/jpeg", "Garden", japan_view.sources[0].source_id, "CC BY 4.0",
        "Example Author", "Garden", 1200, 800,
    )
    html = render_html(japan_view, media={"day-1": [photo] * 3}, options=DEFAULTS)

    assert html.count('src="data:image/jpeg;base64,') == 3
    assert '<link rel="stylesheet"' not in html
    assert "<script src=" not in html
    assert 'src="http' not in html
    assert "@import" not in html
    assert "https://www.google.com/maps" in html
    assert "Internet required" in html
    assert "--paper: #fffef8" in html.lower()


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
    unlicensed = MediaAsset(b"image", "image/jpeg", "Garden", "", "", "Author", "Garden", 1200, 800)

    with pytest.raises(ValueError, match="source and license"):
        render_html(japan_view, media={"day-3": [unlicensed]}, options=HtmlOptions())


def test_optional_media_has_a_visible_failure_fallback(japan_view: ItineraryView) -> None:
    """Catch a failed embedded photo leaving a broken image with no useful explanation."""
    media = MediaAsset(
        b"invalid-image", "image/jpeg", "Garden", japan_view.sources[0].source_id,
        "CC BY 4.0", "Example Author", "Garden", 1200, 800,
    )

    html = render_html(japan_view, media={"day-3": [media]}, options=DEFAULTS)

    assert "data-optional-media" in html
    assert "data-media-fallback" in html
    assert "Photo unavailable; the day plan remains complete." in html


def test_gallery_opens_the_day_before_the_complete_timeline(
    japan_view: ItineraryView,
) -> None:
    """Keep the approved header gallery without dropping the checkpoint or its actions."""
    media = MediaAsset(
        b"image", "image/jpeg", "Garden", japan_view.sources[0].source_id,
        "CC BY 4.0", "Example Author", "Garden", 1200, 800,
    )

    html = render_html(japan_view, media={"day-1": [media]}, options=HtmlOptions(print_images=True))
    day = html[
        html.index('<article class="day-chapter" id="day-1"') : html.index(
            '<article class="day-chapter" id="day-2"'
        )
    ]
    no_javascript = re.sub(r"<script\b[^>]*>.*?</script>", "", day, flags=re.DOTALL)

    for content in (day, no_javascript):
        assert content.index('class="day-thesis"') < content.index('class="day-gallery ')
        assert content.index('class="day-gallery ') < content.index('class="day-meta"')
        assert content.index('class="day-meta"') < content.index('class="scenario-stack"')
        assert content.index('class="day-gallery ') < content.index("</header>")
        assert "What to check" in content and "How to change the plan" in content
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
        (".trip-hero *", ".document-shell *", ".document-footer *"),
        {"min-width": "0"},
    )
    assert_css_rule(
        css,
        (".budget-table",),
        {"width": "100%", "table-layout": "fixed"},
    )


def test_static_css_declares_reading_column_and_nonsticky_contents(
    japan_view: ItineraryView,
) -> None:
    """Catch the page returning to a permanent sidebar or multi-column day dashboard."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    css = html[html.index("<style>") : html.index("</style>")]

    assert_css_rule(
        css,
        (".document-shell",),
        {"width": "min(100% - 2rem, 58rem)", "margin-inline": "auto"},
    )
    assert_css_rule(css, (".contents",), {"position": "static"})
    assert_css_rule(
        css,
        ("main",),
        {"width": "min(100%, 54rem)", "margin-inline": "auto"},
    )
    assert_css_rule(
        css,
        ("button", ".external-link", ".day-nav a"),
        {"min-height": "var(--control)"},
    )
    assert_css_rule(
        css,
        (".day-chapter",),
        {"background": "var(--paper)"},
    )


def test_scenarios_and_day_metadata_keep_semantic_source_wrappers(
    japan_view: ItineraryView,
) -> None:
    """Catch print-oriented heading and metadata groups being flattened in source HTML."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    scenario_groups = re.findall(
        r'<section class="scenario-panel [^"]+".*?data-scenario="[^"]+".*?</section>',
        html,
        flags=re.DOTALL,
    )
    metadata_groups = re.findall(r'<dl class="day-meta">(.*?)</dl>', html, re.DOTALL)

    expected_scenarios = len(japan_view.days) + sum(
        len(day.scenarios) for day in japan_view.days
    )
    assert len(scenario_groups) == expected_scenarios
    assert all(group.count("<dt>") == 3 for group in metadata_groups)


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
        (Path(__file__).parent / "snapshots" / "japan.html.sha256")
        .read_text(encoding="utf-8")
        .strip()
    )

    actual = hashlib.sha256(
        render_html(japan_view, media={}, options=DEFAULTS).encode()
    ).hexdigest()

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
    assert "Prepared copy — checked in Codex" in output.read_text(encoding="utf-8")

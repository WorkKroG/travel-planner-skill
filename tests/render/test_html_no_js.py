import re

import pytest
from travel_planner.render.html import DEFAULTS, render_html
from travel_planner.render.viewmodel import ItineraryView

from tests.render.css_contracts import assert_css_rule

CRITICAL_PRINT_SELECTORS = (
    ".warning-block",
    ".blocker-item",
    ".checkpoint-contract",
    ".day-meta",
    ".timeline-event",
    ".event-alternative",
    ".decision-item",
    ".readiness-item",
    ".risk-item",
)


def _without_javascript(html: str) -> str:
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.DOTALL)


def test_primary_and_backup_exist_without_javascript(japan_view: ItineraryView) -> None:
    """Catch progressive enhancement hiding the fallback itinerary from no-JS readers."""
    html = _without_javascript(render_html(japan_view, media={}, options=DEFAULTS))

    assert 'data-scenario="primary"' in html
    assert 'data-scenario="alternative-direct-rest"' in html
    assert "Arrival and transfer" in html
    assert "Arrival and direct transfer" in html
    assert 'data-scenario="alternative-direct-rest" hidden' not in html


def test_no_javascript_keeps_controls_hidden_and_event_alternatives_expanded(
    japan_view: ItineraryView,
) -> None:
    """Catch enhancement-only controls leaking into or hiding content in the fallback."""
    html = _without_javascript(render_html(japan_view, media={}, options=DEFAULTS))

    assert 'class="scenario-tabs interactive-controls" data-scenario-tabs hidden' in html
    assert '<details class="event-alternatives"' in html
    assert re.search(r'<details class="event-alternatives"[^>]* open>', html)
    assert "Simple meal at the lodging" in html


def test_print_keeps_alternatives_when_a_no_javascript_reader_closes_details(
    japan_view: ItineraryView,
) -> None:
    """Catch user-controlled disclosure state removing required print content."""
    html = _without_javascript(render_html(japan_view, media={}, options=DEFAULTS))
    closed = re.sub(
        r'(<details class="event-alternatives"[^>]*) open>',
        r"\1>",
        html,
    )
    print_copy_start = closed.index('<div class="event-alternatives-print"')
    print_copy_end = closed.index("</div>", print_copy_start)
    print_copy = closed[print_copy_start:print_copy_end]
    print_css = closed[closed.index("@media print") :]

    assert "Simple meal at the lodging" in print_copy
    assert_css_rule(
        print_css,
        (".event-alternatives",),
        {"display": "none !important"},
    )
    assert_css_rule(
        print_css,
        (".event-alternatives-print",),
        {"display": "block"},
    )


def test_scenario_tabs_include_keyboard_and_failure_recovery_logic(
    japan_view: ItineraryView,
) -> None:
    """Keep the bounded source-level evidence for accessible progressive enhancement."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert f'event.key === "{key}"' in html
    assert 'candidate.setAttribute("aria-selected", String(active))' in html
    assert "panel.hidden = panel.dataset.scenario !== selected" in html
    assert 'root.classList.add("enhancement-failed")' in html
    assert "panel.hidden = false" in html
    assert "tablist.hidden = false" in html
    assert "tablist.hidden = true" in html
    assert "disclosure.open = true" in html


def test_contents_and_all_core_sections_remain_linked_without_javascript(
    japan_view: ItineraryView,
) -> None:
    """Catch JavaScript becoming a gate for document navigation or core reading."""
    html = _without_javascript(render_html(japan_view, media={}, options=DEFAULTS))

    assert '<details class="contents">' in html
    for anchor in (
        "#trip-summary",
        "#blockers",
        "#route-overview",
        "#open-decisions",
        "#day-1",
        "#preparation",
        "#budget",
        "#risks",
    ):
        assert f'href="{anchor}"' in html
    assert "Rail booking window is not open yet." in html
    assert 'id="blockers"' in html


def test_print_static_css_keeps_both_scenarios_and_removes_interactive_chrome(
    japan_view: ItineraryView,
) -> None:
    """Catch print-source rules inheriting an ambiguous switched scenario state."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    assert "@media print" in html
    assert ".scenario-panel[hidden]" in html
    assert "display: block !important" in html
    assert ".interactive-controls" in html
    assert "display: none !important" in html
    assert "article[data-day][hidden]" in html
    assert ".day-overview li[hidden]" in html
    print_css = html[html.index("@media print") :]
    assert_css_rule(print_css, CRITICAL_PRINT_SELECTORS, {"break-inside": "avoid"})
    assert_css_rule(
        print_css,
        (".scenario-heading",),
        {"break-after": "avoid", "break-inside": "avoid"},
    )
    assert_css_rule(
        print_css,
        (".scenario-summary",),
        {"orphans": "2", "widows": "2"},
    )
    assert_css_rule(print_css, (".day-chapter",), {"break-before": "page"})
    assert_css_rule(
        print_css,
        (".event-print-context",),
        {"display": "block"},
    )
    assert "string-set" not in print_css
    assert "string(day-title)" not in print_css


def test_print_document_keeps_event_context_and_clickable_actions(japan_view):
    html = render_html(japan_view, media={}, options=DEFAULTS)
    assert "Day 1 · November 2, 2026 · Tokyo" in html
    assert 'href="https://www.google.com/maps/search/?api=1&amp;query=Tokyo"' in html
    assert 'class="print-link-appendix"' not in html


def test_print_critical_group_contract_rejects_auto_mutation(
    japan_view: ItineraryView,
) -> None:
    """Catch the critical group losing page-break protection while another rule keeps it."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    print_css = html[html.index("@media print") :]
    rule_start = print_css.index(".warning-block,")
    rule_end = print_css.index("}", rule_start) + 1
    critical_rule = print_css[rule_start:rule_end]
    assert "break-inside: avoid;" in critical_rule
    mutated_rule = critical_rule.replace("break-inside: avoid;", "break-inside: auto;", 1)
    mutated_css = print_css[:rule_start] + mutated_rule + print_css[rule_end:]

    with pytest.raises(AssertionError, match=r"break-inside: expected 'avoid'"):
        assert_css_rule(
            mutated_css,
            CRITICAL_PRINT_SELECTORS,
            {"break-inside": "avoid"},
        )


def test_print_removes_the_fixed_page_decoration(japan_view: ItineraryView) -> None:
    """Catch the fixed background layer generating a mostly blank trailing print page."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    print_css = html[html.index("@media print") :]

    assert "body::before" in print_css
    assert "display: none !important" in print_css[print_css.index("body::before") :]


def test_print_keeps_version_provenance_without_a_footer_only_page(
    japan_view: ItineraryView,
) -> None:
    """Catch version provenance depending on a screen footer that paginates alone."""
    html = render_html(japan_view, media={}, options=DEFAULTS)
    footer = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.DOTALL)[1]
    print_css = html[html.index("@media print") :]

    assert 'id="document-version"' in html
    assert japan_view.status_label in footer
    assert japan_view.generated_at.isoformat() in footer
    assert_css_rule(
        print_css,
        (".document-footer",),
        {"display": "block !important", "position": "fixed"},
    )
    assert '@bottom-right { content: counter(page) " / " counter(pages); }' in print_css

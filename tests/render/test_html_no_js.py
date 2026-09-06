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
    ".source-item",
)


def _without_javascript(html: str) -> str:
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.DOTALL)


def test_primary_and_backup_exist_without_javascript(japan_view: ItineraryView) -> None:
    """Catch progressive enhancement hiding the fallback itinerary from no-JS readers."""
    html = _without_javascript(render_html(japan_view, media={}, options=DEFAULTS))

    assert 'data-scenario="primary"' in html
    assert 'data-scenario="direct-rest"' in html
    assert "Arrival and transfer" in html
    assert "Arrival and direct transfer" in html
    assert 'data-scenario="direct-rest" hidden' not in html


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
        "#sources",
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
        (".day-title-group h3",),
        {"string-set": "day-title content()"},
    )
    assert_css_rule(print_css, (".day-date",), {"string-set": "day-date content()"})
    assert '@top-right { content: string(day-title) " · " string(day-date); }' in print_css
    assert_css_rule(
        print_css,
        (".event-alternatives > :not(summary)",),
        {"display": "block !important"},
    )


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
    sources = html[html.index('id="sources"') : html.index("</main>")]
    print_css = html[html.index("@media print") :]

    assert 'id="document-version"' in sources
    assert japan_view.status_label in sources
    assert japan_view.generated_at.isoformat() in sources
    footer_rules = print_css[print_css.index(".document-footer") :]
    assert "display: none !important" in footer_rules

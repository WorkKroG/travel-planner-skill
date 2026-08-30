import re

from travel_planner.render.html import DEFAULTS, render_html
from travel_planner.render.viewmodel import ItineraryView


def _without_javascript(html: str) -> str:
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.DOTALL)


def test_primary_and_backup_exist_without_javascript(japan_view: ItineraryView) -> None:
    """Catch progressive enhancement hiding the fallback itinerary from no-JS readers."""
    html = _without_javascript(render_html(japan_view, media={}, options=DEFAULTS))

    assert 'data-scenario="primary"' in html
    assert 'data-scenario="backup"' in html
    assert "Short neighbourhood walk" in html
    assert "Direct rest" in html
    assert 'data-scenario="backup" hidden' not in html


def test_contents_and_all_core_sections_remain_linked_without_javascript(
    japan_view: ItineraryView,
) -> None:
    """Catch JavaScript becoming a gate for document navigation or core reading."""
    html = _without_javascript(render_html(japan_view, media={}, options=DEFAULTS))

    assert '<details class="contents" open>' in html
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


def test_print_keeps_both_scenarios_and_removes_interactive_chrome(
    japan_view: ItineraryView,
) -> None:
    """Catch a printed route inheriting an ambiguous switched scenario state."""
    html = render_html(japan_view, media={}, options=DEFAULTS)

    assert "@media print" in html
    assert ".scenario-panel[hidden]" in html
    assert "display: block !important" in html
    assert ".interactive-controls" in html
    assert "display: none !important" in html
    assert "article[data-day][hidden]" in html
    assert ".day-overview li[hidden]" in html
    print_css = html[html.index("@media print") :]
    assert ".source-item" in print_css
    assert ".metadata-pair" in print_css
    assert ".timeline-event" in print_css
    assert ".constraint-list li" in print_css
    assert "break-inside: avoid" in print_css
    assert ".scenario-heading" in print_css
    assert "break-after: avoid" in print_css
    assert ".scenario-panel > p" in print_css
    assert "orphans: 2" in print_css


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

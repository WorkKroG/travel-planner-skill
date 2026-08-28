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
        "#route-overview",
        "#open-decisions",
        "#day-1",
        "#preparation",
        "#budget",
        "#risks",
        "#sources",
    ):
        assert f'href="{anchor}"' in html


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

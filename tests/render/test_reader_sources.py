"""Research remains technical data while practical links belong to program events."""

import re
from datetime import UTC, datetime

import pytest
from travel_planner.render.html import DEFAULTS, render_html
from travel_planner.render.viewmodel import build_view


@pytest.mark.parametrize("language", ["en", "ru"])
def test_reader_has_event_links_without_a_research_index(japan_state, japan_report, language):
    japan_state.brief["document_language"] = language
    japan_state.candidates["sources"][0]["provenance"] = "TECHNICAL-ONLY-PROVENANCE"
    view = build_view(japan_state, japan_report, datetime(2026, 9, 8, tzinfo=UTC))
    html = render_html(view, {}, DEFAULTS)
    assert 'id="sources"' not in html
    assert 'href="#sources"' not in html
    assert 'class="day-sources"' not in html
    assert 'class="day-sources-print"' not in html
    assert 'class="print-link-appendix"' not in html
    assert "TECHNICAL-ONLY-PROVENANCE" not in html
    for day in view.days:
        for timeline in [day.timeline, *(scenario.timeline for scenario in day.scenarios)]:
            for event in timeline:
                for link in event.links:
                    from html import escape

                    assert f'href="{escape(link.url, quote=True)}"' in html
    footer = re.search(r'<footer\b[^>]*>(.*?)</footer>', html, re.DOTALL)[1]
    assert view.trip_id in footer and view.generated_at.isoformat() in footer
    assert view.status_label in footer

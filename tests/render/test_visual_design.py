"""Approved design source contracts, not browser layout or visual QA."""

import re
from dataclasses import replace

import pytest
from travel_planner.render.html import DEFAULTS, render_html

from tests.render.css_contracts import assert_css_rule


def test_shared_document_uses_the_approved_palette_and_continuous_timeline(japan_view):
    html = render_html(japan_view, {}, DEFAULTS)
    css = html[html.index('<style>') + len('<style>'):html.index('</style>')]
    assert_css_rule(css, (':root',), {
        '--paper': '#fffef8', '--heading-field': '#ffe785', '--ink': '#153369',
        '--ink-soft': '#3b5271', '--accent': '#1649b5', '--selected': '#1747ab',
        '--checkpoint-field': '#fff0b7', '--timeline-line': '#acbee0',
        '--info-field': '#e7efff',
    })
    assert_css_rule(css, ('.trip-hero',), {'background': 'var(--heading-field)'})
    assert_css_rule(css, ('.day-heading',), {'background': 'var(--heading-field)'})
    assert_css_rule(css, ('.timeline::before',), {'background': 'var(--timeline-line)'})
    assert_css_rule(css, ('.timeline-event--checkpoint .event-body',), {
        'background': 'var(--checkpoint-field)',
    })
    assert 'nth-of-type(3n' not in css


def test_gallery_crop_compositions_and_mobile_order_have_explicit_source_rules(japan_view):
    html = render_html(japan_view, {}, DEFAULTS)
    css = html[html.index('<style>') + len('<style>'):html.index('</style>')]
    assert_css_rule(css, ('.day-gallery',), {'gap': '0.75rem'})
    for count, ratio in ((1, '2.8 / 1'), (2, '1.42 / 1'), (3, '1.3 / 1')):
        assert_css_rule(css, (f'.day-gallery--{count} img',), {'aspect-ratio': ratio})
    assert_css_rule(css, ('.day-photo img',), {
        'object-fit': 'cover', 'border-radius': '12px',
    })
    mobile = css[css.index('@media (max-width: 760px)'):css.index('@media print')]
    assert_css_rule(mobile, ('.day-gallery',), {'grid-template-columns': 'minmax(0, 1fr)'})
    assert_css_rule(mobile, ('.day-gallery img',), {'aspect-ratio': '1.9 / 1'})


@pytest.mark.parametrize('weather_sensitive', [True, False])
def test_scenario_icons_use_recorded_semantics_and_leave_labels_intact(
    japan_view, weather_sensitive,
):
    day = replace(japan_view.days[0], weather_sensitive=weather_sensitive)
    view = replace(japan_view, days=(day,))
    html = render_html(view, {}, DEFAULTS)
    buttons = re.findall(r'<button\b[^>]*data-show-scenario="([^"]+)"[^>]*>(.*?)</button>',
                         html, re.DOTALL)
    assert len(buttons) == 1 + len(day.scenarios)
    for key, content in buttons:
        assert '<svg class="icon" aria-hidden="true">' in content
        if key == 'primary':
            assert 'href="#icon-route"' in content
            assert 'Primary' in content
        else:
            icon = 'cloud' if weather_sensitive else 'conflict'
            assert f'href="#icon-{icon}"' in content
            assert any(scenario.label in content for scenario in day.scenarios)

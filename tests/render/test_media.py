"""Day galleries keep their order, attribution and local asset boundary."""

import base64
import re
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from travel_planner.render.html import DEFAULTS, HtmlOptions, MediaAsset, render_html, write_html
from travel_planner.render.viewmodel import build_view

from tests.render.css_contracts import assert_css_rule


def photo(source_id, number=1):
    return MediaAsset(
        content=f"photo-{number}".encode(), mime_type="image/jpeg",
        alt=f"Lake and mountains {number}", source_id=source_id, license="CC BY-SA 4.0",
        attribution="Example Author", caption=f"Lake {number}", width=1280, height=853,
    )


@pytest.mark.parametrize("count", [1, 2, 3])
def test_gallery_keeps_every_image_in_authored_order(japan_view, tmp_path, count):
    photos = [photo(japan_view.sources[0].source_id, n) for n in range(1, count + 1)]
    media = {"day-1": photos}
    html = render_html(japan_view, media, DEFAULTS)
    assert f'class="day-gallery day-gallery--{count}"' in html
    assert html.count('<figure class="day-photo"') == count
    for n, asset in enumerate(photos, 1):
        assert f'alt="Lake and mountains {n}"' in html
        assert f"data:image/jpeg;base64,{base64.b64encode(asset.content).decode()}" in html
    assert html.index('alt="Lake and mountains 1"') <= html.index(
        f'alt="Lake and mountains {count}"'
    )
    assert 'width="1280" height="853"' in html
    assert "Example Author" in html and "CC BY-SA 4.0" in html
    assert f'href="{japan_view.sources[0].url}"' in html
    assert html == render_html(japan_view, media, DEFAULTS)
    assert write_html(japan_view, tmp_path / "gallery.html", DEFAULTS, media=media).read_text() == html


@pytest.mark.parametrize("media", [{}, {"day-1": []}])
def test_absent_media_has_no_empty_gallery(japan_view, media):
    assert '<div class="day-gallery' not in render_html(japan_view, media, DEFAULTS)


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"alt": "  "}, "alt"), ({"caption": ""}, "caption"),
        ({"attribution": "\n"}, "attribution"), ({"license": " "}, "license"),
        ({"source_id": "missing"}, "source"), ({"content": b""}, "empty"),
        ({"mime_type": "image/svg+xml"}, "type"),
        ({"width": 0}, "dimensions"), ({"height": True}, "dimensions"),
    ],
)
def test_invalid_media_is_rejected(japan_view, changes, message):
    asset = replace(photo(japan_view.sources[0].source_id), **changes)
    with pytest.raises(ValueError, match=message):
        render_html(japan_view, {"day-1": [asset]}, DEFAULTS)


def test_gallery_limit_and_unknown_day_are_not_silently_truncated(japan_view):
    asset = photo(japan_view.sources[0].source_id)
    with pytest.raises(ValueError, match="3"):
        render_html(japan_view, {"day-1": [asset] * 4}, DEFAULTS)
    with pytest.raises(ValueError, match="day"):
        render_html(japan_view, {"missing-day": [asset]}, DEFAULTS)


def test_source_import_provenance_survives_projection_and_escaping(japan_state, japan_report):
    note = "Imported from supplied HTML; remote source not rechecked. <img onerror=alert(1)>"
    japan_state.candidates["sources"][0]["provenance"] = note
    view = build_view(japan_state, japan_report, datetime(2026, 9, 7, tzinfo=UTC))
    source_id = japan_state.candidates["sources"][0]["id"]
    assert next(source for source in view.sources if source.source_id == source_id).provenance == note
    html = render_html(view, {}, DEFAULTS)
    assert "remote source not rechecked." in html
    assert "&lt;img onerror=alert(1)&gt;" in html


def test_media_copy_is_escaped_and_omission_option_hides_the_whole_gallery(japan_view):
    asset = replace(photo(japan_view.sources[0].source_id),
                    alt='Lake" onload="alert(1)', caption="<script>caption</script>",
                    attribution="<b>author</b>", license="<i>licence</i>")
    html = render_html(japan_view, {"day-1": [asset]}, DEFAULTS)
    assert ' onload="' not in html
    assert "&lt;script&gt;caption&lt;/script&gt;" in html
    assert "&lt;b&gt;author&lt;/b&gt;" in html
    assert "&lt;i&gt;licence&lt;/i&gt;" in html
    hidden = render_html(japan_view, {"day-1": [asset]}, HtmlOptions(include_optional_media=False))
    assert '<div class="day-gallery' not in hidden


def test_gallery_css_and_no_js_keep_reading_and_print_contracts(japan_view):
    asset = photo(japan_view.sources[0].source_id)
    html = render_html(japan_view, {"day-1": [asset] * 3}, DEFAULTS)
    without_js = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    assert without_js.count('<figure class="day-photo"') == 3
    css = html[html.index("<style>"):html.index("</style>")]
    assert_css_rule(css, (".day-gallery--2",), {"grid-template-columns": "repeat(2, minmax(0, 1fr))"})
    assert_css_rule(css, (".day-gallery--3",), {"grid-template-columns": "repeat(3, minmax(0, 1fr))"})
    mobile_css = css[css.index("@media (max-width: 760px)"):]
    assert_css_rule(mobile_css, (".day-gallery",), {"grid-template-columns": "minmax(0, 1fr)"})
    print_css = css[css.index("@media print"):]
    assert_css_rule(print_css, (".day-photo",), {"break-inside": "avoid"})
    assert_css_rule(print_css, (".no-print-images .day-gallery", "body:not(.print-images) .day-gallery"), {"display": "none"})


def test_print_credit_identifies_each_photos_source(japan_view):
    source_id = japan_view.sources[0].source_id
    html = render_html(japan_view, {"day-1": [photo(source_id)]}, DEFAULTS)
    caption = re.search(r"<figcaption>(.*?)</figcaption>", html, re.DOTALL).group(1)
    assert f'<span class="print-media-source"> · {source_id}</span>' in caption
    css = html[html.index("<style>"):html.index("</style>")]
    assert_css_rule(css[:css.index("@media print")], (".print-media-source",), {"display": "none"})
    assert_css_rule(css[css.index("@media print"):], (".print-media-source",), {"display": "inline"})

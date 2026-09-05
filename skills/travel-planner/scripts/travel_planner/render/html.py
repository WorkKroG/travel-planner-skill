"""Self-contained Curated Route HTML rendering."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from ..budget import format_money
from ..resources import resource_path
from .viewmodel import ItineraryView

_SUPPORTED_MEDIA = frozenset({"image/jpeg", "image/png", "image/webp", "image/avif"})


@dataclass(frozen=True)
class HtmlOptions:
    include_optional_media: bool = True
    print_images: bool = True


DEFAULTS = HtmlOptions()


@dataclass(frozen=True)
class MediaAsset:
    content: bytes
    mime_type: str
    alt: str
    source_id: str
    license: str


@dataclass(frozen=True)
class EmbeddedMedia:
    data_url: str
    alt: str
    source_id: str
    license: str


def embed_media(media: Mapping[str, MediaAsset]) -> dict[str, EmbeddedMedia]:
    """Embed approved raster media only when provenance is complete."""
    embedded: dict[str, EmbeddedMedia] = {}
    for key in sorted(media):
        asset = media[key]
        if not asset.source_id.strip() or not asset.license.strip():
            raise ValueError(f"Optional media {key!r} requires a source and license.")
        if asset.mime_type not in _SUPPORTED_MEDIA:
            raise ValueError(f"Unsupported optional media type for {key!r}: {asset.mime_type}")
        if not asset.content:
            raise ValueError(f"Optional media {key!r} is empty.")
        payload = base64.b64encode(asset.content).decode("ascii")
        embedded[key] = EmbeddedMedia(
            data_url=f"data:{asset.mime_type};base64,{payload}",
            alt=asset.alt,
            source_id=asset.source_id,
            license=asset.license,
        )
    return embedded


def _asset(name: str) -> Path:
    return resource_path("html", name)


def _validate_external_urls(view: ItineraryView) -> None:
    labelled_urls = [
        *((source.source_id, source.url) for source in view.sources),
        *((link.label, link.url) for day in view.days for link in day.links),
    ]
    for label, url in labelled_urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"External link {label!r} must be an absolute HTTPS URL.")


def render_html(
    view: ItineraryView,
    media: Mapping[str, MediaAsset],
    options: HtmlOptions,
) -> str:
    """Render one deterministic document with every required asset inline."""
    _validate_external_urls(view)
    template_path = _asset("itinerary.html.j2")
    environment = Environment(
        loader=FileSystemLoader(template_path.parent),
        autoescape=select_autoescape(("html", "j2"), default=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template(template_path.name)
    optional_media = embed_media(media) if options.include_optional_media else {}
    rendered = template.render(
        money=format_money,
        view=view,
        media=optional_media,
        options=options,
        css=Markup(_asset("styles.css").read_text(encoding="utf-8")),
        js=Markup(_asset("app.js").read_text(encoding="utf-8")),
        icons=Markup(_asset("icons.svg").read_text(encoding="utf-8")),
    )
    return rendered.rstrip() + "\n"


def write_html(
    view: ItineraryView,
    target: Path,
    options: HtmlOptions,
    *,
    media: Mapping[str, MediaAsset] | None = None,
) -> Path:
    """Write exact render bytes to one explicitly selected destination."""
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_html(view, media or {}, options), encoding="utf-8")
    return destination

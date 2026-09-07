"""Load trip-owned raster files and embed ordered day galleries without network access."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from ..state import TripState

SUPPORTED_MEDIA = frozenset({"image/jpeg", "image/png", "image/webp", "image/avif"})


@dataclass(frozen=True)
class MediaAsset:
    content: bytes
    mime_type: str
    alt: str
    source_id: str
    license: str
    attribution: str
    caption: str
    width: int
    height: int


@dataclass(frozen=True)
class EmbeddedMedia:
    data_url: str
    alt: str
    source_id: str
    source_url: str
    license: str
    attribution: str
    caption: str
    width: int
    height: int


def _validate_asset(asset: MediaAsset, label: str) -> None:
    if not asset.source_id.strip() or not asset.license.strip():
        raise ValueError(f"Optional media {label} requires a source and license.")
    for field in ("alt", "attribution", "caption"):
        if not getattr(asset, field).strip():
            raise ValueError(f"Optional media {label} requires nonblank {field}.")
    if asset.mime_type not in SUPPORTED_MEDIA:
        raise ValueError(f"Unsupported optional media type for {label}: {asset.mime_type}")
    if not asset.content:
        raise ValueError(f"Optional media {label} is empty.")
    if any(type(value) is not int or value <= 0 for value in (asset.width, asset.height)):
        raise ValueError(f"Optional media {label} requires positive integer dimensions.")


def load_media(state: TripState) -> dict[str, tuple[MediaAsset, ...]]:
    """Read schema-validated media paths confined to this trip's media directory."""
    root = state.root.resolve()
    result = {}
    for day in state.itinerary.get("days", []):
        photos = []
        for index, record in enumerate(day.get("media", [])):
            label = f"{day['id']}.media[{index}]"
            path = PurePosixPath(record["path"])
            if (
                path.is_absolute() or ".." in path.parts or len(path.parts) < 2
                or path.parts[0] != "media" or "\\" in record["path"] or ":" in record["path"]
            ):
                raise ValueError(f"Optional media {label} requires a relative media/ file path.")
            try:
                target = (root / path).resolve(strict=True)
                if not target.is_relative_to(root / "media"):
                    raise ValueError(f"Optional media {label} escapes the trip media/ directory.")
                if not target.is_file():
                    raise ValueError(f"Optional media {label} requires a regular file.")
                content = target.read_bytes()
            except (OSError, RuntimeError) as error:
                raise ValueError(f"Cannot read optional media {label}: {record['path']}") from error
            metadata = {k: v for k, v in record.items() if k != "path"}
            # JSON Schema integers include YAML values such as 1200.0.
            metadata.update(width=int(record["width"]), height=int(record["height"]))
            asset = MediaAsset(content=content, **metadata)
            _validate_asset(asset, label)
            photos.append(asset)
        if photos:
            result[day["id"]] = tuple(photos)
    return result


def embed_media(
    media: Mapping[str, Sequence[MediaAsset]], source_urls: Mapping[str, str],
) -> dict[str, tuple[EmbeddedMedia, ...]]:
    """Preserve authored image order and retain each resolved source and credit."""
    embedded = {}
    for day_id in sorted(media):
        photos = media[day_id]
        if len(photos) > 3:
            raise ValueError(f"Optional media for {day_id!r} allows at most 3 images.")
        gallery = []
        for index, asset in enumerate(photos):
            label = f"{day_id}.media[{index}]"
            _validate_asset(asset, label)
            if asset.source_id not in source_urls:
                raise ValueError(f"Optional media {label} requires a known source.")
            payload = base64.b64encode(asset.content).decode("ascii")
            gallery.append(EmbeddedMedia(
                data_url=f"data:{asset.mime_type};base64,{payload}", alt=asset.alt,
                source_id=asset.source_id, source_url=source_urls[asset.source_id],
                license=asset.license, attribution=asset.attribution, caption=asset.caption,
                width=asset.width, height=asset.height,
            ))
        if gallery:
            embedded[day_id] = tuple(gallery)
    return embedded

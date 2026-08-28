"""Versioned map-provider policy and safely encoded external map links."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import yaml

from .resources import resource_path


class MapProvider(str, Enum):
    AUTO = "auto"
    YANDEX = "yandex"
    GOOGLE = "google"


@dataclass(frozen=True)
class MapPolicy:
    version: int
    yandex_preferred_country_codes: frozenset[str]
    default_provider: MapProvider


@dataclass(frozen=True)
class MapPlace:
    label: str
    country_code: str
    latitude: float | None = None
    longitude: float | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("Map place label cannot be empty.")
        _country_code(self.country_code)
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be supplied together.")
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90.")
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180.")


@dataclass(frozen=True)
class RouteLeg:
    origin: MapPlace
    destination: MapPlace


@dataclass(frozen=True)
class MapLink:
    provider: MapProvider
    label: str
    url: str
    requires_internet: bool = True


def _country_code(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha() or not normalized.isascii():
        raise ValueError(f"Country code must be a two-letter ISO code: {value!r}")
    return normalized


def _provider(value: str | MapProvider) -> MapProvider:
    try:
        return value if isinstance(value, MapProvider) else MapProvider(value.lower())
    except (AttributeError, ValueError) as error:
        raise ValueError(f"Unknown map provider preference: {value!r}") from error


def load_map_policy(path: Path | None = None) -> MapPolicy:
    """Load and validate the versioned product routing policy."""
    policy_path = path or resource_path("map-policy", "map-provider-policy.yaml")
    raw: Any = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeError("Map policy must be a YAML mapping.")
    try:
        version = int(raw["policy_version"])
        country_codes = frozenset(
            _country_code(str(code)) for code in raw["yandex_preferred_country_codes"]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid map policy: {error}") from error
    try:
        default = _provider(str(raw["default_provider"]))
    except (KeyError, ValueError) as error:
        raise ValueError(f"Invalid map policy default_provider: {error}") from error
    if version < 1:
        raise ValueError("Map policy_version must be positive.")
    if default is MapProvider.AUTO:
        raise ValueError("Map policy default_provider must be concrete.")
    return MapPolicy(version, country_codes, default)


def select_provider(
    country_code: str,
    preference: str | MapProvider,
    policy: MapPolicy,
) -> MapProvider:
    """Resolve an explicit choice or the deterministic destination policy."""
    requested = _provider(preference)
    if requested is not MapProvider.AUTO:
        return requested
    country = _country_code(country_code)
    if country in policy.yandex_preferred_country_codes:
        return MapProvider.YANDEX
    return policy.default_provider


def _coordinate_text(place: MapPlace) -> str | None:
    if place.latitude is None or place.longitude is None:
        return None
    return f"{place.latitude},{place.longitude}"


def _place_query(place: MapPlace) -> str:
    coordinates = _coordinate_text(place)
    return place.label if coordinates is None else f"{coordinates} ({place.label})"


def _https_url(base: str, parameters: Mapping[str, str]) -> str:
    parsed = urlparse(base)
    if parsed.scheme != "https":
        raise ValueError("Map links must use HTTPS.")
    return f"{base}?{urlencode(parameters)}"


def build_place_url(provider: MapProvider, place: MapPlace) -> str:
    """Build an encoded place-search URL with readable text and optional coordinates."""
    concrete = _provider(provider)
    if concrete is MapProvider.AUTO:
        raise ValueError("A concrete map provider is required to build a URL.")
    if concrete is MapProvider.GOOGLE:
        return _https_url(
            "https://www.google.com/maps/search/",
            {"api": "1", "query": _place_query(place)},
        )
    parameters = {"mode": "search", "text": _place_query(place)}
    if place.latitude is not None and place.longitude is not None:
        parameters["ll"] = f"{place.longitude},{place.latitude}"
    return _https_url("https://yandex.com/maps/", parameters)


def _route_url(provider: MapProvider, leg: RouteLeg) -> str:
    if provider is MapProvider.GOOGLE:
        return _https_url(
            "https://www.google.com/maps/dir/",
            {
                "api": "1",
                "origin": _place_query(leg.origin),
                "destination": _place_query(leg.destination),
            },
        )
    origin = _coordinate_text(leg.origin) or leg.origin.label
    destination = _coordinate_text(leg.destination) or leg.destination.label
    return _https_url(
        "https://yandex.com/maps/",
        {
            "mode": "routes",
            "rtext": f"{origin}~{destination}",
            "text": f"{leg.origin.label} → {leg.destination.label}",
        },
    )


def build_route_urls(
    leg: RouteLeg,
    preference: str | MapProvider,
    policy: MapPolicy,
) -> tuple[MapLink, ...]:
    """Build a primary route and an explicit cross-border fallback when auto-routing."""
    requested = _provider(preference)
    primary = select_provider(leg.origin.country_code, requested, policy)
    links = [
        MapLink(primary, f"{primary.value.title()} Maps — primary", _route_url(primary, leg))
    ]
    crosses_border = _country_code(leg.origin.country_code) != _country_code(
        leg.destination.country_code
    )
    if requested is MapProvider.AUTO and crosses_border:
        alternative = (
            MapProvider.GOOGLE if primary is MapProvider.YANDEX else MapProvider.YANDEX
        )
        links.append(
            MapLink(
                alternative,
                f"{alternative.value.title()} Maps — cross-border alternative",
                _route_url(alternative, leg),
            )
        )
    return tuple(links)

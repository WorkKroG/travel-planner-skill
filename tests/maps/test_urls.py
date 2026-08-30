from urllib.parse import parse_qs, urlparse

import pytest
from travel_planner.maps import (
    MapPlace,
    MapProvider,
    RouteLeg,
    build_place_url,
    build_route_urls,
    load_map_policy,
)

KAZAN_KREMLIN = MapPlace(
    label="Казанский кремль & музей",
    country_code="RU",
    latitude=55.798994,
    longitude=49.105746,
)
LEG_KZ_TR = RouteLeg(
    origin=MapPlace("Алматы", "KZ", 43.238949, 76.889709),
    destination=MapPlace("Стамбул", "TR", 41.008238, 28.978359),
)


@pytest.mark.parametrize("provider", [MapProvider.YANDEX, MapProvider.GOOGLE])
def test_place_url_is_https_and_encodes_label_and_coordinates(provider) -> None:
    """Catch unsafe schemes, raw user text, and coordinate-only links with no readable name."""
    url = build_place_url(provider, KAZAN_KREMLIN)
    parsed = urlparse(url)
    decoded_query = str(parse_qs(parsed.query))

    assert parsed.scheme == "https"
    assert " " not in url
    assert "& музей" not in url
    assert "Казанский кремль & музей" in decoded_query
    assert "55.798994" in decoded_query
    assert "49.105746" in decoded_query


def test_cross_border_leg_returns_labelled_alternative() -> None:
    links = build_route_urls(LEG_KZ_TR, "auto", load_map_policy())

    assert {link.provider for link in links} == {MapProvider.YANDEX, MapProvider.GOOGLE}
    assert links[0].label.endswith("primary")
    assert links[1].label.endswith("cross-border alternative")
    assert all(link.requires_internet for link in links)
    assert all(urlparse(link.url).scheme == "https" for link in links)


def test_explicit_provider_does_not_add_unrequested_alternative() -> None:
    links = build_route_urls(LEG_KZ_TR, "google", load_map_policy())

    assert len(links) == 1
    assert links[0].provider is MapProvider.GOOGLE


def test_place_url_rejects_auto_provider() -> None:
    with pytest.raises(ValueError, match="concrete"):
        build_place_url(MapProvider.AUTO, KAZAN_KREMLIN)

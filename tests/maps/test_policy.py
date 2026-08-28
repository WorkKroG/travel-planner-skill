from pathlib import Path

import pytest
from travel_planner.maps import MapProvider, load_map_policy, select_provider
from travel_planner.resources import resource_path


@pytest.fixture
def policy():
    return load_map_policy()


def test_packaged_policy_is_versioned_and_uses_iso_country_codes() -> None:
    """Catch an unversioned or accidentally broadened regional routing policy."""
    policy = load_map_policy()

    assert policy.version == 1
    assert policy.yandex_preferred_country_codes == frozenset(
        {"AM", "AZ", "BY", "KZ", "KG", "MD", "RU", "TJ", "TM", "TR", "UZ"}
    )
    assert resource_path("map-policy", "map-provider-policy.yaml").is_file()


@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("RU", "yandex"),
        ("KZ", "yandex"),
        ("TR", "yandex"),
        ("JP", "google"),
        ("FR", "google"),
    ],
)
def test_auto_provider(country: str, expected: str, policy) -> None:
    assert select_provider(country, "auto", policy).value == expected


def test_explicit_google_override_wins_in_russia(policy) -> None:
    assert select_provider("RU", "google", policy) is MapProvider.GOOGLE


def test_policy_loader_rejects_unknown_provider(tmp_path: Path) -> None:
    broken = tmp_path / "map-provider-policy.yaml"
    broken.write_text(
        "policy_version: 1\nyandex_preferred_country_codes: [RU]\n"
        "default_provider: unknown\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="default_provider"):
        load_map_policy(broken)

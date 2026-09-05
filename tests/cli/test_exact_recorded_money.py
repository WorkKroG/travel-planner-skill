"""Check precision at the actual YAML, CLI, and atomic-write boundaries."""

import json
import subprocess
import sysconfig
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
from travel_planner.state import load_trip, validate_trip, write_state_file

CLI = str(Path(sysconfig.get_path("scripts")) / "travel-planner")
AT = "2026-09-05T12:00:00+00:00"


def _cli(*arguments: str) -> str:
    result = subprocess.run([CLI, *arguments], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@pytest.mark.parametrize("kind", ["exact", "range"])
def test_literal_yaml_money_stays_exact_through_cli_and_rewrite(tmp_path: Path, kind: str):
    root = tmp_path / "trip"
    _cli("init", str(root), "--title", "Precision", "--trip-id", "precision", "--confirm-path")
    path = root / "itinerary.yaml"
    amounts = (
        "  amount: 999999999999999999999999999.99\n"
        if kind == "exact"
        else "  amount_min: 999999999999999999999999999.99\n"
        "  amount_max: 1000000000000000000000000000.09\n"
    )
    rows = (
        f"budget_items:\n- id: large\n  amount_type: {kind}\n{amounts}"
        "  currency: USD\n  basis: per_group\n"
        "- id: cents\n  amount_type: exact\n  amount: 0.02\n"
        "  currency: USD\n  basis: per_group"
    )
    path.write_text(path.read_text().replace("budget_items: []", rows))
    expected = "1,000,000,000,000,000,000,000,000,000.01 USD"
    for rewrite in (False, True):
        if rewrite:
            with localcontext() as context:
                context.prec = 2
                state = load_trip(root)
                write_state_file(path, state.itinerary)
        before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
        assert json.loads(_cli("check", str(root)))["ok"]
        output = tmp_path / f"copy-{rewrite}.html"
        _cli("render", str(root), "--output", str(output), "--at", AT)
        html = output.read_text()
        assert expected in html
        if kind == "range":
            assert "1,000,000,000,000,000,000,000,000,000.11 USD" in html
        assert before == {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        ("0.12345678901234567890123456789", "0.12345678901234567890123456789"),
        ("1.234567890123456789e-20", "1.234567890123456789e-20"),
        ("1_000.000_000_000_000_000_000_001", "1000.000000000000000000001"),
        ("1:02.1234567890123456789", "62.1234567890123456789"),
    ],
)
def test_yaml_numeric_forms_preserve_digits_on_write(minimal_trip, literal, expected):
    path = minimal_trip / "itinerary.yaml"
    rows = (
        "budget_items:\n- id: precise\n  amount_type: exact\n"
        f"  amount: {literal}\n  currency: USD\n  basis: per_group"
    )
    path.write_text(path.read_text().replace("budget_items: []", rows))
    with localcontext() as context:
        context.prec = 2
        state = load_trip(minimal_trip)
        assert state.itinerary["budget_items"][0]["amount"] == Decimal(expected)
        write_state_file(path, state.itinerary)
        assert load_trip(minimal_trip).itinerary["budget_items"][0]["amount"] == Decimal(expected)
    assert validate_trip(minimal_trip).ok


def test_integral_yaml_decimal_keeps_integer_schema_compatibility(minimal_trip):
    path = minimal_trip / "itinerary.yaml"
    path.write_text(path.read_text().replace("schema_version: 1", "schema_version: 1.0"))
    assert validate_trip(minimal_trip).ok
    write_state_file(path, load_trip(minimal_trip).itinerary)
    assert validate_trip(minimal_trip).ok

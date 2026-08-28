import shutil
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from travel_planner.challenge.base import ChallengeContext
from travel_planner.challenge.budget import BudgetBasisRule, BudgetFxRule, MoneyAmount
from travel_planner.state import load_trip


def _context(tmp_path: Path, facts: dict) -> ChallengeContext:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return ChallengeContext(
        load_trip(target), "detailed", datetime(2026, 8, 28, 12, tzinfo=UTC), facts
    )


def test_money_amount_preserves_decimal_and_quality_metadata() -> None:
    """Catch budget normalization losing amount quality, basis, or tax uncertainty."""
    value = MoneyAmount(Decimal("123.45"), "JPY", "quote", "group", None)

    assert value.amount == Decimal("123.45")
    assert value.amount_type == "quote"
    assert value.taxes_included is None


def test_per_person_and_group_prices_are_not_summed_without_normalization(
    tmp_path: Path,
) -> None:
    """Catch a budget total that adds per-person and whole-group prices directly."""
    ctx = _context(
        tmp_path,
        {
            "budget_items": [
                {"id": "hotel", "amount": "600", "currency": "EUR", "basis": "group"},
                {"id": "rail", "amount": "120", "currency": "EUR", "basis": "person"},
            ]
        },
    )

    finding = BudgetBasisRule().evaluate(ctx)[0]

    assert finding.rule_id == "BUD-002"
    assert finding.severity == "blocking"


def test_mixed_currency_budget_requires_dated_fx_source(tmp_path: Path) -> None:
    """Catch currency conversion without a rate, source, and observation date."""
    ctx = _context(
        tmp_path,
        {
            "budget_items": [
                {"id": "hotel", "amount": "600", "currency": "EUR", "basis": "group"},
                {"id": "food", "amount": "30000", "currency": "JPY", "basis": "group"},
            ],
            "budget_currency": "EUR",
        },
    )

    assert BudgetFxRule().evaluate(ctx)[0].rule_id == "BUD-001"


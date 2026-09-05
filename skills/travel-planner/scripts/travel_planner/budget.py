"""Recorded expenses only: no currency conversion or trip completeness verdict."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import MAX_EMAX, MIN_EMIN, Decimal, InvalidOperation, localcontext
from typing import Any, Literal


@dataclass(frozen=True)
class BudgetSubtotal:
    currency: str
    basis: Literal["per_person", "per_group"]
    minimum: Decimal
    maximum: Decimal
    item_count: int


@dataclass(frozen=True)
class BudgetExclusion:
    index: int
    reason: str


@dataclass(frozen=True)
class BudgetCalculation:
    subtotals: tuple[BudgetSubtotal, ...]
    excluded: tuple[BudgetExclusion, ...]


def _amount(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise TypeError("must be a nonnegative finite number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("must be a nonnegative finite number") from None
    if not number.is_finite() or number < 0:
        raise ValueError("must be a nonnegative finite number")
    return number


def budget_item_errors(item: Mapping[str, Any]) -> tuple[str, ...]:
    """Diagnose invalid present values; missing amounts are permissible in drafts."""
    errors = []
    amounts = {}
    for field in ("amount", "amount_min", "amount_max"):
        if item.get(field) is not None:
            try:
                amounts[field] = _amount(item[field])
            except (TypeError, ValueError) as error:
                errors.append(f"{field}: {error}")
    if (
        "amount_min" in amounts
        and "amount_max" in amounts
        and amounts["amount_min"] > amounts["amount_max"]
    ):
        errors.append("amount_max: must be greater than or equal to amount_min")
    currency = item.get("currency")
    if currency is not None and (
        not isinstance(currency, str) or not re.fullmatch("[A-Z]{3}", currency)
    ):
        errors.append("currency: must be a three-letter uppercase currency code")
    if item.get("basis") is not None and item["basis"] not in ("per_person", "per_group"):
        errors.append("basis: must be per_person or per_group")
    if item.get("amount_type") is not None and item["amount_type"] not in (
        "exact",
        "estimate",
        "range",
        "unknown",
    ):
        errors.append("amount_type: must be exact, estimate, range or unknown")
    return tuple(errors)


def calculate_budget(items: Sequence[Mapping[str, Any]]) -> BudgetCalculation:
    """Sum compatible recorded rows and explain every excluded row by input index."""
    totals = {}
    excluded = []
    for index, item in enumerate(items):
        errors = budget_item_errors(item)
        amount_type = item.get("amount_type")
        fields = ("amount_min", "amount_max") if amount_type == "range" else ("amount", "amount")
        missing = [
            field
            for field in dict.fromkeys((*fields, "currency", "basis"))
            if item.get(field) is None
        ]
        if errors:
            reason = "; ".join(errors)
        elif amount_type in (None, "unknown"):
            reason = "Amount is unknown"
        elif missing:
            reason = "Missing " + ", ".join(missing)
        else:
            key = (item["currency"], item["basis"])
            lower, upper, count = totals.get(key, (Decimal(0), Decimal(0), 0))
            totals[key] = (
                _add(lower, _amount(item[fields[0]])),
                _add(upper, _amount(item[fields[1]])),
                count + 1,
            )
            continue
        excluded.append(BudgetExclusion(index, reason))
    return BudgetCalculation(
        tuple(BudgetSubtotal(*key, *values) for key, values in sorted(totals.items())),
        tuple(excluded),
    )


def _add(left: Decimal, right: Decimal) -> Decimal:
    # Use enough digits for every recorded cent and a possible carry. Do not
    # let a caller's ambient Decimal context silently round a subtotal.
    exponent = min(left.as_tuple().exponent, right.as_tuple().exponent)
    with localcontext() as context:
        context.prec = max(left.adjusted(), right.adjusted()) - exponent + 2
        context.Emax = MAX_EMAX
        context.Emin = MIN_EMIN
        return left + right


def format_money(value: Decimal | None, currency: str) -> str:
    """Preserve meaningful decimal places in every document adapter."""
    if value is None:
        return "Unknown"
    number = format(value, ",f")
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    return f"{number} {currency}"

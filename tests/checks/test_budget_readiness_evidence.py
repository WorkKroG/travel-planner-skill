"""Numeric validity and explicit references, without a trip-verdict engine."""

from copy import deepcopy
from decimal import Decimal, localcontext

import pytest
from travel_planner.budget import calculate_budget
from travel_planner.checks import run_checks


@pytest.fixture
def state(japan_state):
    state = deepcopy(japan_state)
    state.itinerary.update(
        days=[],
        selected_route_id=None,
        budget_items=[],
        budget_summary=None,
        challenge_findings=[],
        accepted_blockers=[],
    )
    state.readiness["items"] = []
    state.candidates["items"] = []
    state.candidates["claims"] = []
    return state


@pytest.mark.parametrize(
    "item",
    [
        {"amount_type": "exact", "amount": float("nan")},
        {"amount_type": "range", "amount_min": 20, "amount_max": 10},
        {"amount_type": "unknown", "amount": -1},
    ],
)
def test_invalid_present_money_is_reported_even_when_not_summable(state, item):
    state.itinerary["budget_items"] = [{"id": "cost-one", **item}]
    report = run_checks(state)
    assert [finding.code for finding in report.findings] == ["BUDGET_ITEM_INVALID"]
    assert report.findings[0].path == "itinerary.yaml.budget_items[0]"


@pytest.mark.parametrize("rate", [float("nan"), float("inf"), 0, -1, True])
def test_recorded_fx_rates_are_validated_but_never_used_to_convert_expenses(state, rate):
    state.itinerary["budget_summary"] = {
        "currency": "USD",
        "basis": "per_group",
        "amount": 100,
        "fx": {
            "base_currency": "USD",
            "source_id": state.candidates["sources"][0]["id"],
            "observed_at": "2026-08-30T09:00:00+00:00",
            "rates": {"EUR": rate},
        },
    }
    report = run_checks(state)
    assert "BUDGET_FX_INVALID" in [finding.code for finding in report.findings]


def test_expense_sum_preserves_large_values_under_a_low_decimal_context():
    items = [
        {
            "id": "large",
            "amount_type": "exact",
            "amount": Decimal("999999999999999999999999999.99"),
            "currency": "USD",
            "basis": "per_group",
        },
        {
            "id": "cent",
            "amount_type": "exact",
            "amount": Decimal("0.02"),
            "currency": "USD",
            "basis": "per_group",
        },
    ]
    before = deepcopy(items)
    with localcontext() as context:
        context.prec = 2
        total = calculate_budget(items)
    assert total.subtotals[0].minimum == Decimal("1000000000000000000000000000.01")
    assert items == before


def test_duplicate_source_order_does_not_hide_an_ambiguous_reference(state):
    source = {
        "id": "source-entry",
        "url": "https://official.example/entry",
        "source_type": "official",
        "publisher": "Border agency",
        "retrieved_at": "2026-08-20T12:00:00+00:00",
    }
    editorial = {**source, "url": "https://example.com/entry", "source_type": "editorial"}
    state.candidates["claims"] = [
        {
            "id": "claim-entry",
            "topic": "entry",
            "status": "verified",
            "source_ids": ["source-entry"],
        }
    ]
    for sources in ([source, editorial], [editorial, source]):
        state.candidates["sources"] = sources
        report = run_checks(state)
        assert {finding.code for finding in report.findings} == {
            "ID_DUPLICATE",
            "LINK_SOURCE_NOT_FOUND",
        }


def test_candidate_local_claim_link_keeps_its_canonical_path(state):
    state.candidates["items"] = [
        {
            "id": "candidate-clinic",
            "claims": [
                {
                    "id": "claim-health",
                    "topic": "health",
                    "status": "verified",
                    "source_ids": ["missing-health"],
                }
            ],
        }
    ]
    report = run_checks(state)
    finding = next(
        finding for finding in report.findings if finding.code == "LINK_SOURCE_NOT_FOUND"
    )
    assert finding.path == "candidates.yaml.items[0].claims[0].source_ids[0]"


def test_claim_status_and_dependency_cycles_are_not_turned_into_computed_trip_verdicts(state):
    state.readiness["items"] = [
        {
            "id": "ready-a",
            "category": "transport",
            "status": "action_needed",
            "dependencies": ["ready-b"],
        },
        {"id": "ready-b", "category": "lodging", "status": "unknown", "dependencies": ["ready-a"]},
    ]
    state.candidates["claims"] = [
        {"id": "claim-entry", "topic": "entry", "status": "verified", "source_ids": []}
    ]
    before = deepcopy(state)
    assert run_checks(state).ok
    assert state == before

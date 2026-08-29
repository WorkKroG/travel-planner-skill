"""Executable scenario inventory contract for the offline eval suite."""

from __future__ import annotations

from pathlib import Path

from evals.scenarios import adversarial_case_ids, load_scenario_case, scenario_ids

ROOT = Path(__file__).parents[2] / "evals" / "scenarios"
REQUIRED_SCENARIOS = {"japan-autumn", "european-road-trip", "weekend-city-break"}
REQUIRED_CASE_FILES = {
    "brief.yaml",
    "sources.yaml",
    "operations.yaml",
    "traps.yaml",
    "expected-hard.yaml",
    "rubric.yaml",
    "README.md",
}
EXPECTED_ADVERSARIAL_IDS = {
    "dual-nationality-transit",
    "multigenerational-accessibility",
    "medication-legality",
    "unreleased-schedule",
    "dst-overnight",
    "last-admission",
    "luggage-storage",
    "booking-timezone",
    "source-conflict",
    "prompt-injection",
    "budget-basis",
    "local-weather-swap",
    "frozen-mutation",
    "no-network",
    "missing-pdf-adapter",
    "winter-road-closure",
    "group-reversal",
    "weekend-simplicity",
    "place-collision",
    "sensitive-data-refusal",
}


def test_required_scenarios_and_exact_adversarial_cases_are_executable() -> None:
    """A missing or renamed fixture must not quietly shrink the release matrix."""
    assert scenario_ids(ROOT) >= REQUIRED_SCENARIOS
    assert adversarial_case_ids(ROOT) == EXPECTED_ADVERSARIAL_IDS

    for case_id in REQUIRED_SCENARIOS | EXPECTED_ADVERSARIAL_IDS:
        case = load_scenario_case(case_id, ROOT)
        assert case.path.is_dir()
        assert {path.name for path in case.path.iterdir()} >= REQUIRED_CASE_FILES
        assert case.scenario["fixture_response"]["operations"] == case.operations
        assert case.scenario["rubric_path"] == case.rubric_path


def test_loader_reads_fixture_operations_instead_of_only_documenting_them() -> None:
    """Changing a fixture operation must change the harness scenario given to the adapter."""
    case = load_scenario_case("japan-autumn", ROOT)

    assert case.brief["trip_id"] == "japan-autumn-2026-eval"
    assert case.sources["mode"] == "offline-frozen"
    assert case.traps["injected"][0]["id"] == "weather-risk"
    assert case.scenario["hard_checks"][0]["path"] == "checks.CAL-001.status"

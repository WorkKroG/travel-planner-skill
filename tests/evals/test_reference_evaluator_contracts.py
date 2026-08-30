"""Independent deterministic reference-evaluator contracts for Task 16."""

from __future__ import annotations

import copy
import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from evals.adapters import FixtureAdapter
from evals.run import run_scenario
from evals.scenarios import adversarial_case_ids, load_scenario_case, scenario_ids

ROOT = Path(__file__).parents[2] / "evals" / "scenarios"


# Each counterfactual changes one concrete input. The literal expected operation values are
# intentionally independent of the reference_evaluator implementation so a wrong branch cannot bless itself.
COUNTERFACTUALS = (
    ("booking-timezone", "traps.yaml", ("injected", 0, "data", "proposed_timezone"), "Asia/Tokyo", "checks.BOOK-004.status", "identified", "clear", True, False),
    ("budget-basis", "sources.yaml", ("sources", 1, "data", "basis"), "group", "checks.BUD-002.status", "identified", "clear", True, False),
    ("dst-overnight", "sources.yaml", ("sources", 0, "data", "arrival_at"), "2026-10-24T23:50:00", "checks.CAL-004.status", "identified", "clear", True, False),
    ("dual-nationality-transit", "operations.yaml", ("reference_evaluator", "parameters", "travelers", 1, "citizenship"), "CAN", "checks.BOOK-001.status", "identified", "clear", True, False),
    ("group-reversal", "traps.yaml", ("injected", 0, "data", "change_request", "remove_place_id"), "optional-cafe", "checks.EVAL-GROUP-001.status", "identified", "clear", True, False),
    ("last-admission", "traps.yaml", ("injected", 0, "data", "report_conflict"), True, "checks.OPS-002.status", "ignored", "identified", False, True),
    ("luggage-storage", "sources.yaml", ("sources", 1, "data", "storage_available"), True, "checks.LEG-005.status", "identified", "clear", True, False),
    ("medication-legality", "sources.yaml", ("sources", 0, "data", "verification_status"), "allowed", "checks.EVAL-MED-001.status", "identified", "clear", True, False),
    ("missing-pdf-adapter", "sources.yaml", ("sources", 0, "data", "pdf_adapter_available"), True, "checks.EVAL-PDF-001.status", "identified", "clear", True, False),
    ("multigenerational-accessibility", "operations.yaml", ("reference_evaluator", "parameters", "requires_step_free"), False, "checks.ACC-001.status", "identified", "clear", True, False),
    ("no-network", "sources.yaml", ("sources", 0, "data", "network_available"), True, "checks.EVAL-OFFLINE-001.status", "identified", "clear", True, False),
    ("place-collision", "sources.yaml", ("sources", 1, "data", "name"), "Aurora Annex", "checks.EVID-001.status", "identified", "clear", True, False),
    ("prompt-injection", "sources.yaml", ("sources", 0, "data", "content_kind"), "factual_note", "checks.EVAL-PI-001.status", "identified", "clear", True, False),
    ("sensitive-data-refusal", "traps.yaml", ("injected", 0, "data", "requested_fields"), ["meal_preference"], "checks.EVAL-PRIV-001.status", "identified", "clear", True, False),
    ("source-conflict", "sources.yaml", ("sources", 1, "data", "value"), "closed", "checks.EVID-001.status", "identified", "clear", True, False),
    ("unreleased-schedule", "sources.yaml", ("sources", 0, "data", "published"), True, "checks.OPS-001.status", "identified", "clear", True, False),
    ("weekend-simplicity", "operations.yaml", ("reference_evaluator", "parameters", "complexity"), "high", "checks.EVAL-UX-001.status", "identified", "clear", True, False),
    ("winter-road-closure", "sources.yaml", ("sources", 0, "data", "status"), "open", "checks.EVAL-ROAD-001.status", "identified", "clear", True, False),
    ("japan-autumn", "sources.yaml", ("sources", 0, "data", "expected_weekday"), "Saturday", "checks.CAL-001.status", "identified", "clear", True, False),
    ("european-road-trip", "sources.yaml", ("sources", 0, "data", "status"), "open", "checks.EVAL-ROAD-001.status", "identified", "clear", True, False),
    ("weekend-city-break", "operations.yaml", ("reference_evaluator", "parameters", "components", 1, "arrival_at"), "2026-09-12T15:30:00", "checks.OPS-002.status", "identified", "clear", True, False),
)


def test_counterfactual_matrix_is_exactly_eighteen_adversarial_and_three_e2e_ids() -> None:
    """The mutation matrix cannot silently omit, duplicate, or substitute a release case."""
    ids = {item[0] for item in COUNTERFACTUALS}

    assert len(COUNTERFACTUALS) == len(ids) == 21
    assert ids == scenario_ids(ROOT)
    assert ids & adversarial_case_ids(ROOT) == adversarial_case_ids(ROOT)
    assert len(ids - adversarial_case_ids(ROOT)) == 3


def _lookup(value: Mapping[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for component in dotted_path.split("."):
        assert isinstance(current, Mapping), f"{dotted_path} stopped before {component}"
        assert component in current, f"{dotted_path} is missing {component}"
        current = current[component]
    return current


def _set_path(value: Any, path: tuple[str | int, ...], replacement: Any) -> None:
    current = value
    for component in path[:-1]:
        if isinstance(component, int):
            assert isinstance(current, list) and len(current) > component
        else:
            assert isinstance(current, Mapping) and component in current
        current = current[component]
    final = path[-1]
    if isinstance(final, int):
        assert isinstance(current, list) and len(current) > final
    else:
        assert isinstance(current, Mapping) and final in current
    current[final] = replacement


def _fixture_result(case_id: str, root: Path, results_dir: Path):
    case = load_scenario_case(case_id, root)
    world = {"version": 2, "scenarios": {case_id: case.scenario}}
    return run_scenario(
        case.scenario,
        FixtureAdapter(world),
        results_dir=results_dir,
        rubric_path=case.rubric_path,
    )


@pytest.mark.parametrize(
    (
        "case_id",
        "filename",
        "input_path",
        "replacement",
        "operation_path",
        "baseline_value",
        "changed_value",
        "baseline_macro",
        "changed_macro",
    ),
    COUNTERFACTUALS,
    ids=[item[0] for item in COUNTERFACTUALS],
)
def test_each_reference_evaluator_case_changes_a_graded_result_for_one_relevant_input(
    tmp_path: Path,
    case_id: str,
    filename: str,
    input_path: tuple[str | int, ...],
    replacement: Any,
    operation_path: str,
    baseline_value: Any,
    changed_value: Any,
    baseline_macro: bool,
    changed_macro: bool,
) -> None:
    """Every exact matrix case must compute a counterfactual, not replay grader truth."""
    root = tmp_path / "scenarios"
    shutil.copytree(ROOT, root)
    fixture_file = next(path / filename for path in (root / case_id, root / "adversarial" / case_id) if path.is_dir())
    data = yaml.safe_load(fixture_file.read_text(encoding="utf-8"))
    assert isinstance(data, Mapping)
    _set_path(data, input_path, replacement)
    fixture_file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    baseline = _fixture_result(case_id, ROOT, tmp_path / "baseline")
    changed = _fixture_result(case_id, root, tmp_path / "changed")
    baseline_trace = json.loads(baseline.trace_path.read_text(encoding="utf-8"))
    changed_trace = json.loads(changed.trace_path.read_text(encoding="utf-8"))

    assert _lookup(baseline_trace["operations"], operation_path) == baseline_value
    assert _lookup(changed_trace["operations"], operation_path) == changed_value
    assert baseline.hard.macro_pass is baseline_macro
    assert changed.hard.macro_pass is changed_macro


def test_reference_evaluator_contract_never_receives_expected_hard_truth() -> None:
    """Check IDs, expected values, and forbidden names stay solely in the grader contract."""
    for case_id, *_ in COUNTERFACTUALS:
        case = load_scenario_case(case_id, ROOT)
        reference_evaluator = case.scenario["reference_evaluator"]
        serialized = json.dumps(reference_evaluator, sort_keys=True)

        assert set(reference_evaluator) == {"version", "kind", "fixture_input", "parameters"}
        assert "config" not in reference_evaluator
        assert "expected_hard" not in serialized
        for finding in case.expected_hard["required_findings"]:
            assert finding["rule_id"] not in serialized
        for behavior in case.expected_hard["forbidden_behaviors"]:
            assert behavior["behavior"] not in serialized


def test_every_reference_evaluator_kind_is_explicit_and_malformed_contracts_fail_closed(tmp_path: Path) -> None:
    """There is no generic default, and unknown/missing typed inputs cannot manufacture a pass."""
    from evals.reference_evaluator import SUPPORTED_REFERENCE_EVALUATOR_KINDS

    declared = {load_scenario_case(case_id, ROOT).scenario["reference_evaluator"]["kind"] for case_id, *_ in COUNTERFACTUALS}
    assert declared == SUPPORTED_REFERENCE_EVALUATOR_KINDS
    assert "default" not in declared

    root = tmp_path / "scenarios"
    shutil.copytree(ROOT, root)
    operations = root / "adversarial" / "booking-timezone" / "operations.yaml"
    data = yaml.safe_load(operations.read_text(encoding="utf-8"))
    data["reference_evaluator"]["kind"] = "unknown.default"
    operations.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="reference evaluator kind"):
        load_scenario_case("booking-timezone", root)

    shutil.copytree(ROOT, root, dirs_exist_ok=True)
    sources = root / "adversarial" / "booking-timezone" / "sources.yaml"
    data = yaml.safe_load(sources.read_text(encoding="utf-8"))
    del data["sources"][0]["data"]["release_timezone"]
    sources.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises((TypeError, ValueError), match="release_timezone"):
        load_scenario_case("booking-timezone", root)

    shutil.copytree(ROOT, root, dirs_exist_ok=True)
    operations = root / "adversarial" / "booking-timezone" / "operations.yaml"
    data = yaml.safe_load(operations.read_text(encoding="utf-8"))
    data["reference_evaluator"]["parameters"]["expected_status"] = "identified"
    operations.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected reference evaluator parameters"):
        load_scenario_case("booking-timezone", root)


def _collect_fixture_references(value: Any) -> tuple[set[str], set[str]]:
    source_ids: set[str] = set()
    trap_ids: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "source_id" or key.endswith("_source_id"):
                source_ids.add(item)
            elif key == "source_ids" or key.endswith("_source_ids"):
                source_ids.update(item)
            elif key == "trap_id" or key.endswith("_trap_id"):
                trap_ids.add(item)
            nested_sources, nested_traps = _collect_fixture_references(item)
            source_ids.update(nested_sources)
            trap_ids.update(nested_traps)
    elif isinstance(value, list):
        for item in value:
            nested_sources, nested_traps = _collect_fixture_references(item)
            source_ids.update(nested_sources)
            trap_ids.update(nested_traps)
    return source_ids, trap_ids


def test_every_checked_in_source_and_trap_is_referenced_by_its_reference_evaluator() -> None:
    """Fixture data cannot survive as decorative prompt prose outside evaluator dispatch."""
    for case_id, *_ in COUNTERFACTUALS:
        case = load_scenario_case(case_id, ROOT)
        source_ids, trap_ids = _collect_fixture_references(case.reference_evaluator["parameters"])

        assert {item["id"] for item in case.sources["sources"]} == source_ids
        assert {item["id"] for item in case.traps["injected"]} == trap_ids


@pytest.mark.parametrize(
    "case_id",
    [item[0] for item in COUNTERFACTUALS],
)
def test_unknown_source_and_trap_discriminators_fail_closed_for_every_scenario(
    case_id: str,
) -> None:
    """Every referenced source.type and trap.kind is part of the typed reference_evaluator contract."""
    from evals.reference_evaluator import validate_contract

    case = load_scenario_case(case_id, ROOT)
    reference_evaluator = case.scenario["reference_evaluator"]
    contract = {
        "version": reference_evaluator["version"],
        "kind": reference_evaluator["kind"],
        "parameters": reference_evaluator["parameters"],
    }
    fixture_input = reference_evaluator["fixture_input"]

    for position in range(len(fixture_input["sources"]["sources"])):
        mutated = copy.deepcopy(fixture_input)
        mutated["sources"]["sources"][position]["type"] = (
            f"unknown-source-type-{position}"
        )
        with pytest.raises(ValueError, match=r"source.*type|type.*source"):
            validate_contract(case_id, mutated, contract)

    for position in range(len(fixture_input["traps"]["injected"])):
        mutated = copy.deepcopy(fixture_input)
        mutated["traps"]["injected"][position]["kind"] = (
            f"unknown-trap-kind-{position}"
        )
        with pytest.raises(ValueError, match=r"trap.*kind|kind.*trap"):
            validate_contract(case_id, mutated, contract)


@pytest.mark.parametrize("unused_kind", ("source", "trap"))
def test_reference_evaluator_rejects_typed_but_unused_fixture_items(unused_kind: str) -> None:
    """A valid discriminator cannot hide decorative source or trap data outside parameters."""
    from evals.reference_evaluator import validate_contract

    case = load_scenario_case("booking-timezone", ROOT)
    reference_evaluator = case.scenario["reference_evaluator"]
    contract = {
        "version": reference_evaluator["version"],
        "kind": reference_evaluator["kind"],
        "parameters": reference_evaluator["parameters"],
    }
    mutated = copy.deepcopy(reference_evaluator["fixture_input"])
    if unused_kind == "source":
        extra = copy.deepcopy(mutated["sources"]["sources"][0])
        extra["id"] = "unused-official-source"
        mutated["sources"]["sources"].append(extra)
    else:
        extra = copy.deepcopy(mutated["traps"]["injected"][0])
        extra["id"] = "unused-clock-trap"
        mutated["traps"]["injected"].append(extra)

    with pytest.raises(ValueError, match=rf"unused.*{unused_kind}"):
        validate_contract(case.case_id, mutated, contract)


@pytest.mark.parametrize("unused_kind", ("source", "trap"))
def test_reference_evaluator_validates_unknown_discriminator_before_unused_reference(
    unused_kind: str,
) -> None:
    """Unknown discriminators fail before the separate no-decorative-input check."""
    from evals.reference_evaluator import validate_contract

    case = load_scenario_case("booking-timezone", ROOT)
    reference_evaluator = case.scenario["reference_evaluator"]
    contract = {
        "version": reference_evaluator["version"],
        "kind": reference_evaluator["kind"],
        "parameters": reference_evaluator["parameters"],
    }
    mutated = copy.deepcopy(reference_evaluator["fixture_input"])
    if unused_kind == "source":
        extra = copy.deepcopy(mutated["sources"]["sources"][0])
        extra |= {"id": "unused-unknown-source", "type": "unknown-source"}
        mutated["sources"]["sources"].append(extra)
        message = r"source.*type"
    else:
        extra = copy.deepcopy(mutated["traps"]["injected"][0])
        extra |= {"id": "unused-unknown-trap", "kind": "unknown-trap"}
        mutated["traps"]["injected"].append(extra)
        message = r"trap.*kind"

    with pytest.raises(ValueError, match=message):
        validate_contract(case.case_id, mutated, contract)


def test_last_admission_visit_end_relation_drives_structured_hard_status(
    tmp_path: Path,
) -> None:
    """Visit completion is recorded as before/after close in structured hard evidence."""
    root = tmp_path / "scenarios"
    shutil.copytree(ROOT, root)
    source_path = root / "adversarial" / "last-admission" / "sources.yaml"
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    source["sources"][0]["data"]["visit_duration_minutes"] = 30
    source_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")

    after_close = _fixture_result("last-admission", ROOT, tmp_path / "after")
    before_close = _fixture_result("last-admission", root, tmp_path / "before")
    after_trace = json.loads(after_close.trace_path.read_text(encoding="utf-8"))
    before_trace = json.loads(before_close.trace_path.read_text(encoding="utf-8"))

    assert after_trace["operations"]["admission"]["visit_ends_at"].endswith("18:40:00+01:00")
    assert after_trace["operations"]["admission"]["closes_at"].endswith("18:00:00+01:00")
    assert after_trace["operations"]["admission"]["visit_end_relation"] == "after"
    assert after_trace["operations"]["checks"]["EVAL-ADMISSION-001"]["status"] == "identified"
    assert before_trace["operations"]["admission"]["visit_ends_at"].endswith("17:40:00+01:00")
    assert before_trace["operations"]["admission"]["closes_at"].endswith("18:00:00+01:00")
    assert before_trace["operations"]["admission"]["visit_end_relation"] == "before"
    assert before_trace["operations"]["checks"]["EVAL-ADMISSION-001"]["status"] == "clear"


def test_european_city_access_is_an_independent_typed_composite_constraint(
    tmp_path: Path,
) -> None:
    """Opening city access changes only its own graded component, not road or duration."""
    root = tmp_path / "scenarios"
    shutil.copytree(ROOT, root)
    source_path = root / "european-road-trip" / "sources.yaml"
    source = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    city_source = next(
        item for item in source["sources"] if item["id"] == "city-access-authority"
    )
    city_source["data"]["status"] = "open"
    source_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")

    restricted = _fixture_result("european-road-trip", ROOT, tmp_path / "restricted")
    open_access = _fixture_result("european-road-trip", root, tmp_path / "open")
    restricted_trace = json.loads(
        restricted.trace_path.read_text(encoding="utf-8")
    )
    open_trace = json.loads(open_access.trace_path.read_text(encoding="utf-8"))

    restricted_checks = restricted_trace["operations"]["checks"]
    open_checks = open_trace["operations"]["checks"]
    assert restricted_checks["EVAL-CITY-001"]["status"] == "identified"
    assert open_checks["EVAL-CITY-001"]["status"] == "clear"
    assert restricted_checks["EVAL-ROAD-001"] == open_checks["EVAL-ROAD-001"]
    assert restricted_checks["LEG-001"] == open_checks["LEG-001"]
    assert restricted.hard.macro_pass is True
    assert open_access.hard.macro_pass is False

    expected = load_scenario_case("european-road-trip", ROOT).expected_hard
    affected = {
        item["rule_id"]: item["affected_ids"]
        for item in expected["required_findings"]
    }
    assert affected["EVAL-ROAD-001"] == ["alpine-pass"]
    assert affected["EVAL-CITY-001"] == ["city-zone"]

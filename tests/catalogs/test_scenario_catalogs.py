"""Data-contract checks only; these tests do not execute or score model behavior."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
SKILL_CATALOG = ROOT / "evals" / "skill-scenarios.yaml"
RELEASE_CATALOG = ROOT / "evals" / "release-scenarios.yaml"
KNOWN_SURFACES = {"codex", "chat_web", "mobile", "cross_surface"}


def _load_catalog(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert set(value) == {"catalog", "scenarios"}
    assert isinstance(value["catalog"], dict)
    assert isinstance(value["scenarios"], list)
    return value


def _assert_nonempty_strings(values: list[Any]) -> None:
    assert values
    assert all(isinstance(value, str) and value.strip() for value in values)


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _all_keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _all_keys(item)}
    return set()


def test_targeted_skill_catalog_has_nine_review_inputs_not_agent_answers() -> None:
    catalog = _load_catalog(SKILL_CATALOG)

    assert catalog["catalog"] == {
        "kind": "targeted_skill_scenarios",
        "review_mode": "independent_model_review_required",
        "execution_status": "not_executed",
    }
    scenarios = catalog["scenarios"]
    assert len(scenarios) == 9
    assert len({scenario["id"] for scenario in scenarios}) == 9
    for scenario in scenarios:
        assert set(scenario) == {
            "id",
            "surfaces",
            "context",
            "user_prompt",
            "observable_invariants",
        }
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", scenario["id"])
        _assert_nonempty_strings(scenario["surfaces"])
        assert set(scenario["surfaces"]) <= KNOWN_SURFACES
        assert isinstance(scenario["context"], str) and scenario["context"].strip()
        assert isinstance(scenario["user_prompt"], str) and scenario["user_prompt"].strip()
        _assert_nonempty_strings(scenario["observable_invariants"])


def test_release_catalog_has_exactly_three_unexecuted_evidence_targets() -> None:
    catalog = _load_catalog(RELEASE_CATALOG)

    assert catalog["catalog"] == {
        "kind": "release_scenarios",
        "review_mode": "release_evidence_required",
        "execution_status": "not_executed",
    }
    scenarios = catalog["scenarios"]
    assert [scenario["id"] for scenario in scenarios] == [
        "codex-complex-trip",
        "user-confirmed-final",
        "cross-surface-portability",
    ]
    for scenario in scenarios:
        assert set(scenario) == {
            "id",
            "purpose",
            "preconditions",
            "steps",
            "required_evidence",
        }
        assert isinstance(scenario["purpose"], str) and scenario["purpose"].strip()
        _assert_nonempty_strings(scenario["preconditions"])
        _assert_nonempty_strings(scenario["steps"])
        _assert_nonempty_strings(scenario["required_evidence"])

    portability = scenarios[2]
    evidence = "\n".join(portability["required_evidence"]).lower()
    assert "chat web" in evidence
    assert "mobile" in evidence
    assert "one release scenario" in evidence


def test_catalogs_contain_no_legacy_runner_or_simulator_contract() -> None:
    catalogs = [_load_catalog(SKILL_CATALOG), _load_catalog(RELEASE_CATALOG)]
    forbidden_keys = {
        "agent_answer",
        "expected_response",
        "operations",
        "reference_evaluator",
        "rule_id",
        "rubric",
        "score",
        "grader",
        "trap",
        "fixture_input",
        "result",
    }
    forbidden_text = (
        r"evals/run\.py",
        r"--adapter",
        r"fixture[- ]world",
        r"reference[_ -]evaluator",
        r"soft review: not run",
        r"offline (?:mode|workflow|judge|review|simulator)",
        r"pdf (?:adapter|pipeline|output)",
        r"travel-planner (?:validate|challenge|finalize|qa|pdf)\b",
        r"device farm",
    )

    for catalog in catalogs:
        assert not (_all_keys(catalog) & forbidden_keys)
        serialized = yaml.safe_dump(catalog, sort_keys=True).lower()
        assert [pattern for pattern in forbidden_text if re.search(pattern, serialized)] == []

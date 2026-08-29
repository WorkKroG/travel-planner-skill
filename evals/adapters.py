"""Offline fixture and explicit-command adapters for the executable eval harness."""

from __future__ import annotations

import copy
import json
import math
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from .redaction import redact_text
from .types import AgentRun, JudgeRun


class AgentAdapter(Protocol):
    name: str

    def run(self, prompt: str, workspace: Path) -> AgentRun: ...


class JudgeAdapter(Protocol):
    name: str

    def judge(self, prompt: str, response: str, workspace: Path) -> JudgeRun: ...


class AdapterError(RuntimeError):
    """Raised when an adapter cannot execute the requested scenario."""


_SCENARIO_ID = re.compile(r"^SCENARIO_ID:\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*$", re.MULTILINE)
RESULT_ENVELOPE_VERSION = 1
RUBRIC_DIMENSIONS = (
    "skeleton_distinctness",
    "tradeoffs",
    "pacing",
    "backup_usefulness",
    "readability",
    "calibrated_uncertainty",
)
_SENSITIVE_FLAGS = frozenset({"--token", "--api-key", "--password", "--secret"})
_HEADER_FLAGS = frozenset({"--header", "-H"})
_AUTHORIZATION_FLAG = "--authorization"
_SPLIT_AUTHORIZATION_SCHEMES = frozenset({"basic", "bearer"})
_NEGATION_PREFIXES = (
    "not ",
    "no ",
    "never ",
    "without ",
    "did not ",
    "do not ",
    "does not ",
    "is not ",
    "are not ",
    "was not ",
    "were not ",
)


def _anchor_is_asserted(normalized_response: str, anchor: str) -> bool:
    """Match a whole phrase only when the response asserts rather than negates it."""
    normalized_anchor = " ".join(anchor.casefold().split())
    if not normalized_anchor:
        return False
    anchor_is_explicitly_negative = normalized_anchor.startswith(_NEGATION_PREFIXES)
    pattern = re.compile(
        rf"(?<!\w){re.escape(normalized_anchor)}(?!\w)",
    )
    for match in pattern.finditer(normalized_response):
        prefix = normalized_response[max(0, match.start() - 32) : match.start()]
        if anchor_is_explicitly_negative or not prefix.endswith(_NEGATION_PREFIXES):
            return True
    return False


def _safe_command(command: Sequence[str]) -> list[str]:
    safe: list[str] = []
    redact_next = False
    header_value_next = False
    authorization_value_next = False
    authorization_scheme_next = False
    for item in command:
        if redact_next:
            safe.append("<redacted>")
            redact_next = False
        elif authorization_scheme_next:
            authorization_scheme_next = False
            if item.strip().lower() in _SPLIT_AUTHORIZATION_SCHEMES:
                safe.append(item)
                redact_next = True
            else:
                safe.append("<redacted>")
        else:
            safe.append(redact_text(item))
            if item in _SENSITIVE_FLAGS:
                redact_next = True
            elif item == _AUTHORIZATION_FLAG:
                authorization_scheme_next = True
            elif item in _HEADER_FLAGS:
                header_value_next = True
            elif header_value_next:
                header_value_next = False
                authorization_value_next = item.strip().lower().rstrip(":") == "authorization"
            elif authorization_value_next:
                authorization_value_next = False
                if item.strip().lower() in _SPLIT_AUTHORIZATION_SCHEMES:
                    redact_next = True
    return safe


def _non_standard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def _strict_json_loads(value: str) -> Any:
    return json.loads(value, parse_constant=_non_standard_constant, parse_float=_finite_float)


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return tuple(value)


def _agent_from_stdout(stdout: str, metadata: Mapping[str, Any]) -> AgentRun:
    try:
        envelope = _strict_json_loads(stdout)
        if not isinstance(envelope, Mapping):
            raise TypeError("result envelope must be a JSON object")
        if envelope.get("schema_version") != RESULT_ENVELOPE_VERSION:
            raise ValueError(f"unsupported result schema_version: {envelope.get('schema_version')!r}")
        response = envelope.get("response")
        operations = envelope.get("operations")
        if not isinstance(response, str) or not isinstance(operations, Mapping):
            raise TypeError("result envelope requires string response and object operations")
        return AgentRun(
            response=response,
            operations=copy.deepcopy(dict(operations)),
            metadata=dict(metadata) | {"result_schema_version": RESULT_ENVELOPE_VERSION},
            degraded=_string_list(envelope.get("degraded"), "degraded"),
            errors=_string_list(envelope.get("errors"), "errors"),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return AgentRun(
            response=stdout,
            operations={},
            metadata=dict(metadata),
            errors=(f"result envelope error: {redact_text(str(error))}",),
        )


def _judge_from_stdout(stdout: str, metadata: Mapping[str, Any]) -> JudgeRun:
    try:
        envelope = _strict_json_loads(stdout)
        if not isinstance(envelope, Mapping):
            raise TypeError("judge envelope must be a JSON object")
        if envelope.get("schema_version") != RESULT_ENVELOPE_VERSION:
            raise ValueError(f"unsupported judge schema_version: {envelope.get('schema_version')!r}")
        scores = envelope.get("scores")
        if not isinstance(scores, Mapping) or set(scores) != set(RUBRIC_DIMENSIONS):
            raise ValueError("judge scores must contain exactly the six rubric dimensions")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in scores.values()
        ):
            raise ValueError("judge scores must be finite numbers")
        return JudgeRun(
            scores=copy.deepcopy(dict(scores)),
            metadata=dict(metadata) | {"judge_schema_version": RESULT_ENVELOPE_VERSION},
            degraded=_string_list(envelope.get("degraded"), "degraded"),
            errors=_string_list(envelope.get("errors"), "errors"),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return JudgeRun({}, dict(metadata), errors=(f"judge envelope error: {redact_text(str(error))}",))


def normalize_judge_run(judge_run: JudgeRun) -> JudgeRun:
    """Make every judge adapter obey the same finite six-dimension score boundary."""
    errors = list(judge_run.errors)
    scores = judge_run.scores
    if not errors:
        if not isinstance(scores, Mapping) or set(scores) != set(RUBRIC_DIMENSIONS):
            errors.append("judge result error: scores must contain exactly the six rubric dimensions")
        elif any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in scores.values()
        ):
            errors.append("judge result error: scores must be finite numbers")
    return JudgeRun(
        scores=copy.deepcopy(dict(scores)) if not errors else {},
        metadata=copy.deepcopy(dict(judge_run.metadata)),
        degraded=tuple(judge_run.degraded),
        errors=tuple(errors),
    )


def _scenario_id_from_prompt(prompt: str) -> str:
    match = _SCENARIO_ID.search(prompt)
    if match is None:
        raise AdapterError("Fixture prompt is missing SCENARIO_ID.")
    return match.group(1)


class FixtureAdapter:
    """Deterministic adapter backed only by the passed fixture-world mapping."""

    name = "fixture"

    def __init__(self, world: Mapping[str, Any]) -> None:
        scenarios = world.get("scenarios")
        if not isinstance(scenarios, Mapping):
            raise TypeError("Fixture world requires a scenarios mapping.")
        self._world = world
        self._scenarios = scenarios

    def run(self, prompt: str, workspace: Path) -> AgentRun:
        del workspace
        scenario_id = _scenario_id_from_prompt(prompt)
        scenario = self._scenarios.get(scenario_id)
        if not isinstance(scenario, Mapping):
            raise AdapterError(f"Fixture scenario not found: {scenario_id}")
        oracle = scenario.get("fixture_oracle")
        if isinstance(oracle, Mapping):
            from .fixture_oracle import evaluate

            contract = {
                "version": oracle.get("version"),
                "kind": oracle.get("kind"),
                "parameters": oracle.get("parameters"),
            }
            return evaluate(scenario_id, oracle["fixture_input"], contract)
        response = scenario.get("fixture_response")
        if not isinstance(response, Mapping):
            raise AdapterError(f"Fixture scenario {scenario_id} has no fixture_response mapping.")
        response_text = response.get("text", "")
        operations = response.get("operations", {})
        if not isinstance(response_text, str) or not isinstance(operations, Mapping):
            raise AdapterError(f"Fixture scenario {scenario_id} has an invalid fixture_response.")
        return AgentRun(
            response=response_text,
            operations=copy.deepcopy(dict(operations)),
            metadata={
                "mode": "offline",
                "fixture_world_version": self._world.get("version", 1),
                "scenario_id": scenario_id,
            },
        )


class CodexCliAdapter:
    """Runs a user-supplied command and makes failures visible in its result."""

    name = "codex-cli"

    def __init__(self, command: Sequence[str], model: str | None = None) -> None:
        if not command:
            raise ValueError("CodexCliAdapter requires an explicit command.")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("CodexCliAdapter requires a non-empty model.")
        self._command = tuple(command)
        self._model = model

    def run(self, prompt: str, workspace: Path) -> AgentRun:
        metadata = {"command": _safe_command(self._command), "model": self._model}
        try:
            completed = subprocess.run(
                self._command,
                cwd=workspace,
                input=prompt,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as error:
            return AgentRun("", {}, metadata, errors=(f"command could not start: {redact_text(str(error))}",))
        if completed.returncode != 0:
            detail = redact_text(completed.stderr.strip() or completed.stdout.strip() or "no command output")
            return AgentRun(
                completed.stdout,
                {},
                metadata | {"returncode": completed.returncode},
                errors=(f"command failed ({completed.returncode}): {detail}",),
            )
        return _agent_from_stdout(completed.stdout, metadata | {"returncode": completed.returncode})


class FixtureJudge:
    """Deterministically apply per-scenario semantic anchors to the actual response."""

    name = "fixture-judge"

    def __init__(self, world: Mapping[str, Any]) -> None:
        scenarios = world.get("scenarios")
        if not isinstance(scenarios, Mapping):
            raise TypeError("Fixture world requires a scenarios mapping.")
        self._world = world
        self._scenarios = scenarios

    def judge(self, prompt: str, response: str, workspace: Path) -> JudgeRun:
        del workspace
        scenario_id = _scenario_id_from_prompt(prompt)
        scenario = self._scenarios.get(scenario_id)
        if not isinstance(scenario, Mapping):
            return JudgeRun({}, {"mode": "offline", "scenario_id": scenario_id}, errors=("fixture scenario missing",))
        if "fixture_oracle" not in scenario:
            judge = scenario.get("fixture_judge")
            scores = judge.get("scores") if isinstance(judge, Mapping) else None
            if not isinstance(scores, Mapping):
                return JudgeRun({}, {"mode": "offline", "scenario_id": scenario_id}, errors=("fixture judge scores missing",))
            return JudgeRun(copy.deepcopy(dict(scores)), {"mode": "offline", "fixture_world_version": self._world.get("version", 1), "scenario_id": scenario_id})
        rubric = scenario.get("fixture_rubric")
        dimensions = rubric.get("dimensions") if isinstance(rubric, Mapping) else None
        if not isinstance(dimensions, list):
            return JudgeRun(
                {},
                {"mode": "offline", "scenario_id": scenario_id},
                errors=("fixture rubric anchors missing",),
            )
        normalized = " ".join(response.casefold().split())
        scores: dict[str, int] = {}
        evidence: dict[str, Any] = {}
        for dimension in dimensions:
            if not isinstance(dimension, Mapping):
                return JudgeRun(
                    {},
                    {"mode": "offline", "scenario_id": scenario_id},
                    errors=("fixture rubric dimension is invalid",),
                )
            dimension_id = dimension.get("id")
            anchors = dimension.get("anchors")
            if not isinstance(dimension_id, str) or not isinstance(anchors, Mapping):
                return JudgeRun(
                    {},
                    {"mode": "offline", "scenario_id": scenario_id},
                    errors=("fixture rubric anchors are invalid",),
                )
            required = anchors.get("required")
            evidence_tokens = anchors.get("evidence")
            forbidden = anchors.get("forbidden")
            if not all(
                isinstance(values, list)
                and values
                and all(isinstance(value, str) and value for value in values)
                for values in (required, evidence_tokens, forbidden)
            ):
                return JudgeRun(
                    {},
                    {"mode": "offline", "scenario_id": scenario_id},
                    errors=("fixture rubric anchor lists are invalid",),
                )
            required_hits = [
                value for value in required if _anchor_is_asserted(normalized, value)
            ]
            evidence_hits = [
                value
                for value in evidence_tokens
                if _anchor_is_asserted(normalized, value)
            ]
            forbidden_hits = [
                value for value in forbidden if _anchor_is_asserted(normalized, value)
            ]
            score = round(2 * len(required_hits) / len(required))
            score += round(2 * len(evidence_hits) / len(evidence_tokens))
            if forbidden_hits:
                score = min(score, 1)
            scores[dimension_id] = score
            evidence[dimension_id] = {
                "required_hits": required_hits,
                "evidence_hits": evidence_hits,
                "forbidden_hits": forbidden_hits,
            }
        return JudgeRun(
            scores,
            {
                "mode": "offline",
                "fixture_world_version": self._world.get("version", 1),
                "scenario_id": scenario_id,
                "dimension_evidence": evidence,
            },
        )


class CodexCliJudge:
    """Explicit command-based semantic judge with a separate model and score envelope."""

    name = "codex-cli-judge"

    def __init__(self, command: Sequence[str], model: str | None = None) -> None:
        if not command:
            raise ValueError("CodexCliJudge requires an explicit command.")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("CodexCliJudge requires a non-empty model.")
        self._command = tuple(command)
        self._model = model

    def judge(self, prompt: str, response: str, workspace: Path) -> JudgeRun:
        metadata = {"command": _safe_command(self._command), "model": self._model}
        payload = json.dumps({"schema_version": 1, "prompt": prompt, "response": response}, allow_nan=False)
        try:
            completed = subprocess.run(
                self._command,
                cwd=workspace,
                input=payload,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError as error:
            return JudgeRun({}, metadata, errors=(f"judge command could not start: {redact_text(str(error))}",))
        if completed.returncode != 0:
            detail = redact_text(completed.stderr.strip() or completed.stdout.strip() or "no command output")
            return JudgeRun(
                {}, metadata | {"returncode": completed.returncode}, errors=(f"judge command failed ({completed.returncode}): {detail}",)
            )
        return _judge_from_stdout(completed.stdout, metadata | {"returncode": completed.returncode})

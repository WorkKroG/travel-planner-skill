"""Offline fixture and explicit-command adapters for the executable eval harness."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from .types import AgentRun


class AgentAdapter(Protocol):
    name: str

    def run(self, prompt: str, workspace: Path) -> AgentRun: ...


class AdapterError(RuntimeError):
    """Raised when an adapter cannot execute the requested scenario."""


_SCENARIO_ID = re.compile(r"^SCENARIO_ID:\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*$", re.MULTILINE)
_SENSITIVE = re.compile(r"(api[_-]?key|token|secret|password)", re.IGNORECASE)


def _safe_command(command: Sequence[str]) -> list[str]:
    safe: list[str] = []
    redact_next = False
    for item in command:
        if redact_next or _SENSITIVE.search(item):
            safe.append("<redacted>")
            redact_next = item.startswith("-")
        else:
            safe.append(item)
    return safe


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
        match = _SCENARIO_ID.search(prompt)
        if match is None:
            raise AdapterError("Fixture prompt is missing SCENARIO_ID.")
        scenario_id = match.group(1)
        scenario = self._scenarios.get(scenario_id)
        if not isinstance(scenario, Mapping):
            raise AdapterError(f"Fixture scenario not found: {scenario_id}")
        response = scenario.get("fixture_response")
        if not isinstance(response, Mapping):
            raise AdapterError(f"Fixture scenario {scenario_id} has no fixture_response mapping.")
        response_text = response.get("text", "")
        operations = response.get("operations", {})
        if not isinstance(response_text, str) or not isinstance(operations, Mapping):
            raise AdapterError(f"Fixture scenario {scenario_id} has an invalid fixture_response.")
        return AgentRun(
            response=response_text,
            operations=dict(operations),
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
            return AgentRun("", {}, metadata, errors=(f"command could not start: {error}",))
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "no command output"
            return AgentRun(
                completed.stdout,
                {},
                metadata | {"returncode": completed.returncode},
                errors=(f"command failed ({completed.returncode}): {detail}",),
            )
        return AgentRun(
            completed.stdout,
            {},
            metadata | {"returncode": completed.returncode},
            degraded=("operations were not structured by the command adapter",),
        )

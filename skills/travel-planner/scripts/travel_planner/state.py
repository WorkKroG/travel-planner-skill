"""Versioned state loading, validation, and atomic YAML writes."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .resources import resource_path

STATE_SCHEMA_FILES = {
    "brief.yaml": "brief.schema.json",
    "candidates.yaml": "candidates.schema.json",
    "itinerary.yaml": "itinerary.schema.json",
    "readiness.yaml": "readiness.schema.json",
}


@dataclass
class TripState:
    """Mutable in-memory representation of one trip's structured canonical files."""

    root: Path
    brief: dict[str, Any]
    candidates: dict[str, Any]
    itinerary: dict[str, Any]
    readiness: dict[str, Any]


@dataclass(frozen=True)
class ValidationIssue:
    file: str
    path: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"Expected a YAML mapping in {path}")
    return value


def load_trip(root: Path) -> TripState:
    """Load the four structured state files for one explicit trip root."""
    trip_root = Path(root).expanduser().resolve(strict=False)
    return TripState(
        root=trip_root,
        brief=_load_yaml(trip_root / "brief.yaml"),
        candidates=_load_yaml(trip_root / "candidates.yaml"),
        itinerary=_load_yaml(trip_root / "itinerary.yaml"),
        readiness=_load_yaml(trip_root / "readiness.yaml"),
    )


def _issue_path(file_name: str, parts: list[str | int]) -> str:
    result = file_name
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def _validate_structure(root: Path) -> tuple[list[ValidationIssue], dict[str, Any]]:
    trip_root = Path(root).expanduser().resolve(strict=False)
    issues: list[ValidationIssue] = []
    trip_ids: dict[str, Any] = {}
    for file_name, schema_name in STATE_SCHEMA_FILES.items():
        path = trip_root / file_name
        try:
            value = _load_yaml(path)
            schema = json.loads(resource_path("schemas", schema_name).read_text(encoding="utf-8"))
        except (OSError, TypeError, yaml.YAMLError, json.JSONDecodeError) as error:
            issues.append(ValidationIssue(file_name, file_name, str(error)))
            continue
        trip_ids[file_name] = value.get("trip_id")
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path)):
            issues.append(
                ValidationIssue(
                    file=file_name,
                    path=_issue_path(file_name, list(error.absolute_path)),
                    message=error.message,
                )
            )
    return issues, trip_ids


def validate_structure(root: Path) -> ValidationReport:
    """Validate each structured YAML file against its own schema only."""
    issues, _ = _validate_structure(root)
    return ValidationReport(tuple(issues))


def validate_trip(root: Path) -> ValidationReport:
    """Validate file structure, recorded formats, and shared trip identity."""
    issues, trip_ids = _validate_structure(root)
    expected_trip_id = trip_ids.get("brief.yaml")
    for file_name, value in trip_ids.items():
        if expected_trip_id is not None and value != expected_trip_id:
            issues.append(
                ValidationIssue(
                    file=file_name,
                    path=f"{file_name}.trip_id",
                    message=f"must match brief.yaml trip_id {expected_trip_id!r}",
                )
            )
    return ValidationReport(tuple(issues))


def write_state_file(path: Path, value: Mapping[str, Any]) -> None:
    """Atomically replace one YAML state file while preserving mapping order."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            yaml.safe_dump(dict(value), stream, allow_unicode=True, sort_keys=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

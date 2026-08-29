"""Browser QA report parsing and Final-status hard gates."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_SUPPORTED_PROFILES = frozenset({"phone", "tablet", "desktop", "narrow"})


@dataclass(frozen=True)
class QaReport:
    accessibility_critical: int = 0
    accessibility_serious: int = 0
    horizontal_overflow_count: int = 0
    first_useful_ms: float | None = None
    cumulative_layout_shift: float | None = None
    interaction_ms: float | None = None
    focus_visible: bool = False
    no_js_core: bool = False
    offline_core: bool = False
    zoom_200_core: bool = False
    reduced_motion_core: bool = False
    external_asset_requests: int = 0
    pdf_failures: int = 0
    undersized_touch_targets: int = 0
    filter_sync: bool = False
    mobile_priority_visible: bool = False
    state_matrix_complete: bool = False
    file_size_bytes: int | None = None
    peak_memory_bytes: int | None = None
    errors: tuple[str, ...] = ()

    @property
    def blocking_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.accessibility_critical:
            reasons.append("accessibility_critical")
        if self.accessibility_serious:
            reasons.append("accessibility_serious")
        if self.horizontal_overflow_count:
            reasons.append("horizontal_overflow")
        if self.first_useful_ms is None or self.first_useful_ms >= 2500:
            reasons.append("first_useful_screen")
        if self.cumulative_layout_shift is None or self.cumulative_layout_shift >= 0.1:
            reasons.append("layout_shift")
        if self.interaction_ms is None or self.interaction_ms >= 200:
            reasons.append("interaction_response")
        if not self.focus_visible:
            reasons.append("keyboard_focus")
        if not self.no_js_core:
            reasons.append("no_javascript_core")
        if not self.offline_core:
            reasons.append("offline_core")
        if not self.zoom_200_core:
            reasons.append("zoom_200_core")
        if not self.reduced_motion_core:
            reasons.append("reduced_motion")
        if self.external_asset_requests:
            reasons.append("external_assets")
        if self.pdf_failures:
            reasons.append("pdf_generation")
        if self.undersized_touch_targets:
            reasons.append("touch_targets")
        if not self.filter_sync:
            reasons.append("filter_sync")
        if not self.mobile_priority_visible:
            reasons.append("mobile_first_view")
        if not self.state_matrix_complete:
            reasons.append("visual_state_matrix")
        if self.errors:
            reasons.append("qa_errors")
        return tuple(reasons)

    @property
    def final_allowed(self) -> bool:
        return not self.blocking_reasons

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["errors"] = list(self.errors)
        result["final_allowed"] = self.final_allowed
        result["blocking_reasons"] = list(self.blocking_reasons)
        return result

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> QaReport:
        return cls(
            accessibility_critical=int(value.get("accessibility_critical", 0)),
            accessibility_serious=int(value.get("accessibility_serious", 0)),
            horizontal_overflow_count=int(value.get("horizontal_overflow_count", 0)),
            first_useful_ms=_optional_float(value.get("first_useful_ms")),
            cumulative_layout_shift=_optional_float(value.get("cumulative_layout_shift")),
            interaction_ms=_optional_float(value.get("interaction_ms")),
            focus_visible=bool(value.get("focus_visible", False)),
            no_js_core=bool(value.get("no_js_core", False)),
            offline_core=bool(value.get("offline_core", False)),
            zoom_200_core=bool(value.get("zoom_200_core", False)),
            reduced_motion_core=bool(value.get("reduced_motion_core", False)),
            external_asset_requests=int(value.get("external_asset_requests", 0)),
            pdf_failures=int(value.get("pdf_failures", 0)),
            undersized_touch_targets=int(value.get("undersized_touch_targets", 0)),
            filter_sync=bool(value.get("filter_sync", False)),
            mobile_priority_visible=bool(value.get("mobile_priority_visible", False)),
            state_matrix_complete=bool(value.get("state_matrix_complete", False)),
            file_size_bytes=_optional_int(value.get("file_size_bytes")),
            peak_memory_bytes=_optional_int(value.get("peak_memory_bytes")),
            errors=tuple(str(item) for item in value.get("errors", [])),
        )


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _default_runner() -> tuple[str, ...]:
    repository_root = Path(__file__).resolve().parents[5]
    return ("node", str(repository_root / "tests" / "ui" / "qa.mjs"))


def run_document_qa(
    html_path: Path,
    profiles: Sequence[str],
    *,
    command: Sequence[str] | None = None,
) -> QaReport:
    """Execute browser QA and convert its JSON boundary into enforceable gates."""
    source = Path(html_path).resolve(strict=False)
    if not source.is_file():
        return QaReport(errors=(f"HTML input does not exist: {source}",))
    selected_profiles = tuple(profiles)
    unknown = sorted(set(selected_profiles) - _SUPPORTED_PROFILES)
    if unknown:
        return QaReport(errors=(f"Unknown QA profiles: {', '.join(unknown)}",))
    invocation = [*(command or _default_runner()), str(source), "--profiles", ",".join(selected_profiles)]
    try:
        completed = subprocess.run(invocation, check=False, capture_output=True, text=True)
    except OSError as error:
        return QaReport(errors=(f"Browser QA command failed to start: {error}",))
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown runner error"
        return QaReport(errors=(f"Browser QA failed ({completed.returncode}): {detail}",))
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        return QaReport(errors=("Browser QA returned no JSON report.",))
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as error:
        return QaReport(errors=(f"Browser QA returned invalid JSON: {error}",))
    if not isinstance(payload, Mapping):
        return QaReport(errors=("Browser QA JSON report must be an object.",))
    return QaReport.from_mapping(payload)


@dataclass(frozen=True)
class QaAttestation:
    """A successful browser-QA receipt bound to one exact HTML artifact."""

    sha256: str
    byte_count: int
    report: QaReport

    def matches(self, html_path: Path) -> bool:
        """Return whether this receipt still approves the exact file on disk."""
        source = Path(html_path)
        if not source.is_file():
            return False
        content = source.read_bytes()
        return len(content) == self.byte_count and hashlib.sha256(content).hexdigest() == self.sha256

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
            "final_allowed": self.report.final_allowed,
            "qa_report": self.report.as_dict(),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> QaAttestation:
        report_value = value.get("qa_report")
        if value.get("schema_version") != 1 or not isinstance(report_value, Mapping):
            raise ValueError("Invalid QA attestation.")
        receipt = cls(
            sha256=str(value["sha256"]),
            byte_count=int(value["byte_count"]),
            report=QaReport.from_mapping(report_value),
        )
        if not receipt.report.final_allowed:
            raise ValueError("QA attestation does not allow Final status.")
        return receipt


def attestation_path(html_path: Path) -> Path:
    """Return the auditable sidecar path for an HTML artifact."""
    source = Path(html_path)
    return source.with_name(f"{source.name}.qa.json")


def attest_document(html_path: Path, report: QaReport) -> QaAttestation:
    """Create a Final-only receipt after a successful QA run for the artifact."""
    source = Path(html_path)
    if not source.is_file():
        raise FileNotFoundError(f"HTML input does not exist: {source}")
    if not report.final_allowed:
        raise ValueError("QA report does not allow Final status.")
    content = source.read_bytes()
    return QaAttestation(hashlib.sha256(content).hexdigest(), len(content), report)


def write_attestation(
    html_path: Path, receipt: QaAttestation, *, destination: Path | None = None
) -> Path:
    """Atomically persist a receipt only when it matches the published HTML exactly."""
    source = Path(html_path)
    if not receipt.matches(source):
        raise ValueError("QA attestation does not match the HTML artifact.")
    target = destination or attestation_path(source)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(receipt.as_dict(), stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return target


def load_attestation(html_path: Path) -> QaAttestation | None:
    """Load a valid sidecar receipt, treating malformed or stale data as absent."""
    try:
        value = json.loads(attestation_path(html_path).read_text(encoding="utf-8"))
        return QaAttestation.from_mapping(value) if isinstance(value, Mapping) else None
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError, KeyError):
        return None

"""Conservative recursive redaction for persisted eval traces and command diagnostics."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_SENSITIVE_KEY = re.compile(r"(?:authorization|api[_-]?key|token|secret|password)", re.IGNORECASE)
_AUTHORIZATION = re.compile(
    r"(authorization\s*[:=]\s*(?:bearer\s+)?)['\"]?[^\s,;'\"]+", re.IGNORECASE
)
_ASSIGNMENT = re.compile(
    r"((?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?)[^\s,;'\"]+", re.IGNORECASE
)
_PASSPORT = re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def redact_text(value: str) -> str:
    """Remove common credentials and sensitive fixture identifiers from human-readable text."""
    result = _AUTHORIZATION.sub(r"\1<redacted>", value)
    result = _ASSIGNMENT.sub(r"\1<redacted>", result)
    result = _PASSPORT.sub("<redacted>", result)
    return _CARD.sub("<redacted>", result)


def redact_value(value: Any) -> Any:
    """Deep-copy a JSON-like value while redacting values and sensitive mapping fields."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            str(key): "<redacted>" if _SENSITIVE_KEY.search(str(key)) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact_value(item) for item in value]
    return value

"""Semantic change detection and deterministic partial-rebuild targets."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from .state import TripState

ImpactKind = Literal["candidate", "day", "leg", "readiness", "route", "outputs"]
_BOOKKEEPING_FIELDS = frozenset({"updated_at", "generated_at"})
_TARGET_ORDER = {"candidate": 0, "day": 1, "leg": 2, "readiness": 3, "route": 4, "outputs": 5}


@dataclass(frozen=True, order=True)
class ImpactTarget:
    kind: ImpactKind
    entity_id: str


@dataclass(frozen=True)
class ImpactReport:
    before_hash: str
    after_hash: str
    changed_ids: tuple[str, ...]
    targets: tuple[ImpactTarget, ...]

    @property
    def changed(self) -> bool:
        return self.before_hash != self.after_hash

    def as_dict(self) -> dict[str, Any]:
        return {
            "changed": self.changed,
            "before_hash": self.before_hash,
            "after_hash": self.after_hash,
            "changed_ids": list(self.changed_ids),
            "targets": [asdict(target) for target in self.targets],
        }


def _semantic_value(value: Any) -> Any:
    if isinstance(value, TripState):
        return {
            "brief": _semantic_value(value.brief),
            "candidates": _semantic_value(value.candidates),
            "itinerary": _semantic_value(value.itinerary),
            "readiness": _semantic_value(value.readiness),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return _semantic_value(asdict(value))
    if isinstance(value, Mapping):
        return {
            str(key): _semantic_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _BOOKKEEPING_FIELDS
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_semantic_value(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, Path)):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return value


def semantic_hash(value: Any) -> str:
    """Hash canonical meaning while ignoring declared bookkeeping timestamps."""
    serialized = json.dumps(
        _semantic_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _entity_index(items: Any) -> dict[str, Any]:
    if not isinstance(items, list):
        return {}
    indexed: dict[str, Any] = {}
    for position, item in enumerate(items):
        if isinstance(item, Mapping):
            entity_id = str(item.get("id") or item.get("day_id") or f"index-{position}")
        else:
            entity_id = f"index-{position}"
        indexed[entity_id] = item
    return indexed


def _changed_entities(before: Any, after: Any) -> tuple[str, ...]:
    before_index = _entity_index(before)
    after_index = _entity_index(after)
    return tuple(
        entity_id
        for entity_id in sorted(before_index.keys() | after_index.keys())
        if semantic_hash(before_index.get(entity_id)) != semantic_hash(after_index.get(entity_id))
    )


def _without(mapping: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    return {key: value for key, value in mapping.items() if key not in keys}


def _target_key(target: ImpactTarget) -> tuple[int, str]:
    return (_TARGET_ORDER[target.kind], target.entity_id)


def analyze_change(before: TripState, after: TripState) -> ImpactReport:
    """Map state differences to the smallest deterministic rebuild boundary."""
    before_hash = semantic_hash(before)
    after_hash = semantic_hash(after)
    if before_hash == after_hash:
        return ImpactReport(before_hash, after_hash, (), ())

    targets: set[ImpactTarget] = set()
    changed_ids: set[str] = set()

    candidate_ids = _changed_entities(before.candidates.get("items"), after.candidates.get("items"))
    day_ids = _changed_entities(before.itinerary.get("days"), after.itinerary.get("days"))
    readiness_ids = _changed_entities(before.readiness.get("items"), after.readiness.get("items"))
    for entity_id in candidate_ids:
        changed_ids.add(entity_id)
        targets.add(ImpactTarget("candidate", entity_id))
    for entity_id in day_ids:
        changed_ids.add(entity_id)
        targets.add(ImpactTarget("day", entity_id))
    for entity_id in readiness_ids:
        changed_ids.add(entity_id)
        targets.add(ImpactTarget("readiness", entity_id))

    route_changed = (
        semantic_hash(before.brief) != semantic_hash(after.brief)
        or semantic_hash(_without(before.itinerary, "days"))
        != semantic_hash(_without(after.itinerary, "days"))
    )
    if route_changed:
        changed_ids.add("route")
        targets.add(ImpactTarget("route", "all"))

    candidates_metadata_changed = semantic_hash(_without(before.candidates, "items")) != semantic_hash(
        _without(after.candidates, "items")
    )
    readiness_metadata_changed = semantic_hash(
        _without(before.readiness, "items")
    ) != semantic_hash(_without(after.readiness, "items"))
    if candidates_metadata_changed or readiness_metadata_changed:
        changed_ids.add("state-metadata")

    targets.add(ImpactTarget("outputs", "all"))
    return ImpactReport(
        before_hash,
        after_hash,
        tuple(sorted(changed_ids)),
        tuple(sorted(targets, key=_target_key)),
    )


def select_rebuild_targets(report: ImpactReport) -> tuple[ImpactTarget, ...]:
    """Expose the stable target selection boundary for future render adapters."""
    return report.targets

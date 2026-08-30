from datetime import UTC, datetime
from pathlib import Path

import pytest
from travel_planner.decisions import DecisionRecord, DuplicateDecisionError, append_decision


def test_decision_journal_appends_without_replacing_history(tmp_path: Path) -> None:
    """Catch a new decision overwriting the rationale for an earlier choice."""
    path = tmp_path / "decisions.md"
    path.write_text("# Decisions\n", encoding="utf-8")
    first = DecisionRecord(
        decision_id="decision-route",
        decided_at=datetime(2026, 8, 28, 12, tzinfo=UTC),
        selected_option="Balanced route",
        reason="Keeps two slower mornings",
        rejected_alternatives=("Compact route",),
        affected_ids=("route-balanced",),
    )
    second = DecisionRecord(
        decision_id="decision-hotel",
        decided_at=datetime(2026, 8, 29, 9, tzinfo=UTC),
        selected_option="Station hotel",
        reason="Reduces luggage transfer risk",
        rejected_alternatives=("Old town hotel",),
        affected_ids=("night-4", "day-5"),
    )

    append_decision(path, first)
    append_decision(path, second)
    journal = path.read_text(encoding="utf-8")

    assert journal.index("decision-route") < journal.index("decision-hotel")
    assert "Keeps two slower mornings" in journal
    assert "Reduces luggage transfer risk" in journal


def test_duplicate_decision_id_is_rejected(tmp_path: Path) -> None:
    """Catch an immutable decision identifier being silently reused."""
    path = tmp_path / "decisions.md"
    record = DecisionRecord(
        decision_id="decision-route",
        decided_at=datetime(2026, 8, 28, 12, tzinfo=UTC),
        selected_option="Balanced route",
        reason="Best fit",
    )
    append_decision(path, record)

    with pytest.raises(DuplicateDecisionError):
        append_decision(path, record)

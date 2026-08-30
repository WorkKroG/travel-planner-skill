from datetime import UTC, datetime

from travel_planner.checks import CheckReport
from travel_planner.render.markdown import render_markdown
from travel_planner.render.viewmodel import build_view
from travel_planner.state import TripState

GENERATED_AT = datetime(2026, 8, 28, 12, tzinfo=UTC)


def test_markdown_uses_approved_reading_order(
    japan_state: TripState, japan_report: CheckReport
) -> None:
    """Catch an output that places detailed days before route, decisions, or blockers."""
    document = render_markdown(build_view(japan_state, japan_report, GENERATED_AT))

    assert document.startswith("# Japan Autumn — Render Reference\n\n**Status: Draft**")
    assert document.index("## Trip summary") < document.index("## Route overview")
    assert document.index("## Open decisions") < document.index("## Detailed days")
    assert document.index("## Preparation") < document.index("## Budget")
    assert document.index("## Risks and warnings") < document.index("## Sources")


def test_markdown_prints_unknown_stale_conflicting_and_last_checked_text(
    japan_state: TripState, japan_report: CheckReport
) -> None:
    """Catch uncertainty disappearing behind blank values or colour-only presentation."""
    document = render_markdown(build_view(japan_state, japan_report, GENERATED_AT))

    assert "Unknown" in document
    assert "Stale" in document
    assert "Conflicting" in document
    assert "Last checked: 2026-07-01T10:00:00+00:00" in document
    assert "Rail booking window is not open yet." in document


def test_markdown_is_byte_deterministic_for_fixed_inputs(
    japan_state: TripState, japan_report: CheckReport
) -> None:
    """Catch hidden clock reads or unstable collection ordering in derived documents."""
    view = build_view(japan_state, japan_report, GENERATED_AT)

    assert render_markdown(view).encode() == render_markdown(view).encode()

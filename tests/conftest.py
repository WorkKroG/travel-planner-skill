import shutil
from pathlib import Path

import pytest
from travel_planner.checks import CheckReport, Finding
from travel_planner.render.viewmodel import ItineraryView, build_view
from travel_planner.state import TripState, load_trip


@pytest.fixture
def minimal_trip(tmp_path: Path) -> Path:
    source = Path(__file__).parent / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return target


@pytest.fixture
def japan_state(tmp_path: Path) -> TripState:
    source = Path(__file__).parent / "fixtures" / "japan-reference"
    target = tmp_path / "japan-reference"
    shutil.copytree(source, target)
    return load_trip(target)


@pytest.fixture
def japan_report() -> CheckReport:
    return CheckReport(
        structural_errors=(),
        findings=(),
        saved_findings=(
            Finding(
                id="booking-window-rail-release",
                code="BOOK-001",
                severity="blocking",
                path="readiness.yaml.items[0]",
                affected_ids=("rail-release", "day-2"),
                message="Rail booking window is not open yet.",
            ),
            Finding(
                id="source-recheck-day-3",
                code="EVID-001",
                severity="warning",
                path="itinerary.yaml.days[2]",
                affected_ids=("day-3",),
                message="Garden hours require rechecking.",
            ),
        ),
        lifecycle_findings=(),
        accepted_blocker_ids=(),
    )


@pytest.fixture
def japan_view(japan_state: TripState, japan_report: CheckReport) -> ItineraryView:
    from datetime import UTC, datetime

    return build_view(japan_state, japan_report, datetime(2026, 8, 28, 12, tzinfo=UTC))

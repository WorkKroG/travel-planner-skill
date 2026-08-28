import shutil
from pathlib import Path

import pytest
from travel_planner.challenge import ChallengeReport
from travel_planner.evidence import Finding
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
def japan_report() -> ChallengeReport:
    from datetime import UTC, datetime

    generated_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    return ChallengeReport(
        stage="detailed",
        evaluated_at=generated_at,
        findings=(
            Finding(
                rule_id="BOOK-001",
                severity="blocking",
                confidence="high",
                affected_ids=("rail-release", "day-2"),
                evidence_ids=("source-rail",),
                message="Rail booking window is not open yet.",
            ),
            Finding(
                rule_id="EVID-001",
                severity="warning",
                confidence="medium",
                affected_ids=("day-3",),
                evidence_ids=("source-garden",),
                message="Garden hours require rechecking.",
            ),
        ),
        rule_versions=(("BOOK-001", 1), ("EVID-001", 1)),
    )

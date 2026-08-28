import shutil
from pathlib import Path

import pytest
import yaml
from travel_planner.cli import main
from travel_planner.state import load_trip, validate_trip, write_state_file


@pytest.fixture
def minimal_trip(tmp_path: Path) -> Path:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return target


def test_unknown_readiness_status_reports_exact_path(minimal_trip: Path) -> None:
    """Catch invalid readiness state without forcing the user to hunt for its field."""
    data = yaml.safe_load((minimal_trip / "readiness.yaml").read_text())
    data["items"] = [{"id": "ready-1", "status": "done-ish", "category": "entry"}]
    write_state_file(minimal_trip / "readiness.yaml", data)

    report = validate_trip(minimal_trip)

    assert report.ok is False
    assert report.issues[0].path == "readiness.yaml.items[0].status"


def test_candidate_keeps_evidence_popularity_assessment_and_verdict_separate(
    minimal_trip: Path,
) -> None:
    """Catch a candidate model that turns popularity or opinion into a fact."""
    candidate = load_trip(minimal_trip).candidates["items"][0]

    assert {"claims", "popularity_signals", "assessments", "verdict"} <= candidate.keys()
    assert candidate["verdict"] not in candidate["claims"]


def test_write_state_file_preserves_mapping_order_and_valid_yaml(minimal_trip: Path) -> None:
    """Catch an atomic writer that reshuffles human-edited state or emits broken YAML."""
    path = minimal_trip / "readiness.yaml"
    value = {"schema_version": 1, "trip_id": "minimal-trip", "items": []}

    write_state_file(path, value)

    assert list(yaml.safe_load(path.read_text()).keys()) == ["schema_version", "trip_id", "items"]
    assert path.read_text().splitlines()[0] == "schema_version: 1"


def test_validate_cli_reports_file_and_field_for_corrupt_state(
    minimal_trip: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch validation diagnostics that are unusable from a terminal or Codex."""
    data = yaml.safe_load((minimal_trip / "itinerary.yaml").read_text())
    data["route_state"] = "almost-final"
    write_state_file(minimal_trip / "itinerary.yaml", data)

    exit_code = main(["validate", str(minimal_trip)])

    assert exit_code == 2
    assert "itinerary.yaml.route_state" in capsys.readouterr().err

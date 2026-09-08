from pathlib import Path

import pytest
import yaml
from travel_planner import workspace as workspace_module
from travel_planner.cli import main
from travel_planner.workspace import (
    WorkspaceExistsError,
    discover_trip_roots,
    initialize_trip,
)


def test_initialize_trip_never_overwrites_an_existing_trip(tmp_path: Path) -> None:
    """Catch a second initialization replacing an existing trip's identity."""
    initialize_trip(tmp_path, "Japan 2026", "japan-2026")

    with pytest.raises(WorkspaceExistsError):
        initialize_trip(tmp_path, "Iceland 2027", "iceland-2027")

    brief = yaml.safe_load((tmp_path / "brief.yaml").read_text())
    assert brief["trip_id"] == "japan-2026"


def test_discovery_returns_all_trips_in_stable_order(tmp_path: Path) -> None:
    """Catch discovery silently choosing one of two simultaneous trips."""
    initialize_trip(tmp_path / "b", "B", "trip-b")
    initialize_trip(tmp_path / "a", "A", "trip-a")

    assert [path.name for path in discover_trip_roots(tmp_path)] == ["a", "b"]


def test_initialize_creates_the_complete_workspace(tmp_path: Path) -> None:
    """Catch an initializer that leaves a trip impossible to resume."""
    root = tmp_path / "new-trip"

    paths = initialize_trip(root, "New Trip", "new-trip")

    assert paths.root == root
    assert {path.name for path in root.iterdir()} == {
        "brief.yaml",
        "candidates.yaml",
        "decisions.md",
        "itinerary.yaml",
        "outputs",
        "readiness.yaml",
    }
    assert paths.outputs.is_dir()
    itinerary = yaml.safe_load(paths.itinerary.read_text())
    expected_lifecycle = {
        "document_status": "draft",
        "verification_level": "none",
        "finalization_basis": None,
        "accepted_blockers": [],
    }
    assert {key: itinerary.get(key) for key in expected_lifecycle} == expected_lifecycle


def test_workspace_names_canonical_and_generated_paths_separately() -> None:
    """Catch generated outputs being mislabeled as canonical trip state."""
    assert getattr(workspace_module, "CANONICAL_FILES", ()) == (
        "brief.yaml",
        "candidates.yaml",
        "itinerary.yaml",
        "readiness.yaml",
        "decisions.md",
    )
    assert getattr(workspace_module, "GENERATED_FILES", ()) == ()
    assert getattr(workspace_module, "GENERATED_DIRECTORIES", ()) == ("outputs",)


def test_cli_refuses_to_write_until_path_is_confirmed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch the CLI writing trip state before explicit path confirmation."""
    root = tmp_path / "unconfirmed"

    exit_code = main(["init", str(root), "--title", "Unconfirmed"])

    assert exit_code == 2
    assert not root.exists()
    assert "Codex project" in capsys.readouterr().err


def test_cli_reports_the_initialized_trip_identity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch a successful initialization that crashes before reporting its identity."""
    root = tmp_path / "confirmed"

    exit_code = main(
        [
            "init",
            str(root),
            "--title",
            "Confirmed",
            "--trip-id",
            "confirmed-trip",
            "--confirm-path",
        ]
    )

    assert exit_code == 0
    assert "confirmed-trip" in capsys.readouterr().out

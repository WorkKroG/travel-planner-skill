from pathlib import Path

import pytest
import yaml
from travel_planner.cli import main
from travel_planner.migration import (
    ConfirmationRequired,
    MigrationError,
    SourceChanged,
    apply_migration,
    preview_migration,
)
from travel_planner.state import STATE_SCHEMA_FILES


def _versions(root: Path) -> dict[str, int]:
    return {
        name: yaml.safe_load((root / name).read_text(encoding="utf-8"))["schema_version"]
        for name in STATE_SCHEMA_FILES
    }


def test_migration_preview_is_read_only_and_confirmation_is_required(
    minimal_trip: Path,
) -> None:
    before = _versions(minimal_trip)

    plan = preview_migration(minimal_trip, 2)

    assert _versions(minimal_trip) == before
    assert plan.target_version == 2
    assert {change.file_name for change in plan.changes} == set(STATE_SCHEMA_FILES)
    assert not plan.backup_root.exists()
    with pytest.raises(ConfirmationRequired):
        apply_migration(plan, confirmed=False)
    assert not plan.backup_root.exists()


def test_confirmed_migration_creates_sibling_backup_and_updates_versions(
    minimal_trip: Path,
) -> None:
    plan = preview_migration(minimal_trip, 2)

    apply_migration(plan, confirmed=True)

    assert plan.backup_root.parent == minimal_trip.parent
    assert plan.backup_root.name.startswith(f"{minimal_trip.name}.backup-")
    assert plan.backup_root.is_dir()
    assert set(_versions(minimal_trip).values()) == {2}
    assert set(_versions(plan.backup_root).values()) == {1}
    assert preview_migration(minimal_trip, 2).changes == ()


def test_failed_validation_restores_original_state(
    minimal_trip: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from travel_planner import migration

    before = {
        name: (minimal_trip / name).read_bytes() for name in STATE_SCHEMA_FILES
    }
    plan = preview_migration(minimal_trip, 2)

    def reject_migrated_state(root: Path, target_version: int) -> None:
        raise MigrationError("simulated validation failure")

    monkeypatch.setattr(migration, "_validate_migrated_root", reject_migrated_state)

    with pytest.raises(MigrationError, match="restored"):
        apply_migration(plan, confirmed=True)

    assert plan.backup_root.is_dir()
    assert {
        name: (minimal_trip / name).read_bytes() for name in STATE_SCHEMA_FILES
    } == before


def test_apply_refuses_when_state_changed_after_preview(minimal_trip: Path) -> None:
    plan = preview_migration(minimal_trip, 2)
    brief = minimal_trip / "brief.yaml"
    brief.write_text(brief.read_text(encoding="utf-8") + "\n# user edit\n", encoding="utf-8")

    with pytest.raises(SourceChanged):
        apply_migration(plan, confirmed=True)

    assert not plan.backup_root.exists()


def test_migration_cli_defaults_to_preview_only(minimal_trip: Path, capsys) -> None:
    exit_code = main(["migrate", str(minimal_trip), "--target-version", "2"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"mode": "preview"' in output
    assert set(_versions(minimal_trip).values()) == {1}

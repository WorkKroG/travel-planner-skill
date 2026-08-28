from pathlib import Path

from travel_planner.resources import resource_path


def test_resource_lookup_falls_back_to_installed_data(tmp_path: Path) -> None:
    """Catch clean installs that contain Python code but cannot find schemas or templates."""
    missing_source = tmp_path / "source" / "schemas"
    installed = tmp_path / "share" / "schemas"
    installed.mkdir(parents=True)
    schema = installed / "brief.schema.json"
    schema.write_text("{}", encoding="utf-8")

    result = resource_path("schemas", "brief.schema.json", roots=(missing_source, installed))

    assert result == schema


def test_resource_lookup_rejects_parent_traversal(tmp_path: Path) -> None:
    """Catch a resource name escaping the approved package data directories."""
    root = tmp_path / "schemas"
    root.mkdir()

    try:
        resource_path("schemas", "../secret.txt", roots=(root,))
    except ValueError as error:
        assert "plain file name" in str(error)
    else:
        raise AssertionError("parent traversal was accepted")

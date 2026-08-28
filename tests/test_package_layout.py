import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_plugin_layout_and_version_agree() -> None:
    """Catch a manifest/package version mismatch or missing skill entrypoint."""
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())

    assert manifest["name"] == "travel-planner"
    assert manifest["version"] == "0.1.0"
    assert manifest["skills"] == "./skills/"
    assert (ROOT / "skills/travel-planner/SKILL.md").exists()

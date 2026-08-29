"""Contract tests for the installable travel-planner skill entrypoint."""

from __future__ import annotations

from pathlib import Path

import yaml

SKILL_PATH = Path(__file__).resolve().parents[2] / "skills" / "travel-planner" / "SKILL.md"


def parse_skill(path: Path) -> tuple[dict[str, object], str]:
    """Load frontmatter independently from the skill's Markdown instructions."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, frontmatter, body = text.split("---\n", 2)
    value = yaml.safe_load(frontmatter)
    assert isinstance(value, dict)
    return value, body


def test_skill_frontmatter_is_minimal_and_specific() -> None:
    """Catch a broad or metadata-heavy trigger that misroutes place questions."""
    frontmatter, _ = parse_skill(SKILL_PATH)

    assert frontmatter["name"] == "travel-planner"
    assert set(frontmatter) == {"name", "description"}
    description = str(frontmatter["description"])
    assert description.startswith("Use when")
    assert "путешеств" in description.lower()
    assert "do not use for a single factual question about one place" in description.lower()

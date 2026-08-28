import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from travel_planner.challenge import ChallengeContext, run_challenge
from travel_planner.challenge.base import DuplicateRuleError
from travel_planner.cli import main
from travel_planner.evidence import Finding
from travel_planner.state import load_trip, write_state_file

NOW = datetime(2026, 8, 28, 12, tzinfo=UTC)


@dataclass(frozen=True)
class FakeRule:
    rule_id: str
    severity: str
    version: int = 1
    stages: frozenset[str] = frozenset({"skeleton", "detailed"})

    def evaluate(self, ctx: ChallengeContext):
        return (
            Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                confidence="high",
                affected_ids=(ctx.state.brief["trip_id"],),
                evidence_ids=(),
                message=f"Finding from {self.rule_id}",
                rule_version=self.version,
            ),
        )


@pytest.fixture
def state(tmp_path: Path):
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return load_trip(target)


def test_report_is_stable_and_blocking_fails_macro_gate(state) -> None:
    """Catch unstable findings or a blocking constraint hidden by aggregate scoring."""
    rules = [FakeRule("LEG-002", "warning"), FakeRule("CAL-001", "blocking")]

    report = run_challenge(state, "skeleton", NOW, rules=rules)

    assert [finding.rule_id for finding in report.findings] == ["CAL-001", "LEG-002"]
    assert report.hard_pass is False


def test_report_serialization_is_byte_stable(state) -> None:
    """Catch nondeterministic challenge output that creates noisy rebuilds."""
    rules = [FakeRule("OPS-002", "note"), FakeRule("CAL-001", "warning")]

    first = json.dumps(run_challenge(state, "detailed", NOW, rules=rules).as_dict())
    second = json.dumps(run_challenge(state, "detailed", NOW, rules=reversed(rules)).as_dict())

    assert first == second


def test_duplicate_rule_ids_are_rejected(state) -> None:
    """Catch two implementations emitting indistinguishable rule identifiers."""
    with pytest.raises(DuplicateRuleError):
        run_challenge(
            state,
            "skeleton",
            NOW,
            rules=[FakeRule("CAL-001", "warning"), FakeRule("CAL-001", "blocking")],
        )


def test_cli_returns_three_when_macro_gate_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch a blocking challenge being reported as command success."""
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    candidates = yaml.safe_load((target / "candidates.yaml").read_text())
    candidates["sources"] = [
        {
            "id": "blog-1",
            "url": "https://example.com/visa",
            "source_type": "editorial",
            "publisher": "Blog",
            "retrieved_at": "2026-08-20T12:00:00+00:00",
        }
    ]
    candidates["claims"] = [
        {
            "id": "claim-entry",
            "topic": "entry",
            "status": "reported",
            "source_ids": ["blog-1"],
        }
    ]
    write_state_file(target / "candidates.yaml", candidates)

    exit_code = main(
        ["challenge", str(target), "--stage", "skeleton", "--at", NOW.isoformat()]
    )

    assert exit_code == 3
    assert "EVID-001" in capsys.readouterr().out

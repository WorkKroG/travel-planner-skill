import argparse
import json
from pathlib import Path

import pytest
import yaml
from travel_planner.cli import _parser, main
from travel_planner.state import write_state_file


def _commands() -> tuple[str, ...]:
    parser = _parser()
    action = next(item for item in parser._actions if isinstance(item, argparse._SubParsersAction))
    return tuple(action.choices)


def _update_itinerary(root: Path, **updates: object) -> None:
    itinerary = yaml.safe_load((root / "itinerary.yaml").read_text(encoding="utf-8"))
    itinerary.update(updates)
    write_state_file(root / "itinerary.yaml", itinerary)


def test_parser_exposes_exact_internal_cli_inventory() -> None:
    assert _commands() == ("init", "check", "render")

    with pytest.raises(SystemExit):
        _parser().parse_args(["challenge"])
    with pytest.raises(SystemExit):
        _parser().parse_args(["pdf"])


def test_check_returns_2_and_structural_errors_for_invalid_state(
    minimal_trip: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _update_itinerary(minimal_trip, route_state="not-a-route-state")

    exit_code = main(["check", str(minimal_trip)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["ok"] is False
    assert payload["structural_errors"][0]["path"] == "itinerary.yaml.route_state"
    assert payload["findings"] == []


def test_check_returns_0_and_keeps_draft_blocker_visible(
    minimal_trip: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _update_itinerary(
        minimal_trip,
        challenge_findings=[
            {
                "id": "blocker-rail",
                "code": "SCHEDULE_UNRELEASED",
                "severity": "blocking",
                "status": "unresolved",
                "path": "itinerary.yaml.days[0]",
                "affected_ids": ["day-1"],
                "message": "The final timetable is not released.",
            }
        ],
    )

    exit_code = main(["check", str(minimal_trip)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["lifecycle_consistent"] is True
    assert payload["unaccepted_blocking_findings"][0]["id"] == "blocker-rail"


def test_check_returns_0_for_user_confirmed_final_with_accepted_blocker(
    minimal_trip: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _update_itinerary(
        minimal_trip,
        document_status="final",
        verification_level="ai_reviewed",
        finalization_basis="user_confirmed",
        challenge_findings=[
            {
                "id": "blocker-rail",
                "code": "SCHEDULE_UNRELEASED",
                "severity": "blocking",
                "status": "unresolved",
                "path": "itinerary.yaml.days[0]",
                "affected_ids": ["day-1"],
                "message": "The final timetable is not released.",
            }
        ],
        accepted_blockers=[
            {
                "blocker_id": "blocker-rail",
                "accepted_by_user": True,
                "accepted_at": "2026-08-30T09:00:00+00:00",
                "rationale": "The user accepts the remaining timetable uncertainty.",
            }
        ],
    )

    exit_code = main(["check", str(minimal_trip)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["ok"] is True
    assert payload["accepted_blocking_findings"][0]["severity"] == "blocking"


def test_render_writes_only_html_without_a_format_switch(
    minimal_trip: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "trip.html"

    exit_code = main(
        [
            "render",
            str(minimal_trip),
            "--output",
            str(output),
            "--at",
            "2026-08-30T09:00:00+00:00",
        ]
    )

    assert exit_code == 0
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert "Rendered HTML" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        _parser().parse_args(
            [
                "render",
                str(minimal_trip),
                "--format",
                "markdown",
                "--output",
                str(output),
                "--at",
                "2026-08-30T09:00:00+00:00",
            ]
        )

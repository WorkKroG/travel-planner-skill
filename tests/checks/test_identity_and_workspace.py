import json
from copy import deepcopy
from pathlib import Path

import yaml
from travel_planner.checks import run_checks
from travel_planner.cli import main
from travel_planner.state import load_trip, write_state_file


def test_duplicate_canonical_ids_and_acceptances_have_exact_paths(
    minimal_trip: Path,
) -> None:
    state = load_trip(minimal_trip)
    state.itinerary.update(
        {
            "alternatives": [{"id": "route-one"}, {"id": "route-one"}],
            "route_stops": [{"id": "stop-one"}, {"id": "stop-one"}],
            "days": [
                {
                    "id": "day-one",
                    "timeline": [
                        {"id": "leg-one", "time": "09:00", "title": "First", "detail": ""},
                        {"id": "leg-one", "time": "10:00", "title": "Second", "detail": ""},
                    ],
                },
                {"id": "day-one", "timeline": []},
            ],
            "challenge_findings": [
                {"id": "blocker-one", "code": "SAVED", "severity": "blocking", "status": "unresolved", "path": "itinerary.yaml.days[0]", "affected_ids": [], "message": "One."},
                {"id": "blocker-one", "code": "SAVED", "severity": "blocking", "status": "unresolved", "path": "itinerary.yaml.days[1]", "affected_ids": [], "message": "Two."},
            ],
            "accepted_blockers": [
                {"blocker_id": "blocker-one", "accepted_by_user": True, "accepted_at": "2026-08-30T09:00:00+00:00", "rationale": "Accepted once."},
                {"blocker_id": "blocker-one", "accepted_by_user": True, "accepted_at": "2026-08-30T09:01:00+00:00", "rationale": "Accepted twice."},
            ],
            "budget_items": [
                {"id": "budget-one", "amount_type": "exact", "amount": 10, "currency": "USD", "basis": "per_group"},
                {"id": "budget-one", "amount_type": "exact", "amount": 10, "currency": "USD", "basis": "per_group"},
            ],
        }
    )
    state.brief["travelers"] = [{"id": "traveler-one"}, {"id": "traveler-one"}]
    state.candidates["sources"] = [
        {"id": "source-one", "url": "https://one.example", "source_type": "official", "publisher": "One", "retrieved_at": "2026-08-20T12:00:00+00:00"},
        {"id": "source-one", "url": "https://two.example", "source_type": "official", "publisher": "Two", "retrieved_at": "2026-08-20T12:00:00+00:00"},
    ]
    state.candidates["claims"] = [
        {"id": "claim-one", "topic": "entry", "status": "verified", "source_ids": ["source-one"]},
        {"id": "claim-one", "topic": "entry", "status": "verified", "source_ids": ["source-one"]},
    ]
    candidate = deepcopy(state.candidates["items"][0])
    candidate["id"] = "candidate-one"
    candidate["claims"] = []
    state.candidates["items"] = [candidate, deepcopy(candidate)]
    state.readiness["items"] = [
        {"id": "ready-one", "category": "transport", "status": "action_needed"},
        {"id": "ready-one", "category": "lodging", "status": "action_needed"},
    ]

    report = run_checks(state)

    duplicate_paths = {finding.path for finding in report.all_findings if finding.code == "ID_DUPLICATE"}
    assert duplicate_paths == {
        "itinerary.yaml.alternatives[1].id",
        "itinerary.yaml.route_stops[1].id",
        "itinerary.yaml.days[1].id",
        "itinerary.yaml.days[0].timeline[1].id",
        "candidates.yaml.sources[1].id",
        "candidates.yaml.claims[1].id",
        "readiness.yaml.items[1].id",
        "itinerary.yaml.challenge_findings[1].id",
        "itinerary.yaml.accepted_blockers[1].blocker_id",
        "itinerary.yaml.budget_items[1].id",
        "brief.yaml.travelers[1].id",
        "candidates.yaml.items[1].id",
    }
    assert report.ok is False


def test_initialized_workspace_runs_checks_on_canonical_timeline(
    tmp_path: Path, capsys
) -> None:
    root = tmp_path / "ordinary-user-trip"
    assert main(["init", str(root), "--title", "Ordinary trip", "--confirm-path"]) == 0
    capsys.readouterr()
    itinerary = yaml.safe_load((root / "itinerary.yaml").read_text(encoding="utf-8"))
    itinerary.update(
        {
            "alternatives": [{"id": "route-one"}],
            "selected_route_id": "route-one",
            "route_stops": [{"id": "stop-one"}],
            "days": [
                {
                    "id": "day-one",
                    "overnight": "City",
                    "overnight_stop_id": "stop-one",
                    "timeline": [
                        {"id": "event-one", "time": "09:00", "title": "First", "detail": "First event.", "start_at": "2026-11-02T09:00:00+00:00", "end_at": "2026-11-02T10:00:00+00:00"},
                        {"id": "event-two", "time": "09:30", "title": "Second", "detail": "Overlapping event.", "start_at": "2026-11-02T09:30:00+00:00", "end_at": "2026-11-02T10:30:00+00:00"},
                    ],
                }
            ],
            "budget_summary": None,
        }
    )
    write_state_file(root / "itinerary.yaml", itinerary)

    exit_code = main(["check", str(root)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["structural_errors"] == []
    assert payload["findings"] == []


def test_malformed_stored_blocker_is_a_structural_cli_error(
    minimal_trip: Path, capsys
) -> None:
    itinerary = yaml.safe_load((minimal_trip / "itinerary.yaml").read_text(encoding="utf-8"))
    itinerary.update(
        {
            "document_status": "final",
            "verification_level": "codex_validated",
            "finalization_basis": "codex_validated",
            "challenge_findings": [{"severity": "blocking", "message": "Missing identity."}],
        }
    )
    write_state_file(minimal_trip / "itinerary.yaml", itinerary)

    exit_code = main(["check", str(minimal_trip)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert payload["structural_errors"][0]["path"].startswith(
        "itinerary.yaml.challenge_findings[0]"
    )

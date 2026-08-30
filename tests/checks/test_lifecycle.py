from copy import deepcopy

from travel_planner.checks import run_checks
from travel_planner.state import TripState


def _state(japan_state: TripState, **itinerary_updates: object) -> TripState:
    state = deepcopy(japan_state)
    state.itinerary["selected_route_id"] = None
    state.itinerary["alternatives"] = []
    state.itinerary["route_stops"] = []
    state.itinerary["days"] = []
    state.itinerary["budget_items"] = []
    state.itinerary["budget_summary"] = None
    state.itinerary.update(itinerary_updates)
    return state


def _blocker(blocker_id: str = "blocker-rail") -> dict[str, object]:
    return {
        "id": blocker_id,
        "code": "SCHEDULE_UNRELEASED",
        "severity": "blocking",
        "status": "unresolved",
        "path": "itinerary.yaml.days[1]",
        "affected_ids": ["day-2"],
        "message": "The final timetable is not released.",
    }


def _acceptance(blocker_id: str = "blocker-rail") -> dict[str, object]:
    return {
        "blocker_id": blocker_id,
        "accepted_by_user": True,
        "accepted_at": "2026-08-30T09:00:00+00:00",
        "rationale": "The user accepts the remaining timetable uncertainty.",
    }


def test_draft_reports_unaccepted_saved_blocker_without_mutating_state(
    japan_state: TripState,
) -> None:
    state = _state(
        japan_state,
        document_status="draft",
        verification_level="none",
        finalization_basis=None,
        accepted_blockers=[],
        challenge_findings=[_blocker()],
    )
    before = deepcopy(state.itinerary)

    report = run_checks(state)

    assert report.ok is False
    assert report.lifecycle_consistent is True
    assert [finding.id for finding in report.blocking_findings] == ["blocker-rail"]
    assert report.accepted_blocking_findings == ()
    assert [finding.id for finding in report.unaccepted_blocking_findings] == [
        "blocker-rail"
    ]
    assert state.itinerary == before


def test_user_confirmed_final_accepts_but_does_not_resolve_saved_blocker(
    japan_state: TripState,
) -> None:
    state = _state(
        japan_state,
        document_status="final",
        verification_level="ai_reviewed",
        finalization_basis="user_confirmed",
        accepted_blockers=[_acceptance()],
        challenge_findings=[_blocker()],
    )

    report = run_checks(state)

    assert report.ok is True
    assert report.lifecycle_consistent is True
    assert [finding.id for finding in report.accepted_blocking_findings] == [
        "blocker-rail"
    ]
    assert report.unaccepted_blocking_findings == ()
    assert report.findings[0].severity == "blocking"
    assert state.itinerary["challenge_findings"][0]["status"] == "unresolved"


def test_codex_validated_final_with_blocker_is_inconsistent(
    japan_state: TripState,
) -> None:
    report = run_checks(
        _state(
            japan_state,
            document_status="final",
            verification_level="codex_validated",
            finalization_basis="codex_validated",
            accepted_blockers=[],
            challenge_findings=[_blocker()],
        )
    )

    assert report.ok is False
    assert report.lifecycle_consistent is False
    assert report.unaccepted_blocking_findings
    assert any(finding.code == "FINAL_CODEX_HAS_BLOCKERS" for finding in report.lifecycle_findings)


def test_user_confirmed_final_requires_acceptance_for_each_remaining_blocker(
    japan_state: TripState,
) -> None:
    report = run_checks(
        _state(
            japan_state,
            document_status="final",
            verification_level="ai_reviewed",
            finalization_basis="user_confirmed",
            accepted_blockers=[],
            challenge_findings=[_blocker()],
        )
    )

    assert report.lifecycle_consistent is False
    assert [finding.code for finding in report.lifecycle_findings] == [
        "FINAL_USER_BLOCKERS_UNACCEPTED"
    ]
    assert [finding.id for finding in report.unaccepted_blocking_findings if finding.code == "SCHEDULE_UNRELEASED"] == [
        "blocker-rail"
    ]


def test_ai_reviewed_never_satisfies_codex_validation(japan_state: TripState) -> None:
    report = run_checks(
        _state(
            japan_state,
            document_status="final",
            verification_level="ai_reviewed",
            finalization_basis="codex_validated",
            accepted_blockers=[],
            challenge_findings=[],
        )
    )

    assert report.ok is False
    assert report.lifecycle_consistent is False
    assert [finding.code for finding in report.lifecycle_findings] == [
        "FINAL_CODEX_VERIFICATION_REQUIRED"
    ]


def test_invalid_lifecycle_combinations_and_unknown_acceptance_are_reported(
    japan_state: TripState,
) -> None:
    draft = run_checks(
        _state(
            japan_state,
            document_status="draft",
            finalization_basis="user_confirmed",
            accepted_blockers=[],
            challenge_findings=[],
        )
    )
    final_without_basis = run_checks(
        _state(
            japan_state,
            document_status="final",
            finalization_basis=None,
            accepted_blockers=[_acceptance("missing-blocker")],
            challenge_findings=[],
        )
    )

    assert [finding.code for finding in draft.lifecycle_findings] == [
        "DRAFT_FINALIZATION_BASIS"
    ]
    assert {finding.code for finding in final_without_basis.lifecycle_findings} == {
        "FINAL_BASIS_REQUIRED",
        "ACCEPTED_BLOCKER_NOT_FOUND",
    }


def test_computed_and_stored_finding_id_collision_is_inconsistent(
    japan_state: TripState,
) -> None:
    collision_id = "link-route-not-found-missing-route-33730ff5"
    state = _state(
        japan_state,
        document_status="final",
        verification_level="ai_reviewed",
        finalization_basis="user_confirmed",
        alternatives=[],
        selected_route_id="missing-route",
        challenge_findings=[_blocker(collision_id)],
        accepted_blockers=[_acceptance(collision_id)],
    )

    report = run_checks(state)

    assert "FINDING_ID_COLLISION" in [
        finding.code for finding in report.lifecycle_findings
    ]
    assert report.ok is False
    assert len(
        [
            finding
            for finding in report.blocking_findings
            if finding.id == collision_id
        ]
    ) == 2


def test_codex_final_is_not_blocked_by_a_nonblocking_unknown_budget_note(
    japan_state: TripState,
) -> None:
    report = run_checks(
        _state(
            japan_state,
            document_status="final",
            verification_level="codex_validated",
            finalization_basis="codex_validated",
            challenge_findings=[],
            accepted_blockers=[],
            budget_items=[
                {
                    "id": "unknown-cost",
                    "amount_type": "unknown",
                    "currency": "JPY",
                    "basis": "per_group",
                }
            ],
        )
    )

    assert [finding.code for finding in report.findings] == ["BUDGET_AMOUNT_UNKNOWN"]
    assert report.blocking_findings == ()
    assert report.ok is True

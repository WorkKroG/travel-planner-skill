from copy import deepcopy

from travel_planner.checks import run_checks
from travel_planner.state import TripState


def _state(japan_state: TripState) -> TripState:
    state = deepcopy(japan_state)
    state.itinerary.update(
        {
            "document_status": "draft",
            "finalization_basis": None,
            "accepted_blockers": [],
            "challenge_findings": [],
            "selected_route_id": None,
            "budget_items": [],
        }
    )
    return state


def test_calendar_rejects_invalid_and_overlapping_explicit_intervals(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary["days"] = [
        {
            "id": "day-check",
            "intervals": [
                {
                    "id": "visit-a",
                    "start": "2026-11-02T09:00:00+09:00",
                    "end": "2026-11-02T10:30:00+09:00",
                },
                {
                    "id": "visit-b",
                    "start": "2026-11-02T10:00:00+09:00",
                    "end": "2026-11-02T11:00:00+09:00",
                },
                {
                    "id": "visit-invalid",
                    "start": "2026-11-02T12:00:00+09:00",
                    "end": "2026-11-02T12:00:00+09:00",
                },
            ],
        }
    ]

    report = run_checks(state)

    assert [finding.code for finding in report.findings] == [
        "CALENDAR_INTERVAL_INVALID",
        "CALENDAR_INTERVAL_OVERLAP",
    ]
    overlap = next(
        finding for finding in report.findings if finding.code == "CALENDAR_INTERVAL_OVERLAP"
    )
    assert overlap.affected_ids == ("day-check", "visit-a", "visit-b")


def test_calendar_checks_only_explicit_operating_and_service_cutoffs(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary["days"] = [
        {
            "id": "day-check",
            "intervals": [
                {
                    "id": "late-visit",
                    "start": "2026-11-02T10:15:00+09:00",
                    "end": "2026-11-02T12:30:00+09:00",
                    "operating_start": "2026-11-02T10:30:00+09:00",
                    "operating_end": "2026-11-02T12:00:00+09:00",
                    "last_admission_at": "2026-11-02T10:00:00+09:00",
                    "last_service_at": "2026-11-02T10:10:00+09:00",
                },
                {
                    "id": "unknown-hours",
                    "start": "2026-11-02T13:00:00+09:00",
                    "end": "2026-11-02T14:00:00+09:00",
                },
            ],
        }
    ]

    codes = [finding.code for finding in run_checks(state).findings]

    assert codes == [
        "CALENDAR_LAST_ADMISSION",
        "CALENDAR_LAST_SERVICE",
        "CALENDAR_OUTSIDE_OPERATING_WINDOW",
    ]


def test_calendar_reports_incomparable_explicit_cutoff_instead_of_crashing(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary["days"] = [
        {
            "id": "day-check",
            "intervals": [
                {
                    "id": "mixed-timezone",
                    "start": "2026-11-02T10:15:00+09:00",
                    "end": "2026-11-02T11:15:00+09:00",
                    "operating_start": "2026-11-02T10:00:00",
                }
            ],
        }
    ]

    report = run_checks(state)

    assert [finding.code for finding in report.findings] == [
        "CALENDAR_TIMESTAMP_INVALID"
    ]


def test_explicit_door_to_door_connection_and_buffer_shortfalls_are_blocking(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary["legs"] = [
        {
            "id": "leg-tight",
            "components": {"walk": 10, "platform": 5, "ride": 20},
            "allocated_minutes": 30,
            "required_buffers": ["security", "station"],
            "buffer_markers": ["station"],
        }
    ]
    state.itinerary["connections"] = [
        {"id": "connection-tight", "available_minutes": 12, "minimum_minutes": 15}
    ]

    findings = run_checks(state).findings

    assert [finding.code for finding in findings] == [
        "BUFFER_DOOR_TO_DOOR_SHORTFALL",
        "BUFFER_MARKER_MISSING",
        "CONNECTION_MINIMUM_SHORTFALL",
    ]
    assert all(finding.severity == "blocking" for finding in findings)


def test_reference_and_overnight_links_must_resolve_to_canonical_ids(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary.update(
        {
            "alternatives": [{"id": "route-known"}],
            "selected_route_id": "route-missing",
            "nights": [{"id": "night-known"}],
            "days": [
                {
                    "id": "day-known",
                    "route_id": "route-missing",
                    "readiness_ids": ["ready-missing"],
                    "source_ids": ["source-missing"],
                    "claim_ids": ["claim-missing"],
                }
            ],
            "legs": [
                {
                    "id": "leg-night",
                    "day_id": "day-missing",
                    "dependency_ids": ["ready-missing"],
                    "overnight": True,
                    "night_id": "night-missing",
                }
            ],
        }
    )
    state.readiness["items"] = [
        {
            "id": "ready-known",
            "category": "transport",
            "status": "action_needed",
            "dependencies": ["ready-missing"],
            "source_ids": ["source-missing"],
            "claim_ids": ["claim-missing"],
        }
    ]

    report = run_checks(state)
    codes = [finding.code for finding in report.findings]

    assert codes.count("LINK_ROUTE_NOT_FOUND") == 2
    assert codes.count("LINK_DAY_NOT_FOUND") == 1
    assert codes.count("LINK_READINESS_NOT_FOUND") == 3
    assert codes.count("LINK_SOURCE_NOT_FOUND") == 2
    assert codes.count("LINK_CLAIM_NOT_FOUND") == 2
    assert codes.count("LINK_OVERNIGHT_STAY_NOT_FOUND") == 1

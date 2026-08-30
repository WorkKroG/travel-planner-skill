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
            "alternatives": [],
            "route_stops": [],
            "days": [],
            "budget_items": [],
            "budget_summary": None,
        }
    )
    state.readiness["items"] = []
    state.candidates["claims"] = []
    state.candidates["items"] = []
    return state


def test_calendar_uses_canonical_timeline_and_detects_cross_day_overlap(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary["days"] = [
        {
            "id": "day-one",
            "timeline": [
                {
                    "id": "overnight-ride",
                    "time": "23:30",
                    "title": "Overnight ride",
                    "detail": "Arrives after midnight.",
                    "start_at": "2026-11-02T23:30:00+09:00",
                    "end_at": "2026-11-03T01:00:00+09:00",
                }
            ],
        },
        {
            "id": "day-two",
            "timeline": [
                {
                    "id": "early-transfer",
                    "time": "00:30",
                    "title": "Early transfer",
                    "detail": "Overlaps the inbound ride.",
                    "start_at": "2026-11-03T00:30:00+09:00",
                    "end_at": "2026-11-03T01:30:00+09:00",
                }
            ],
        },
    ]

    report = run_checks(state)

    overlap = next(
        finding for finding in report.findings if finding.code == "CALENDAR_INTERVAL_OVERLAP"
    )
    assert overlap.path == "itinerary.yaml.days[1].timeline[0]"
    assert overlap.affected_ids == ("overnight-ride", "early-transfer")


def test_calendar_reports_naive_timestamps_instead_of_raising_type_error(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary["days"] = [
        {
            "id": "day-one",
            "timeline": [
                {
                    "id": "aware",
                    "time": "09:00",
                    "title": "Aware event",
                    "detail": "Offset is explicit.",
                    "start_at": "2026-11-02T09:00:00+09:00",
                    "end_at": "2026-11-02T10:00:00+09:00",
                },
                {
                    "id": "naive",
                    "time": "09:30",
                    "title": "Naive event",
                    "detail": "Offset is missing.",
                    "start_at": "2026-11-02T09:30:00",
                    "end_at": "2026-11-02T10:30:00",
                },
            ],
        }
    ]

    report = run_checks(state)

    finding = next(
        finding for finding in report.findings if finding.code == "CALENDAR_TIMESTAMP_INVALID"
    )
    assert finding.path == "itinerary.yaml.days[0].timeline[1]"
    assert finding.affected_ids == ("naive",)


def test_calendar_checks_only_structured_operating_and_service_cutoffs(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary["days"] = [
        {
            "id": "day-one",
            "timeline": [
                {
                    "id": "late-visit",
                    "time": "10:15",
                    "title": "Late visit",
                    "detail": "Outside explicit cutoffs.",
                    "start_at": "2026-11-02T10:15:00+09:00",
                    "end_at": "2026-11-02T12:30:00+09:00",
                    "operating_start_at": "2026-11-02T10:30:00+09:00",
                    "operating_end_at": "2026-11-02T12:00:00+09:00",
                    "last_admission_at": "2026-11-02T10:00:00+09:00",
                    "last_service_at": "2026-11-02T10:10:00+09:00",
                },
                {
                    "id": "unknown-hours",
                    "time": "13:00",
                    "title": "Unknown hours",
                    "detail": "No structured cutoff exists.",
                },
            ],
        }
    ]

    assert [finding.code for finding in run_checks(state).findings] == [
        "CALENDAR_LAST_ADMISSION",
        "CALENDAR_LAST_SERVICE",
        "CALENDAR_OUTSIDE_OPERATING_WINDOW",
    ]


def test_timeline_travel_fields_expose_buffer_and_connection_shortfalls(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    state.itinerary["days"] = [
        {
            "id": "day-one",
            "timeline": [
                {
                    "id": "leg-tight",
                    "time": "09:00",
                    "title": "Tight transfer",
                    "detail": "Explicit travel arithmetic.",
                    "allocated_minutes": 30,
                    "components_minutes": {"walk": 10, "platform": 5, "ride": 20},
                    "required_buffer_markers": ["security", "station"],
                    "buffer_markers": ["station"],
                    "connection": {"available_minutes": 12, "minimum_minutes": 15},
                }
            ],
        }
    ]

    assert [finding.code for finding in run_checks(state).findings] == [
        "BUFFER_DOOR_TO_DOOR_SHORTFALL",
        "BUFFER_MARKER_MISSING",
        "CONNECTION_MINIMUM_SHORTFALL",
    ]


def test_canonical_references_resolve_and_array_findings_include_the_index(
    japan_state: TripState,
) -> None:
    state = _state(japan_state)
    source_id = state.candidates["sources"][0]["id"]
    state.itinerary.update(
        {
            "alternatives": [{"id": "route-known"}],
            "selected_route_id": "route-known",
            "route_stops": [{"id": "stop-known"}],
            "days": [
                {
                    "id": "day-known",
                    "route_id": "route-known",
                    "overnight": "Tokyo",
                    "overnight_stop_id": "stop-missing",
                    "readiness_ids": ["ready-known", "ready-missing"],
                    "source_ids": [source_id, "source-missing"],
                    "claim_ids": ["claim-missing"],
                    "timeline": [
                        {
                            "id": "leg-known",
                            "time": "09:00",
                            "title": "Transfer",
                            "detail": "Canonical nested leg.",
                            "readiness_ids": ["ready-missing"],
                        }
                    ],
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
        }
    ]

    report = run_checks(state)

    missing_ready = [
        finding for finding in report.findings if finding.code == "LINK_READINESS_NOT_FOUND"
    ]
    assert {finding.path for finding in missing_ready} == {
        "itinerary.yaml.days[0].readiness_ids[1]",
        "itinerary.yaml.days[0].timeline[0].readiness_ids[0]",
        "readiness.yaml.items[0].dependencies[0]",
    }
    assert any(
        finding.code == "LINK_OVERNIGHT_STAY_NOT_FOUND"
        and finding.path == "itinerary.yaml.days[0].overnight_stop_id"
        for finding in report.findings
    )

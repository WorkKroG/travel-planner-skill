import shutil
from pathlib import Path

import pytest
import yaml
from travel_planner import state as state_module
from travel_planner.cli import main
from travel_planner.state import (
    STATE_SCHEMA_FILES,
    load_trip,
    validate_trip,
    write_state_file,
)


@pytest.fixture
def minimal_trip(tmp_path: Path) -> Path:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-trip"
    target = tmp_path / "minimal-trip"
    shutil.copytree(source, target)
    return target


def _write_lifecycle(
    root: Path,
    *,
    document_status: object = "draft",
    verification_level: object = "none",
    finalization_basis: object = None,
    accepted_blockers: object = None,
) -> None:
    data = yaml.safe_load((root / "itinerary.yaml").read_text())
    data.update(
        {
            "document_status": document_status,
            "verification_level": verification_level,
            "finalization_basis": finalization_basis,
            "accepted_blockers": [] if accepted_blockers is None else accepted_blockers,
        }
    )
    write_state_file(root / "itinerary.yaml", data)


def test_four_structured_files_validate_with_canonical_lifecycle_fields(
    minimal_trip: Path,
) -> None:
    """Catch a schema or fixture bundle that omits the approved itinerary lifecycle."""
    assert tuple(STATE_SCHEMA_FILES) == (
        "brief.yaml",
        "candidates.yaml",
        "itinerary.yaml",
        "readiness.yaml",
    )
    itinerary = load_trip(minimal_trip).itinerary
    expected_lifecycle = {
        "document_status": "draft",
        "verification_level": "none",
        "finalization_basis": None,
        "accepted_blockers": [],
    }
    assert {key: itinerary.get(key) for key in expected_lifecycle} == expected_lifecycle
    assert validate_trip(minimal_trip).ok is True


@pytest.mark.parametrize(
    "relative_root",
    [
        "tests/fixtures/minimal-trip",
        "tests/fixtures/japan-reference",
        "tests/fixtures/japan-final-reference",
        "examples/japan-autumn-2026",
    ],
)
def test_repository_trip_bundles_match_all_four_schemas(relative_root: str) -> None:
    """Catch a committed example or reference bundle drifting behind the state contract."""
    repository_root = Path(__file__).parents[2]
    schema_root = repository_root / "skills" / "travel-planner" / "schemas"

    assert {path.name for path in schema_root.glob("*.schema.json")} == set(
        STATE_SCHEMA_FILES.values()
    )
    assert validate_trip(repository_root / relative_root).ok is True


def test_itinerary_accepts_typed_event_context_and_full_scenario_timeline(
    minimal_trip: Path,
) -> None:
    """Catch the schema rejecting the readable-day event and scenario contract."""
    brief = yaml.safe_load((minimal_trip / "brief.yaml").read_text())
    brief["document_language"] = "ru"
    write_state_file(minimal_trip / "brief.yaml", brief)
    itinerary = yaml.safe_load((minimal_trip / "itinerary.yaml").read_text())
    itinerary["days"] = [
        {
            "id": "day-one",
            "timeline": [
                {
                    "id": "event-transfer",
                    "kind": "transport",
                    "time": "09:00",
                    "title": "Train",
                    "detail": "Travel to the next district.",
                    "links": [
                        {
                            "label": "Build route",
                            "url": "https://maps.example/route",
                            "kind": "route",
                            "requires_internet": True,
                        }
                    ],
                    "alternatives": [
                        {
                            "id": "event-transfer-bus",
                            "title": "Bus",
                            "reason": "Use when the train is disrupted.",
                            "detail": "Direct local bus.",
                            "price": "Approx. JPY 500",
                            "effort": "low",
                            "distance": "8 km",
                            "booking": "No reservation",
                            "links": [
                                {
                                    "label": "Open on map",
                                    "url": "https://maps.example/bus",
                                    "kind": "map",
                                    "requires_internet": True,
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "event-lunch",
                    "kind": "meal",
                    "time": "12:30",
                    "title": "Lunch",
                    "detail": "Eat near the next stop.",
                },
                {
                    "id": "event-check",
                    "kind": "checkpoint",
                    "time": "14:00",
                    "title": "Weather check",
                    "detail": "Decide before leaving the station.",
                    "checkpoint": {
                        "check": "Confirm the rain warning.",
                        "adjust_plan": "Use the indoor scenario.",
                    },
                },
            ],
            "scenarios": [
                {
                    "id": "rain",
                    "label": "Rain",
                    "summary": "Replace the outdoor half of the day.",
                    "timeline": [
                        {
                            "id": "event-rain-museum",
                            "kind": "activity",
                            "time": "15:00",
                            "title": "Museum",
                            "detail": "Stay indoors.",
                        }
                    ],
                }
            ],
        }
    ]
    write_state_file(minimal_trip / "itinerary.yaml", itinerary)

    assert validate_trip(minimal_trip).ok is True


@pytest.mark.parametrize(
    "event",
    [
        {
            "id": "missing-kind",
            "time": "09:00",
            "title": "Untyped",
            "detail": "An event needs a type.",
        },
        {
            "id": "bad-checkpoint",
            "kind": "checkpoint",
            "time": "09:00",
            "title": "Decide",
            "detail": "Missing the adjustment contract.",
            "checkpoint": {"check": "Check conditions."},
        },
        {
            "id": "bad-link",
            "kind": "activity",
            "time": "09:00",
            "title": "Visit",
            "detail": "Unsafe action URL.",
            "links": [
                {
                    "label": "Open",
                    "url": "http://example.test/place",
                    "kind": "map",
                    "requires_internet": True,
                }
            ],
        },
    ],
)
def test_typed_timeline_event_rejects_an_incomplete_contract(
    minimal_trip: Path, event: dict[str, object]
) -> None:
    """Catch ambiguous events, checkpoints or unsafe contextual actions."""
    itinerary = yaml.safe_load((minimal_trip / "itinerary.yaml").read_text())
    itinerary["days"] = [{"id": "day-one", "timeline": [event]}]
    write_state_file(minimal_trip / "itinerary.yaml", itinerary)

    assert validate_trip(minimal_trip).ok is False


def test_alternative_day_scenario_requires_a_label_and_nonempty_timeline(
    minimal_trip: Path,
) -> None:
    """Catch a description-only scenario that cannot replace the visible day plan."""
    itinerary = yaml.safe_load((minimal_trip / "itinerary.yaml").read_text())
    itinerary["days"] = [
        {
            "id": "day-one",
            "timeline": [],
            "scenarios": [{"id": "rain", "summary": "No actual alternative events."}],
        }
    ]
    write_state_file(minimal_trip / "itinerary.yaml", itinerary)

    assert validate_trip(minimal_trip).ok is False


@pytest.mark.parametrize(
    "field",
    ["document_status", "verification_level", "finalization_basis", "accepted_blockers"],
)
def test_itinerary_lifecycle_fields_are_required(minimal_trip: Path, field: str) -> None:
    """Catch lifecycle fields becoming optional and silently disappearing from a trip."""
    itinerary = yaml.safe_load((minimal_trip / "itinerary.yaml").read_text())
    del itinerary[field]
    write_state_file(minimal_trip / "itinerary.yaml", itinerary)

    report = validate_trip(minimal_trip)

    assert report.ok is False
    assert report.issues[0].path == "itinerary.yaml"
    assert f"'{field}' is a required property" in report.issues[0].message


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("document_status", "published"),
        ("verification_level", "human_reviewed"),
        ("finalization_basis", "automatic"),
    ],
)
def test_invalid_lifecycle_value_reports_exact_field_path(
    minimal_trip: Path, field: str, invalid: str
) -> None:
    """Catch lifecycle enum diagnostics that point only at the itinerary root."""
    _write_lifecycle(minimal_trip, **{field: invalid})

    report = validate_trip(minimal_trip)

    assert report.ok is False
    assert [issue.path for issue in report.issues] == [f"itinerary.yaml.{field}"]


@pytest.mark.parametrize(
    ("document_status", "verification_level", "finalization_basis"),
    [
        ("final", "none", None),
        ("draft", "ai_reviewed", "user_confirmed"),
    ],
)
def test_schema_does_not_encode_lifecycle_cross_field_rules(
    minimal_trip: Path,
    document_status: str,
    verification_level: str,
    finalization_basis: str | None,
) -> None:
    """Catch JSON Schema taking over finalization semantics reserved for hard checks."""
    _write_lifecycle(
        minimal_trip,
        document_status=document_status,
        verification_level=verification_level,
        finalization_basis=finalization_basis,
    )

    assert validate_trip(minimal_trip).ok is True


@pytest.mark.parametrize(
    "missing_field",
    ["blocker_id", "accepted_by_user", "accepted_at", "rationale"],
)
def test_accepted_blocker_requires_an_explicit_auditable_record(
    minimal_trip: Path, missing_field: str
) -> None:
    """Catch blocker acceptance records that cannot prove what the user accepted and why."""
    acceptance = {
        "blocker_id": "blocker-rail",
        "accepted_by_user": True,
        "accepted_at": "2026-08-30T09:00:00+00:00",
        "rationale": "The user accepts the remaining timetable uncertainty.",
    }
    del acceptance[missing_field]
    _write_lifecycle(minimal_trip, accepted_blockers=[acceptance])

    report = validate_trip(minimal_trip)

    assert report.ok is False
    issue = report.issues[0]
    assert issue.path == "itinerary.yaml.accepted_blockers[0]"
    assert f"'{missing_field}' is a required property" in issue.message


def test_accepted_blocker_rejects_invalid_accepted_at_timestamp(
    minimal_trip: Path,
) -> None:
    """Catch an unauditable acceptance timestamp passing structural validation."""
    _write_lifecycle(
        minimal_trip,
        accepted_blockers=[
            {
                "blocker_id": "blocker-rail",
                "accepted_by_user": True,
                "accepted_at": "definitely-not-a-timestamp",
                "rationale": "The user accepts the remaining timetable uncertainty.",
            }
        ],
    )

    report = validate_trip(minimal_trip)

    assert report.ok is False
    assert report.issues[0].path == "itinerary.yaml.accepted_blockers[0].accepted_at"


@pytest.mark.parametrize(
    ("field", "invalid"),
    [("accepted_by_user", False), ("rationale", "   ")],
)
def test_accepted_blocker_rejects_empty_acceptance(
    minimal_trip: Path, field: str, invalid: object
) -> None:
    """Catch a false marker or blank rationale masquerading as user acceptance."""
    acceptance = {
        "blocker_id": "blocker-rail",
        "accepted_by_user": True,
        "accepted_at": "2026-08-30T09:00:00+00:00",
        "rationale": "The user accepts the remaining timetable uncertainty.",
    }
    acceptance[field] = invalid
    _write_lifecycle(minimal_trip, accepted_blockers=[acceptance])

    report = validate_trip(minimal_trip)

    assert report.ok is False
    assert report.issues[0].path == f"itinerary.yaml.accepted_blockers[0].{field}"


def test_user_acceptance_keeps_the_original_blocker_unresolved_and_visible(
    minimal_trip: Path,
) -> None:
    """Catch acceptance being represented by mutating or removing the source blocker."""
    itinerary = yaml.safe_load((minimal_trip / "itinerary.yaml").read_text())
    itinerary["challenge_findings"] = [
            {
                "id": "blocker-rail",
                "code": "SCHEDULE_UNRELEASED",
                "severity": "blocking",
                "status": "unresolved",
                "path": "itinerary.yaml.days[0]",
                "affected_ids": ["day-1"],
                "message": "The final timetable is not released.",
            }
    ]
    write_state_file(minimal_trip / "itinerary.yaml", itinerary)
    _write_lifecycle(
        minimal_trip,
        document_status="final",
        verification_level="ai_reviewed",
        finalization_basis="user_confirmed",
        accepted_blockers=[
            {
                "blocker_id": "blocker-rail",
                "accepted_by_user": True,
                "accepted_at": "2026-08-30T09:00:00+00:00",
                "rationale": "The user accepts the published-schedule risk.",
            }
        ],
    )

    assert validate_trip(minimal_trip).ok is True
    reloaded = load_trip(minimal_trip).itinerary
    assert reloaded["challenge_findings"][0]["status"] == "unresolved"
    assert reloaded["accepted_blockers"][0]["blocker_id"] == "blocker-rail"


def test_schema_only_validation_does_not_apply_cross_file_trip_id_rule(
    minimal_trip: Path,
) -> None:
    """Catch the four per-file schemas being presented as cross-file validation."""
    validate_structure = getattr(state_module, "validate_structure", None)
    assert callable(validate_structure)
    readiness = yaml.safe_load((minimal_trip / "readiness.yaml").read_text())
    readiness["trip_id"] = "another-trip"
    write_state_file(minimal_trip / "readiness.yaml", readiness)

    assert validate_structure(minimal_trip).ok is True
    trip_report = validate_trip(minimal_trip)
    assert trip_report.ok is False
    assert trip_report.issues[0].path == "readiness.yaml.trip_id"


def test_generated_paths_are_not_required_for_load_or_structural_validation(
    minimal_trip: Path,
) -> None:
    """Catch generated reports or outputs becoming hidden canonical validation inputs."""
    validate_structure = getattr(state_module, "validate_structure", None)
    assert callable(validate_structure)
    shutil.rmtree(minimal_trip / "outputs", ignore_errors=True)

    assert load_trip(minimal_trip).itinerary["document_status"] == "draft"
    assert validate_structure(minimal_trip).ok is True


def test_unknown_readiness_status_reports_exact_path(minimal_trip: Path) -> None:
    """Catch invalid readiness state without forcing the user to hunt for its field."""
    data = yaml.safe_load((minimal_trip / "readiness.yaml").read_text())
    data["items"] = [{"id": "ready-1", "status": "done-ish", "category": "entry"}]
    write_state_file(minimal_trip / "readiness.yaml", data)

    report = validate_trip(minimal_trip)

    assert report.ok is False
    assert report.issues[0].path == "readiness.yaml.items[0].status"


def test_candidate_keeps_evidence_popularity_assessment_and_verdict_separate(
    minimal_trip: Path,
) -> None:
    """Catch a candidate model that turns popularity or opinion into a fact."""
    candidate = load_trip(minimal_trip).candidates["items"][0]

    assert {"claims", "popularity_signals", "assessments", "verdict"} <= candidate.keys()
    assert candidate["verdict"] not in candidate["claims"]


def test_write_state_file_preserves_mapping_order_and_valid_yaml(minimal_trip: Path) -> None:
    """Catch an atomic writer that reshuffles human-edited state or emits broken YAML."""
    path = minimal_trip / "readiness.yaml"
    value = {"schema_version": 1, "trip_id": "minimal-trip", "items": []}

    write_state_file(path, value)

    assert list(yaml.safe_load(path.read_text()).keys()) == ["schema_version", "trip_id", "items"]
    assert path.read_text().splitlines()[0] == "schema_version: 1"


def test_check_cli_reports_file_and_field_for_corrupt_state(
    minimal_trip: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch validation diagnostics that are unusable from a terminal or Codex."""
    data = yaml.safe_load((minimal_trip / "itinerary.yaml").read_text())
    data["route_state"] = "almost-final"
    write_state_file(minimal_trip / "itinerary.yaml", data)

    exit_code = main(["check", str(minimal_trip)])

    assert exit_code == 2
    assert "itinerary.yaml.route_state" in capsys.readouterr().out

"""Run the copyable field-recording example through the actual bundle and HTML path."""

import os
import re
from copy import deepcopy
from html import unescape
from pathlib import Path

import pytest
import yaml
from travel_planner.cli import main
from travel_planner.state import load_trip, write_state_file
from travel_planner.workspace import initialize_trip

DEFAULT_SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills/travel-planner"


def _recording_example(required_files=None):
    if required_files is None:
        required_files = {"itinerary.yaml", "readiness.yaml", "candidates.yaml"}
    planning = (
        Path(os.environ.get("TRAVEL_PLANNER_SKILL_ROOT", DEFAULT_SKILL_ROOT))
        / "references/planning.md"
    )
    examples = [
        yaml.safe_load(block)
        for block in re.findall(r"```yaml\n(.*?)\n```", planning.read_text(), re.DOTALL)
    ]
    bundles = [
        example for example in examples
        if isinstance(example, dict)
        and required_files <= example.keys()
    ]
    assert len(bundles) == 1, "Provide one executable example of the event field contract."
    return deepcopy(bundles[0])


def _visible_text(fragment):
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


@pytest.mark.parametrize("scenario", [False, True], ids=["primary", "full-scenario"])
def test_documented_event_data_reaches_the_reader(tmp_path, capsys, scenario):
    """A copyable example must preserve its times, booking, uncertainty and alternatives."""
    fragments = _recording_example()
    root = tmp_path / "trip"
    initialize_trip(root, "Recording example", "recording-example")
    state = load_trip(root)
    day = fragments["itinerary.yaml"]["days"][0]
    if scenario:
        day["scenarios"] = [{
            "id": "alternative-day", "label": "Alternative day", "timeline": day["timeline"],
        }]
        day["timeline"] = [{
            "id": "rest-day", "kind": "rest", "title": "Rest", "detail": "Stay at the hotel.",
        }]

    # The example contains additions to initialized files, not a second bundle format.
    for filename, additions in fragments.items():
        data = getattr(state, filename.removesuffix(".yaml"))
        for key, records in additions.items():
            data.setdefault(key, []).extend(records)
        write_state_file(root / filename, data)

    before = {path.name: path.read_bytes() for path in root.glob("*.yaml")}
    assert main(["check", str(root)]) == 0
    capsys.readouterr()
    output = tmp_path / "itinerary.html"
    assert main([
        "render", str(root), "--output", str(output), "--at", "2026-09-09T12:00:00+00:00",
    ]) == 0
    html = output.read_text()
    days, preparation = html.split('id="preparation"', 1)

    def event_html(event_id):
        return (
            days.split(f'data-event-id="{event_id}"', 1)[1]
            .split('<li class="timeline-event', 1)[0]
        )

    def event_text(event_id):
        return _visible_text(event_html(event_id))

    museum = event_text("museum-visit")
    assert "10:30–12:00, local UTC+03:00" in museum
    assert "Last entry 11:00" in museum
    assert "Not booked; reserve by 18:00 the previous day" in museum
    transfer = event_text("museum-transfer")
    assert "75 minutes door to door" in transfer
    assert "10 min walk + 35 min train + 15 min wait + 15 min bus" in transfer
    assert "Taxi" in transfer and "45 EUR per group" in transfer
    assert "Bus" in transfer and "8 EUR per person" in transfer
    assert "Book the taxi in advance" in transfer
    assert "Ask about nuts before ordering" in event_text("museum-lunch")
    decision = event_text("return-check")
    assert "Return timetable not yet published" in decision
    assert "Check the operator before leaving" in decision
    assert "Take a taxi if no departure is confirmed" in decision
    assert 'href="https://example.org/museum"' in event_html("museum-visit")
    assert 'href="https://example.org/museum-map"' in event_html("museum-visit")
    assert "Reserve the museum visit" in _visible_text(preparation)
    assert "2026-11-13T18:00:00+03:00" in preparation
    assert "Recheck the return timetable" in _visible_text(preparation)
    assert before == {path.name: path.read_bytes() for path in root.glob("*.yaml")}


@pytest.mark.parametrize("scenario", [False, True], ids=["primary", "full-scenario"])
def test_documented_luggage_chain_reaches_the_reader(tmp_path, capsys, scenario):
    """Checkout, bag custody and recovery must survive real validation and rendering."""
    fragments = _recording_example({"brief.yaml", "itinerary.yaml", "readiness.yaml"})
    root = tmp_path / "trip"
    initialize_trip(root, "Luggage example", "luggage-example")
    state = load_trip(root)
    day = fragments["itinerary.yaml"]["days"][0]
    if scenario:
        day["scenarios"] = [{
            "id": "cycling-alternative", "label": "Cycling day", "timeline": day["timeline"],
        }]
        day["timeline"] = [{
            "id": "stay-at-base", "kind": "rest", "title": "Rest", "detail": "Stay at base.",
        }]
    for filename, additions in fragments.items():
        data = getattr(state, filename.removesuffix(".yaml"))
        for key, records in additions.items():
            data.setdefault(key, []).extend(records)
        write_state_file(root / filename, data)

    before = {path.name: path.read_bytes() for path in root.glob("*.yaml")}
    assert main(["check", str(root)]) == 0
    capsys.readouterr()
    output = tmp_path / "luggage.html"
    assert main([
        "render", str(root), "--output", str(output), "--at", "2026-09-10T12:00:00+00:00",
    ]) == 0
    html = output.read_text()
    days, preparation = html.split('id="preparation"', 1)
    expected = {
        "leave-old-hotel": ["Before departure", "early checkout and key handover"],
        "transfer-with-bags": ["one large suitcase and one daypack", "per user"],
        "drop-bags": [
            "before cycling", "Bag drop is not early room access", "acceptance is unconfirmed",
            "Station storage", "Collect here after returning the bicycles",
            "capacity, opening hours and price are unknown",
        ],
        "cycle": ["Daypack only", "storage is still unresolved"],
        "collect-bags": ["After bicycle return", "before storage closes", "detour and queue"],
        "enter-new-hotel": ["Room check-in", "check-in window is unknown"],
    }
    positions = []
    for event_id, required in expected.items():
        marker = f'data-event-id="{event_id}"'
        positions.append(days.index(marker))
        event = _visible_text(days.split(marker, 1)[1].split('<li class="timeline-event', 1)[0])
        for text in required:
            assert text in event, (event_id, text)
    assert positions == sorted(positions)
    assert "Confirm bag drop and collection" in _visible_text(preparation)
    assert "before relying on storage" in _visible_text(preparation)
    assert load_trip(root).itinerary["document_status"] == "draft"
    assert before == {path.name: path.read_bytes() for path in root.glob("*.yaml")}

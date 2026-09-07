import base64
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from decimal import Decimal

import pytest
from travel_planner.checks import run_checks
from travel_planner.cli import main
from travel_planner.state import load_trip, validate_trip, write_state_file


@pytest.fixture
def media_trip(japan_state):
    root = japan_state.root
    (root / "media").mkdir()
    (root / "media/lake.jpg").write_bytes(b"recorded-photo")
    japan_state.itinerary["days"][0]["media"] = [{
        "path": "media/lake.jpg", "mime_type": "image/jpeg", "alt": "Lake beneath mountains",
        "caption": "Lake", "source_id": japan_state.candidates["sources"][0]["id"],
        "attribution": "Example Author", "license": "CC BY 4.0", "width": 1200, "height": 800,
    }]
    write_state_file(root / "itinerary.yaml", japan_state.itinerary)
    return root


def render(root, output):
    return main(["render", str(root), "--output", str(output), "--at", "2026-09-07T12:00:00+00:00"])


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_cli_renders_saved_gallery_after_bundle_move(media_trip, tmp_path, count):
    state = load_trip(media_trip)
    day = state.itinerary["days"][0]
    day["media"] *= count
    write_state_file(media_trip / "itinerary.yaml", state.itinerary)
    moved = tmp_path / "moved-trip"
    shutil.copytree(media_trip, moved)
    before = {p.relative_to(moved): p.read_bytes() for p in moved.rglob("*") if p.is_file()}
    output = tmp_path / "itinerary.html"
    assert render(moved, output) == 0
    first = output.read_bytes()
    assert first.count(b"data:image/jpeg;base64,") == count
    if count:
        assert base64.b64encode(b"recorded-photo") in first
    assert render(moved, output) == 0
    assert output.read_bytes() == first
    assert {p.relative_to(moved): p.read_bytes() for p in moved.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("change", [
    {"alt": " "}, {"caption": ""}, {"license": " "}, {"attribution": ""},
    {"width": 0}, {"height": 1.5}, {"mime_type": "image/svg+xml"}, {"path": ""},
])
def test_schema_rejects_malformed_photo_records(media_trip, change):
    state = load_trip(media_trip)
    state.itinerary["days"][0]["media"][0].update(change)
    write_state_file(media_trip / "itinerary.yaml", state.itinerary)
    report = validate_trip(media_trip)
    assert not report.ok
    assert all("days[0].media[0]" in issue.path for issue in report.issues)


@pytest.mark.parametrize("value", [None, {}, "lake.jpg", [None], [{ }]])
def test_schema_rejects_non_gallery_values(media_trip, value):
    state = load_trip(media_trip)
    state.itinerary["days"][0]["media"] = value
    write_state_file(media_trip / "itinerary.yaml", state.itinerary)
    assert not validate_trip(media_trip).ok


def test_four_photos_fail_before_overwriting_output(media_trip, tmp_path):
    state = load_trip(media_trip)
    state.itinerary["days"][0]["media"] *= 4
    write_state_file(media_trip / "itinerary.yaml", state.itinerary)
    output = tmp_path / "keep.html"
    output.write_text("Keep existing output")
    assert render(media_trip, output) == 2
    assert output.read_text() == "Keep existing output"


def test_integer_dimensions_use_the_schema_integer_semantics(media_trip, tmp_path):
    state = load_trip(media_trip)
    state.itinerary["days"][0]["media"][0]["width"] = Decimal("1200.0")
    write_state_file(media_trip / "itinerary.yaml", state.itinerary)
    assert validate_trip(media_trip).ok
    assert render(media_trip, tmp_path / "integer.html") == 0


def test_photo_source_reference_is_checked(media_trip):
    state = load_trip(media_trip)
    before = deepcopy(state)
    state.itinerary["days"][0]["media"][0]["source_id"] = "missing-source"
    report = run_checks(state)
    assert any(f.code == "LINK_SOURCE_NOT_FOUND" and f.path.endswith("media[0].source_id")
               for f in report.findings)
    assert before.candidates == state.candidates


@pytest.mark.parametrize("path", ["media/missing.jpg", "../outside.jpg", "/tmp/outside.jpg", "https://example.org/image.jpg"])
def test_cli_rejects_missing_or_nonlocal_media_without_writing(media_trip, tmp_path, capsys, path):
    state = load_trip(media_trip)
    state.itinerary["days"][0]["media"][0]["path"] = path
    write_state_file(media_trip / "itinerary.yaml", state.itinerary)
    output = tmp_path / "out.html"
    assert render(media_trip, output) == 2
    assert not output.exists()
    assert "media" in capsys.readouterr().err.lower()


def test_cli_rejects_symlink_escape_and_empty_file(media_trip, tmp_path):
    asset = media_trip / "media/lake.jpg"
    asset.write_bytes(b"")
    assert render(media_trip, tmp_path / "empty.html") == 2
    asset.unlink()
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(b"private data")
    asset.symlink_to(outside)
    assert render(media_trip, tmp_path / "escaped.html") == 2
    assert not (tmp_path / "escaped.html").exists()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO files are POSIX-specific")
def test_cli_rejects_fifo_media_without_waiting_for_a_writer(media_trip, tmp_path):
    asset = media_trip / "media/lake.jpg"
    asset.unlink()
    os.mkfifo(asset)
    output = tmp_path / "fifo.html"
    result = subprocess.run(
        [sys.executable, "-c", ("import sys; from travel_planner.cli import main; "
         "sys.exit(main(sys.argv[1:]))"), "render", str(media_trip), "--output", str(output),
         "--at", "2026-09-07T12:00:00+00:00"],
        capture_output=True, text=True, timeout=3, check=False,
    )
    assert result.returncode == 2
    assert "regular file" in result.stderr
    assert not output.exists()

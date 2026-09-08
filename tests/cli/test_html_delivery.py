"""Trip delivery produces HTML without a separate research-history archive."""

from pathlib import Path

from travel_planner.cli import main
from travel_planner.state import load_trip, write_state_file


def render(trip, output, at="2026-09-08T18:19:57+00:00"):
    return main(["render", str(trip), "--output", str(output), "--at", at])


def test_repeated_delivery_writes_only_html_and_preserves_working_data(minimal_trip, tmp_path):
    state = load_trip(minimal_trip)
    state.candidates["sources"].append({
        "id": "research-only", "url": "https://example.gov/research",
        "source_type": "official", "publisher": "Research authority",
        "retrieved_at": "2026-09-08T12:00:00+00:00",
    })
    write_state_file(minimal_trip / "candidates.yaml", state.candidates)
    originals = {p: p.read_bytes() for p in minimal_trip.iterdir() if p.is_file()}
    output = tmp_path / "delivery/trip.html"

    assert render(minimal_trip, output) == 0
    first = output.read_bytes()
    assert render(minimal_trip, output) == 0
    assert output.read_bytes() == first
    assert render(minimal_trip, output, "2026-09-08T19:00:00+00:00") == 0
    assert output.read_bytes() != first
    assert list(output.parent.iterdir()) == [output]
    assert not (minimal_trip / "sources.md").exists()
    assert all(p.read_bytes() == original for p, original in originals.items())
    assert "https://example.gov/research" not in output.read_text()


def test_existing_source_files_do_not_block_render_or_get_changed(minimal_trip, tmp_path, capsys):
    output = tmp_path / "delivery/trip.html"
    output.parent.mkdir()
    legacy = minimal_trip / "sources.md"
    legacy.write_text("Earlier user research")
    occupied = output.parent / "sources"
    occupied.write_text("Unrelated file")

    assert render(minimal_trip, output) == 0
    assert legacy.read_text() == "Earlier user research"
    assert occupied.read_text() == "Unrelated file"
    assert set(output.parent.iterdir()) == {output, occupied}
    assert capsys.readouterr().out.strip() == f"Rendered HTML: {output}"


def test_html_publication_failure_keeps_previous_file(minimal_trip, tmp_path, monkeypatch):
    output = tmp_path / "delivery/trip.html"
    output.parent.mkdir()
    output.write_text("previous document")
    replace = Path.replace

    def fail_publication(path, target):
        if target == output:
            raise PermissionError("Simulated HTML publication failure")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_publication)
    assert render(minimal_trip, output) == 2
    assert output.read_text() == "previous document"
    assert list(output.parent.iterdir()) == [output]

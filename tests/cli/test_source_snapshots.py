"""A shared HTML keeps a retrievable, immutable inventory of its actual sources."""

import hashlib
from pathlib import Path

from travel_planner import cli
from travel_planner.cli import main
from travel_planner.state import load_trip, write_state_file


def render(trip, output, at="2026-09-08T12:00:00+00:00"):
    return main(["render", str(trip), "--output", str(output), "--at", at])


def snapshot(output):
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return output.parent / "sources" / f"{digest}.md"


def test_render_archives_all_sources_against_exact_html_without_changing_canonical_files(
    minimal_trip, tmp_path
):
    state = load_trip(minimal_trip)
    state.candidates["sources"].append({
        "id": "unused-source", "url": "https://example.gov/unused",
        "source_type": "official", "publisher": "Unused Authority",
        "retrieved_at": "2026-09-08T12:00:00+00:00",
        "provenance": "Imported; not remotely rechecked.",
    })
    write_state_file(minimal_trip / "candidates.yaml", state.candidates)
    originals = {p: p.read_bytes() for p in minimal_trip.iterdir() if p.is_file()}
    output = tmp_path / "shared.html"
    assert render(minimal_trip, output) == 0
    report = snapshot(output).read_text()
    assert hashlib.sha256(output.read_bytes()).hexdigest() in report
    assert "minimal-trip" in report and "2026-09-08T12:00:00+00:00" in report
    assert "https://example.gov/unused" in report
    assert "Imported; not remotely rechecked." in report
    assert "official-1" in report and "claim-hours" in report
    assert all(p.read_bytes() == original for p, original in originals.items())
    assert "https://example.gov/unused" not in output.read_text()


def test_new_build_keeps_old_snapshot_and_repeat_is_idempotent(minimal_trip, tmp_path):
    output = tmp_path / "trip.html"
    assert render(minimal_trip, output) == 0
    first = snapshot(output)
    content, modified = first.read_bytes(), first.stat().st_mtime_ns
    assert render(minimal_trip, output) == 0
    assert first.stat().st_mtime_ns == modified
    assert render(minimal_trip, output, "2026-09-08T13:00:00+00:00") == 0
    assert snapshot(output) != first
    assert first.read_bytes() == content
    assert len(list((tmp_path / "sources").glob("*.md"))) == 2


def test_changed_technical_evidence_cannot_replace_same_html_snapshot(
    minimal_trip, tmp_path, capsys
):
    output = tmp_path / "trip.html"
    assert render(minimal_trip, output) == 0
    html, report = output.read_bytes(), snapshot(output).read_bytes()
    state = load_trip(minimal_trip)
    state.candidates["sources"][0]["provenance"] = "Different recorded evidence"
    write_state_file(minimal_trip / "candidates.yaml", state.candidates)
    assert render(minimal_trip, output) == 2
    assert "--at" in capsys.readouterr().err
    assert output.read_bytes() == html and snapshot(output).read_bytes() == report


def test_snapshot_failure_does_not_publish_html(minimal_trip, tmp_path, capsys):
    output = tmp_path / "trip.html"
    output.write_text("previous document")
    (tmp_path / "sources").write_text("unrelated file")
    assert render(minimal_trip, output) == 2
    assert output.read_text() == "previous document"
    assert (tmp_path / "sources").read_text() == "unrelated file"
    assert capsys.readouterr().err


def test_snapshot_symlink_is_not_followed(minimal_trip, tmp_path):
    output = tmp_path / "trip.html"
    assert render(minimal_trip, output) == 0
    report = snapshot(output)
    saved = report.read_bytes()
    outside = tmp_path / "unrelated.md"
    outside.write_bytes(saved)
    report.unlink()
    report.symlink_to(outside)
    assert render(minimal_trip, output) == 2
    assert outside.read_bytes() == saved


def test_relocated_bundle_produces_same_html_and_source_snapshot(minimal_trip, tmp_path):
    import shutil

    copied = tmp_path / "relocated"
    shutil.copytree(minimal_trip, copied)
    first, second = tmp_path / "one/trip.html", tmp_path / "two/renamed.html"
    assert render(minimal_trip, first) == render(copied, second) == 0
    assert first.read_bytes() == second.read_bytes()
    assert snapshot(first).read_bytes() == snapshot(second).read_bytes()


def test_html_publication_failure_keeps_previous_file(minimal_trip, tmp_path, monkeypatch):
    output = tmp_path / "trip.html"
    output.write_text("previous document")
    replace = Path.replace

    def fail_publication(path, target):
        if target == output:
            raise PermissionError("Simulated HTML publication failure")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_publication)
    assert render(minimal_trip, output) == 2
    assert output.read_text() == "previous document"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["minimal-trip", "sources", "trip.html"]


def test_canonical_edit_during_render_stops_publication(minimal_trip, tmp_path, monkeypatch):
    output = tmp_path / "trip.html"
    output.write_text("previous document")
    original = cli.render_html

    def edit_during_render(*args, **kwargs):
        state = load_trip(minimal_trip)
        state.candidates["sources"][0]["provenance"] = "Changed while rendering"
        write_state_file(minimal_trip / "candidates.yaml", state.candidates)
        return original(*args, **kwargs)

    monkeypatch.setattr(cli, "render_html", edit_during_render)
    assert render(minimal_trip, output) == 2
    assert output.read_text() == "previous document"
    assert not list((tmp_path / "sources").glob("*.md"))


def test_valid_mixed_yaml_keys_are_preserved_in_source_metadata(minimal_trip, tmp_path):
    state = load_trip(minimal_trip)
    state.candidates["items"][0]["claims"][0]["value"] = {
        2026: "integer-key", "2026": "string-key", "holiday": "closed"
    }
    write_state_file(minimal_trip / "candidates.yaml", state.candidates)
    assert main(["check", str(minimal_trip)]) == 0
    output = tmp_path / "trip.html"
    assert render(minimal_trip, output) == 0
    text = snapshot(output).read_text()
    assert "integer-key" in text and "string-key" in text and "closed" in text
    assert "2026:" in text and "'2026':" in text

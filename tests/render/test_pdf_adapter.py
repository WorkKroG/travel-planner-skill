from datetime import UTC, datetime
from pathlib import Path

import pytest
from travel_planner.challenge import run_challenge
from travel_planner.cli import main
from travel_planner.render.html import DEFAULTS, write_html
from travel_planner.render.pdf import PdfAdapter, PdfResult, render_pdf
from travel_planner.render.qa import QaReport, attest_document, write_attestation
from travel_planner.render.viewmodel import build_view
from travel_planner.state import load_trip


def test_missing_pdf_adapter_returns_html_success_but_not_pdf_success(
    tmp_path: Path, monkeypatch
) -> None:
    """Catch a missing browser being reported as a successfully created PDF."""
    html = tmp_path / "trip.html"
    html.write_text("<!doctype html><title>Trip</title>", encoding="utf-8")
    monkeypatch.setattr(PdfAdapter, "available", lambda self: False)

    result = render_pdf(html, tmp_path / "trip.pdf")

    assert result.created is False
    assert result.code == "PDF_ADAPTER_MISSING"
    assert not (tmp_path / "trip.pdf").exists()


def test_pdf_cli_returns_distinct_failure_when_adapter_is_missing(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Catch automation confusing a valid HTML fallback with PDF success."""
    html = tmp_path / "trip.html"
    html.write_text("<!doctype html><title>Trip</title>", encoding="utf-8")
    monkeypatch.setattr(PdfAdapter, "available", lambda self: False)

    exit_code = main(["pdf", str(html), "--output", str(tmp_path / "trip.pdf")])

    assert exit_code == 4
    assert "PDF_ADAPTER_MISSING" in capsys.readouterr().err


def test_pdf_success_requires_a_nonempty_output_file(tmp_path: Path) -> None:
    """Catch an adapter returning normally without producing a usable PDF."""
    html = tmp_path / "trip.html"
    html.write_text("<!doctype html><title>Trip</title>", encoding="utf-8")

    class EmptyAdapter(PdfAdapter):
        def available(self) -> bool:
            return True

        def create(self, html_path: Path, pdf_path: Path) -> None:
            del html_path, pdf_path

    result = render_pdf(html, tmp_path / "trip.pdf", adapter=EmptyAdapter())

    assert result.created is False
    assert result.code == "PDF_OUTPUT_MISSING"


def test_pdf_adapter_reports_success_only_after_real_file_write(tmp_path: Path) -> None:
    """Catch the success result being disconnected from the filesystem side effect."""
    html = tmp_path / "trip.html"
    html.write_text("<!doctype html><title>Trip</title>", encoding="utf-8")
    pdf = tmp_path / "nested" / "trip.pdf"

    class FileWritingAdapter(PdfAdapter):
        def available(self) -> bool:
            return True

        def create(self, html_path: Path, pdf_path: Path) -> None:
            assert html_path == html
            pdf_path.write_bytes(b"%PDF-1.7\nsynthetic test adapter\n")

    result = render_pdf(html, pdf, adapter=FileWritingAdapter())

    assert result.created is True
    assert result.code == "PDF_CREATED"
    assert result.pdf_path == pdf
    assert pdf.stat().st_size > 0


def _render_final_html(tmp_path: Path) -> Path:
    fixture = Path(__file__).parents[1] / "fixtures" / "japan-final-reference"
    generated_at = datetime(2026, 8, 28, 12, tzinfo=UTC)
    state = load_trip(fixture)
    view = build_view(state, run_challenge(state, "detailed", generated_at), generated_at, qa_attested=True)
    return write_html(view, tmp_path / "trip.html", DEFAULTS)


def _passing_qa_report() -> QaReport:
    return QaReport(
        first_useful_ms=120,
        cumulative_layout_shift=0.01,
        interaction_ms=20,
        focus_visible=True,
        no_js_core=True,
        offline_core=True,
        zoom_200_core=True,
        reduced_motion_core=True,
        filter_sync=True,
        mobile_priority_visible=True,
        state_matrix_complete=True,
    )


def test_pdf_cli_rejects_renderer_final_html_without_a_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch the actual renderer's Final class bypassing its required QA receipt."""
    html = _render_final_html(tmp_path)
    assert "document-status--final" in html.read_text(encoding="utf-8")
    monkeypatch.setattr(
        "travel_planner.cli.render_pdf",
        lambda *args, **kwargs: PdfResult(True, "PDF_CREATED", "synthetic success"),
    )

    exit_code = main(["pdf", str(html), "--output", str(tmp_path / "trip.pdf")])

    assert exit_code == 4
    assert "QA attestation" in capsys.readouterr().err


def test_pdf_cli_rejects_renderer_final_html_after_a_checked_byte_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Catch a valid Final receipt being reused after the rendered artifact is altered."""
    html = _render_final_html(tmp_path)
    write_attestation(html, attest_document(html, _passing_qa_report()))
    html.write_bytes(html.read_bytes() + b" ")
    monkeypatch.setattr(
        "travel_planner.cli.render_pdf",
        lambda *args, **kwargs: PdfResult(True, "PDF_CREATED", "synthetic success"),
    )

    exit_code = main(["pdf", str(html), "--output", str(tmp_path / "trip.pdf")])

    assert exit_code == 4
    assert "QA attestation" in capsys.readouterr().err

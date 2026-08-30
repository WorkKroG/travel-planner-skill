from pathlib import Path

from travel_planner.cli import main
from travel_planner.render.pdf import PdfAdapter, render_pdf


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

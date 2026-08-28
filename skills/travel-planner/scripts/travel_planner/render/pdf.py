"""Optional Playwright PDF adapter with explicit degraded outcomes."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PdfResult:
    created: bool
    code: str
    message: str
    pdf_path: Path | None = None


class PdfAdapter:
    """Thin boundary around the optional Playwright browser runtime."""

    def available(self) -> bool:
        return importlib.util.find_spec("playwright") is not None

    def create(self, html_path: Path, pdf_path: Path) -> None:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(html_path.resolve().as_uri(), wait_until="load")
                page.emulate_media(media="print")
                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                )
            finally:
                browser.close()


def render_pdf(
    html_path: Path,
    pdf_path: Path,
    *,
    adapter: PdfAdapter | None = None,
) -> PdfResult:
    """Render PDF or return a machine-readable reason without overstating success."""
    source = Path(html_path)
    destination = Path(pdf_path)
    if not source.is_file():
        return PdfResult(False, "HTML_NOT_FOUND", f"HTML input does not exist: {source}")
    selected = adapter or PdfAdapter()
    if not selected.available():
        return PdfResult(
            False,
            "PDF_ADAPTER_MISSING",
            "HTML is valid, but the optional Playwright PDF adapter is unavailable.",
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    try:
        selected.create(source, destination)
    except Exception as error:  # noqa: BLE001 - optional adapter boundary must degrade safely
        destination.unlink(missing_ok=True)
        return PdfResult(False, "PDF_RENDER_FAILED", f"PDF rendering failed: {error}")
    if not destination.is_file() or destination.stat().st_size == 0:
        destination.unlink(missing_ok=True)
        return PdfResult(
            False,
            "PDF_OUTPUT_MISSING",
            "The PDF adapter returned without creating a non-empty file.",
        )
    return PdfResult(True, "PDF_CREATED", "PDF created and verified.", destination)

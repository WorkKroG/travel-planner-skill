import json
from pathlib import Path

from travel_planner.render.qa import QaReport, attest_document, run_document_qa


def test_serious_accessibility_finding_blocks_final_status() -> None:
    """Catch Final status ignoring a serious screen-reader or keyboard defect."""
    report = QaReport(accessibility_serious=1)

    assert report.final_allowed is False
    assert "accessibility_serious" in report.blocking_reasons


def test_performance_overflow_and_pdf_failures_are_hard_gates() -> None:
    """Catch measured browser regressions being reduced to informational metrics."""
    report = QaReport(
        horizontal_overflow_count=1,
        first_useful_ms=2500,
        cumulative_layout_shift=0.1,
        interaction_ms=200,
        pdf_failures=1,
        external_asset_requests=1,
        undersized_touch_targets=1,
        filter_sync=False,
        mobile_priority_visible=False,
        state_matrix_complete=False,
    )

    assert report.final_allowed is False
    assert set(report.blocking_reasons) >= {
        "horizontal_overflow",
        "first_useful_screen",
        "layout_shift",
        "interaction_response",
        "pdf_generation",
        "external_assets",
        "touch_targets",
        "filter_sync",
        "mobile_first_view",
        "visual_state_matrix",
    }


def test_clean_report_allows_final_and_preserves_measured_values() -> None:
    """Catch the hard gate rejecting evidence that is strictly inside every threshold."""
    report = QaReport(
        first_useful_ms=2499,
        cumulative_layout_shift=0.099,
        interaction_ms=199,
        focus_visible=True,
        no_js_core=True,
        offline_core=True,
        zoom_200_core=True,
        reduced_motion_core=True,
        filter_sync=True,
        mobile_priority_visible=True,
        state_matrix_complete=True,
        external_asset_requests=0,
        file_size_bytes=46099,
    )

    assert report.final_allowed is True
    assert report.as_dict()["file_size_bytes"] == 46099


def test_run_document_qa_parses_real_runner_output(tmp_path: Path) -> None:
    """Catch the Python gate drifting from the JSON contract emitted by browser QA."""
    html = tmp_path / "trip.html"
    html.write_text("<!doctype html><title>Trip</title>", encoding="utf-8")
    runner = tmp_path / "qa-runner.py"
    runner.write_text(
        "import json\n"
        "print(json.dumps({"
        "'accessibility_critical': 0, 'accessibility_serious': 0, "
        "'horizontal_overflow_count': 0, 'first_useful_ms': 120, "
        "'cumulative_layout_shift': 0, 'interaction_ms': 8, "
        "'focus_visible': True, 'no_js_core': True, 'offline_core': True, "
        "'zoom_200_core': True, 'reduced_motion_core': True, "
        "'external_asset_requests': 0, 'pdf_failures': 0, "
        "'undersized_touch_targets': 0, 'filter_sync': True, "
        "'mobile_priority_visible': True, "
        "'state_matrix_complete': True, "
        "'file_size_bytes': 42, 'errors': []}))\n",
        encoding="utf-8",
    )

    report = run_document_qa(
        html,
        profiles=("phone", "desktop"),
        command=("python3", str(runner)),
    )

    assert report.final_allowed is True
    assert json.loads(json.dumps(report.as_dict()))["first_useful_ms"] == 120


def test_qa_attestation_rejects_changed_html_bytes(tmp_path: Path) -> None:
    """Catch a successful QA result being reused after its approved HTML changes."""
    html = tmp_path / "trip.html"
    html.write_text("<!doctype html><title>Checked trip</title>", encoding="utf-8")
    report = QaReport(
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
    receipt = attest_document(html, report)
    assert receipt.matches(html) is True

    html.write_text("<!doctype html><title>Changed trip</title>", encoding="utf-8")

    assert receipt.matches(html) is False

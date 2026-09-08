# Readable Itinerary Independent Review Remediation Plan

> **Historical plan:** These corrections shipped with readable days in PR #9. See [project status](../../PROJECT_STATUS.md) for subsequent changes and current evidence. The execution steps below record the original review task, not pending work or new authorization.

**Goal:** Resolve every finding from the independent review of `69487cc` and obtain a clean re-review before creating a pull request.

**Architecture:** Keep the canonical trip schema unchanged where it is already valid. Harden only the HTML projection and human release evidence: use progressive enhancement for disclosures and tabs, namespace rendered scenario identities, emit print-readable context and URLs directly in the document, and localize missing date values at the view-model boundary.

**Tech Stack:** Python 3.12, Jinja2, vanilla HTML/CSS/JavaScript, Pytest, Ruff.

**Review baseline:** `69487cc1d5089e0ff8fe77a35ded29299d79cedd`

### Task 1: Capture the seven regressions with tests

**Files:**
- Modify: `tests/render/test_html_no_js.py`
- Modify: `tests/render/test_html_structure.py`
- Modify: `tests/render/test_viewmodel.py`

- [x] Add behavior-level tests for print-visible alternatives, full source/event URLs, event-level print day context, collision-safe scenario IDs, no-JS hidden tab controls, and localized missing Russian dates.
- [x] Run the focused tests and verify each new assertion fails for the intended current behavior.

### Task 2: Harden progressive enhancement and print output

**Files:**
- Modify: `skills/travel-planner/assets/html/itinerary.html.j2`
- Modify: `skills/travel-planner/assets/html/app.js`
- Modify: `skills/travel-planner/assets/html/styles.css`

- [x] Render event alternatives open in the source, collapse them only after successful JavaScript enhancement, and expand/restore them around printing.
- [x] Keep scenario controls hidden until enhancement succeeds and reveal all scenario content on failure.
- [x] Namespace alternative scenario DOM identities so a valid scenario ID such as `primary` cannot collide with the primary panel.
- [x] Print full external URLs and a compact day/date/region context with every event; remove unsupported paged-media string functions.
- [x] Run the focused render tests until green.

### Task 3: Localize incomplete dates and synchronize release evidence

**Files:**
- Modify: `skills/travel-planner/scripts/travel_planner/render/viewmodel.py`
- Modify: `docs/RELEASE_CHECKLIST.md`
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `examples/japan-autumn-2026/outputs/itinerary.html`
- Modify: `tests/render/snapshots/japan.html.sha256`

- [x] Use the active document language for missing start/end date labels.
- [x] Remove the obsolete search observation and describe only supported filter/reset behavior.
- [x] Regenerate the fixed-time Japan artifact and snapshot, then update exact evidence.

### Task 4: Verify, commit, and independently re-review

- [x] Run fresh focused and full Python tests, Ruff, package checks, JavaScript syntax, deterministic rendering, temporary workspace smoke, and diff hygiene.
- [x] Commit the remediation on `codex/readable-itinerary-days`.
- [x] Send the exact new head to an independent review task and wait for a `Ready to merge: Yes` verdict.
- [ ] Only after that verdict, run final exact-head verification, push the feature branch, and create a PR against `main`; never merge it.

# Readable Itinerary Days Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the shared itinerary HTML around readable day chapters, typed event-owned context and complete alternative scenario timelines.

**Architecture:** Keep `days[].timeline` as the canonical primary timeline and add complete alternative timelines under `days[].scenarios[]`. Project both through immutable view-model records into one localized, self-contained Jinja document whose JavaScript changes view state only.

**Tech Stack:** Python 3.12, JSON Schema 2020-12, Jinja2, vanilla HTML/CSS/JavaScript, Pytest, Ruff.

**Spec:** `docs/superpowers/specs/2026-09-06-itinerary-readable-days-design.md`

## Global Constraints

- Preserve the v0.1 boundary: no MCP/backend/apps/accounts/sync, offline workflow, built-in PDF pipeline, migrations/partial rebuild, browser automation stack, or eval runner/judge/simulator.
- Use one shared self-contained HTML template for Codex, Chat/Work and mobile.
- Keep canonical YAML authoritative; HTML interactions never mutate or persist canonical state.
- Preserve incomplete valid drafts and do not invent times, prices, confirmations or source truth.
- Use test-first red/green cycles for every behaviour change.
- Perform one desktop+mobile visual inspection, one batched fix, and at most one confirmation inspection.

---

### Task 1: Canonical contract and reference-check traversal

**Files:**
- Modify: `skills/travel-planner/schemas/brief.schema.json`
- Modify: `skills/travel-planner/schemas/itinerary.schema.json`
- Modify: `skills/travel-planner/scripts/travel_planner/checks.py`
- Modify: `skills/travel-planner/references/planning.md`
- Modify: `skills/travel-planner/references/readiness-and-budget.md`
- Test: `tests/state/test_schema_validation.py`
- Test: `tests/checks/test_calendar_and_links.py`
- Test: `tests/checks/test_identity_and_workspace.py`

**Interfaces:**
- Consumes: existing day, timestamp, ID and canonical-reference checking helpers.
- Produces: `brief.document_language`; typed `timeline_event`; event `links[]`; event `alternatives[]`; alternative day `scenarios[].timeline[]`; checks that visit every scenario event.

- [ ] **Step 1: Write failing schema tests** for a valid typed meal, transport link, checkpoint, event alternative and alternative scenario timeline, plus invalid checkpoint/link/scenario cases.
- [ ] **Step 2: Run focused schema tests and verify the expected schema failures.**
- [ ] **Step 3: Add failing integrity tests** proving duplicate IDs and unresolved canonical references inside alternative scenario timelines are reported with exact paths.
- [ ] **Step 4: Run focused integrity tests and verify the scenario records are currently skipped.**
- [ ] **Step 5: Implement the minimal JSON Schema definitions and flatten primary plus scenario timelines in checks.**
- [ ] **Step 6: Run the focused schema/check tests until green, then update the two runtime authoring references with the exact new contract.**

### Task 2: Localized immutable view model

**Files:**
- Modify: `skills/travel-planner/scripts/travel_planner/render/viewmodel.py`
- Test: `tests/render/test_viewmodel.py`

**Interfaces:**
- Consumes: `brief.document_language`, primary timeline, alternative scenarios and event-owned context from Task 1.
- Produces: immutable `TimelineEventView`, `EventAlternativeView`, `ScenarioView`, `CheckpointView`, `LinkView`, `DayView`, and localized lifecycle/date labels used by the renderer.

- [ ] **Step 1: Write failing view-model tests** that assert event kind, event links, alternative details, checkpoint instructions and complete scenario timelines are preserved without mutating canonical state.
- [ ] **Step 2: Run the focused view-model tests and verify failures name missing fields/types.**
- [ ] **Step 3: Add failing localization tests** for Russian weekday/lifecycle labels and English equivalents selected by `document_language`.
- [ ] **Step 4: Implement the smallest frozen records, timeline projection and two-language lifecycle/date helpers.**
- [ ] **Step 5: Run all view-model tests and refactor only after green.**

### Task 3: Readable semantic HTML and progressive scenario tabs

**Files:**
- Modify: `skills/travel-planner/scripts/travel_planner/render/html.py`
- Modify: `skills/travel-planner/assets/html/itinerary.html.j2`
- Modify: `skills/travel-planner/assets/html/app.js`
- Test: `tests/render/test_html_structure.py`
- Test: `tests/render/test_html_no_js.py`

**Interfaces:**
- Consumes: Task 2 view records and an `en`/`ru` UI-copy catalog.
- Produces: event-owned contextual actions/disclosures; WAI-ARIA scenario tabs; complete no-JS scenario reading order; localized announcements; validated HTTPS links including alternative-owned links.

- [ ] **Step 1: Write failing HTML tests** for one-column contents, day-chapter anatomy, typed events, links inside events, alternatives inside events and absence of legacy Food/Contextual actions/Critical constraints regions.
- [ ] **Step 2: Run the focused structure tests and confirm they fail against the incumbent template.**
- [ ] **Step 3: Write failing no-JS/print tests** proving primary and alternative timelines remain complete, tabs are labelled, and print restores every scenario.
- [ ] **Step 4: Run the no-JS tests and confirm the old description-only scenarios fail.**
- [ ] **Step 5: Rebuild the Jinja template with the approved direction contract as the first body comment and add the localized copy catalog in `html.py`.**
- [ ] **Step 6: Implement tab keyboard/view behaviour and localized filter announcements in `app.js`; keep all content visible before enhancement.**
- [ ] **Step 7: Extend URL validation to scenario events and event alternatives, then run all render tests until green.**

### Task 4: Reading-column visual system and print rules

**Files:**
- Modify: `skills/travel-planner/assets/html/styles.css`
- Test: `tests/render/test_html_structure.py`
- Test: `tests/render/test_html_no_js.py`

**Interfaces:**
- Consumes: semantic classes and ARIA state from Task 3.
- Produces: centred reading column, closed in-flow contents, visually bounded day chapters, strong time column, checkpoint contrast, mobile stacking, reduced motion and compact alternative print treatment.

- [ ] **Step 1: Write failing static CSS contract tests** for no sticky/fixed contents, bounded reading width, chapter boundaries, 44 px controls, timeline transformations, print scenario restoration and page-break safeguards.
- [ ] **Step 2: Run focused CSS tests and verify failure against the sidebar/day-rail layout.**
- [ ] **Step 3: Replace the stylesheet with the minimal complete responsive/print implementation, preserving Mineral and Maple tokens and soft day accents.**
- [ ] **Step 4: Run all render tests and Ruff until green.**

### Task 5: Repository fixtures, example and canonical documentation

**Files:**
- Modify: `skills/travel-planner/assets/trip-template/brief.yaml`
- Modify: `skills/travel-planner/assets/trip-template/itinerary.yaml`
- Modify: `tests/fixtures/japan-reference/brief.yaml`
- Modify: `tests/fixtures/japan-reference/itinerary.yaml`
- Modify: `tests/fixtures/japan-final-reference/brief.yaml`
- Modify: `tests/fixtures/japan-final-reference/itinerary.yaml`
- Modify: `tests/fixtures/minimal-trip/brief.yaml`
- Modify: `examples/japan-autumn-2026/brief.yaml`
- Modify: `examples/japan-autumn-2026/itinerary.yaml`
- Modify: `examples/japan-autumn-2026/outputs/itinerary.html`
- Modify: `PRODUCT.md`
- Modify: `ARCHITECTURE.md`
- Modify: `README.md`
- Modify: `docs/PROJECT_STATUS.md`
- Modify: `tests/render/snapshots/japan.html.sha256`

**Interfaces:**
- Consumes: the new schema, renderer and CLI.
- Produces: valid installable template data, focused English test fixture, Russian reviewable Japan example and synchronized canonical documentation.

- [ ] **Step 1: Update fixtures to the new typed event/scenario contract**, including transport, activity, meal, lodging/rest, checkpoint, event links and event alternatives.
- [ ] **Step 2: Run repository-bundle validation and focused render tests; fix only fixture-contract errors.**
- [ ] **Step 3: Update the bundled template and canonical documents** to describe language selection, event-owned context and alternative scenario timelines without widening v0.1.
- [ ] **Step 4: Render the Japan example at the fixed evaluation time, update the exact reference hash, and prove a second render is byte-identical.**

### Task 6: Bounded design QA, packaging and finish

**Files:**
- Create: `DESIGN.md` only if the finish documenter confirms the existing visual system needs a durable record.
- Modify: changed UI files only for one batched visual-fix pass.

**Interfaces:**
- Consumes: the final generated Japan HTML and all changed files.
- Produces: desktop/mobile QA evidence, detector output, clean-install/package smoke, full verification and one feature commit.

- [ ] **Step 1: Render the committed example into a temporary QA path and inspect desktop plus mobile in one batched browser round.**
- [ ] **Step 2: Apply one batched correction for material defects, then perform at most one confirmation round.**
- [ ] **Step 3: Run the Impeccable detector once over changed HTML/CSS/JS targets and fix mechanical findings without a second detector run.**
- [ ] **Step 4: Run fresh full verification:** `pip check`, `pytest -q`, `ruff check .`, CLI help, exact render/determinism, static HTML/CSS/JS checks, temporary `init/check/render`, clean-install, archive and staged-plugin smokes.
- [ ] **Step 5: Review the final diff against the spec, confirm no unrelated changes or non-goal expansion, stage all intended files and commit once on `codex/readable-itinerary-days`.**
- [ ] **Step 6: Report branch, commit SHA, changed contracts, exact test evidence, reviewable HTML path and honest manual/browser limitations; do not merge.**

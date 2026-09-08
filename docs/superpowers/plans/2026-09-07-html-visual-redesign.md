# HTML visual redesign implementation plan

> **Historical plan:** Implemented in merged PR #10, followed by the day-composition refinement in PR #11. See [project status](../../PROJECT_STATUS.md) for current evidence and [DESIGN.md](../../../DESIGN.md) for the implemented visual system. The execution instructions and checklist below record the original task; they do not authorize new work.

**Goal:** Apply the approved Lemon and Cobalt design to the complete shared HTML and rebuild the actual 2–13 November 2026 Japan trip.

**Architecture:** Retain the existing Python view model, Jinja template, inline CSS/JS and local SVG sprite. Import the reviewed gallery loader and canonical photo records from the explicitly named source worktree. Keep canonical trip content unchanged; presentation belongs to the common renderer.

**Tech stack:** Python 3.12, Jinja2, PyYAML, JSON Schema, pytest, Ruff, ordinary HTML/CSS/JavaScript.

**Spec:** [Approved visual redesign](../specs/2026-09-07-html-visual-redesign-design.md), subordinate to PRODUCT.md and ARCHITECTURE.md.

## Global constraints

- Self-contained artifact, RU/EN, complete no-JS content, native disclosures, existing filters and ARIA scenario tabs.
- No full-text search, new photo research, route changes, duplicate imagery or theme selector.
- No backend/accounts/sync/PDF pipeline/browser automation/migrations/eval runner.
- Preserve all event kinds, owned links, local alternatives, full scenario timelines, unknown values, lifecycle truth and print provenance.
- Galleries: 0 absent; 1 wide; 2 equal; 3 equal; mobile single column. Photo bytes, order, captions, attribution, licenses and source bindings stay intact.
- No browser or capture workaround. Automated checks are source/data evidence; manual visual and print observations remain pending.
- Use temporary directories for command, installation and package smokes. Rebuild the committed example only as the requested deliverable.

## 1. Transfer the gallery implementation and real trip

Files: the inspected tracked source diff, `render/media.py`, three media test modules, the approved spec, and `examples/japan-autumn-2026/media/` (18 JPEGs plus provenance).

- [x] Inspect current/source/parent worktrees, remotes, canonical references and tests. Compare canonical parent data against source after removing gallery additions; they are equal.
- [x] Verify clean baseline with `.venv/bin/python -m pytest -q`.
- [x] Transfer only named implementation files using apply_patch; copy binary JPEGs byte-for-byte. Do not import research, historical checks plans/specs, eval results, node_modules or tests/ui.
- [x] Run the gallery and renderer tests before redesign. Existing media tests establish the inherited behavior and provenance boundary.

## 2. Redesign the shared document

Files: `skills/travel-planner/assets/html/{itinerary.html.j2,styles.css,icons.svg}`, `scripts/travel_planner/render/html.py`, and renderer tests.

- [x] First add failing assertions for gallery placement inside the day header, after the introduction and before metadata/scenarios; update the superseded checkpoint-before-photo assertion while keeping checkpoint-before-affected-event order.

```python
assert day.index('class="day-thesis"') < day.index('class="day-gallery ')
assert day.index('class="day-gallery ') < day.index('class="day-meta"')
assert day.index('class="day-meta"') < day.index('class="scenario-stack"')
```

- [x] Add failing source/semantic checks for the approved palette, gallery aspect ratios, continuous timeline, semantic marker icons and scenario icons. Use synthetic IDs and all six kinds to prevent dependence on fixture IDs/positions. Scenario icons must describe the existing alternate-plan semantics without guessing weather from prose.
- [x] Run focused tests and observe expected failures before changing production markup.
- [x] Rebuild the shared CSS vocabulary: yellow opening fields, cobalt actions, warm paper, sans display, bounded reading column, comfortable controls, clear support sections and semantic states. Keep mobile and print transformations explicit.
- [x] Move existing day gallery markup into the header. Keep one ordered timeline; do not infer phases from ambiguous human labels. Place existing event-kind icons on the continuous line and add locally bundled primary/alternative symbols to scenario controls.
- [x] Run focused tests; adjust only contracts superseded by the approved specification. Existing lifecycle, no-JS, links, escaping, filters, print, unknown-data and localization coverage remains required.

## 3. Rebuild and document the real Japan artifact

Files: `PRODUCT.md`, `ARCHITECTURE.md`, active HTML specs, runtime references, `DESIGN.md`, `docs/PROJECT_STATUS.md`, example README/output and deterministic snapshot.

- [x] Reconcile outdated visual/imagery wording with the new approved spec; preserve historical evidence as historical.
- [x] Render actual example at the recorded deterministic time; update the output and fixture hash after reviewing expected source changes.

```sh
.venv/bin/travel-planner check examples/japan-autumn-2026
.venv/bin/travel-planner render examples/japan-autumn-2026 --output examples/japan-autumn-2026/outputs/itinerary.html --at 2026-09-07T17:44:11+00:00
```

- [x] Verify 12 days, original route/dates, gallery counts `[1,1,2,1,2,2,1,1,2,2,2,1]`, 18 unique unchanged photo digests and exact fixed-time rebuild. Hakone retains two photos; Motosu belongs to day 8.

## 4. Verify, independently review, contribute

- [x] Run fresh `pip check`, full pytest, Ruff, CLI help, JS syntax and `git diff --check`.
- [x] Run clean-install/package, temporary init/check/render and staged-plugin validation smokes. Record any environmental limitation precisely.
- [x] Request an independent code review of the complete final diff, approved spec, real bundle preservation and tests; work on packaging verification while review runs.
- [x] Fix confirmed findings with failing regression tests first, repeat affected/full checks as appropriate, and obtain a final review verdict.
## Contribution handoff

Commit only successful reviewed work, push `codex/html-visual-redesign`, open PR, do not merge. Deliver the PR and absolute Japan HTML path for manual viewing; do not claim browser visual QA.

Implementation evidence: 190 baseline tests; 103 inherited renderer/media checks; new design contracts failed before implementation; final full suite 241 passed. Clean wheel installation and moved-bundle rendering reproduced the output exactly. Independent code review: Ready for PR, no confirmed P0–P3 findings. Independent source-design finish review: Pass with limitations; manual browser/print review remains pending.

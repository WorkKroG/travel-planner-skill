# Travel Planner 0.1.0 release evidence

**Status:** source release candidate; public-directory submission is out of scope

This is a checklist and evidence index, not a runner or an eval framework. Catalog entries remain `not_executed` until their named review or observation is actually performed.

## Automated exact-head gates

Run every command on the final PR head and record the exact commit in the PR body:

The checkmarks below record the PR 7 baseline. The September recorded-data integration reruns the applicable gates on its own exact head; its results belong in that PR. The local 30-attempt research archive is separate evidence and does not validate this integration.

- [x] full Python suite;
- [x] Ruff;
- [x] focused package, skill, catalog, render, and CLI tests;
- [x] skill `quick_validate`;
- [x] `plugin-creator` validation against a staged root named `travel-planner`;
- [x] `pip check`;
- [x] clean Python 3.12 local-helper installation using the README commands;
- [x] temporary-workspace `init`, `check`, and `render` smoke;
- [x] fixed-time Japan byte determinism and committed output/hash checks;
- [x] exactly eight targeted prompts and three release scenarios, both data-only and `not_executed`;
- [x] README links/commands, manifest paths/URLs, repo-wide broken-reference and stale-command scans;
- [x] historical-file deletion, no duplicate normative docs, and no reintroduced Node/Playwright/axe/MCP/backend/PDF/offline/eval framework;
- [x] `git diff --check`, clean worktree, and exact base/head confirmation.

## Historical independent model review

- [x] A separate reviewer evaluated all eight entries in `evals/skill-scenarios.yaml` against their observable invariants.

External evidence recorded 2026-08-30 against exact reviewed head `e3ca14c0951b6e4254932095cfb0fdd361f2de7a`: two-phase blind isolation was preserved, the result was 8/8 Pass, and invariant violations were 0. The implementation owner did not self-grade them. That result does not validate the September changes to the workflow and scenario invariants.

Both catalogs remain data-only with `execution_status: not_executed`. Here `not_executed` means the catalog embeds no runner or result; it does not erase separately recorded external review evidence. Catalog structure tests alone are not execution evidence.

## Local desktop HTML observations

Record date, exact PR head, browser/version, artifact hash, result, and failures for each item. Static source tests do not satisfy this checklist.

- [ ] Search: match, no match, and reset restore the complete itinerary.
- [ ] Every filter—All days, unresolved, weather-sensitive, transfers, warnings—keeps detailed days and overview synchronized; reset works.
- [ ] Contents opens; a section link and day link land without obscured heading or focus.
- [ ] Primary/backup switching works in both directions and announces each state.
- [ ] An induced enhancement failure leaves complete core content, both scenarios, and normal links readable with a concise notice.
- [ ] Opening through `file://` causes no automatic HTTP(S) asset/fetch request; labelled external links are checked separately as user-initiated connectivity actions.
- [ ] 320 px, 390×844, 768×1024, and 1440×900 layouts have no horizontal page scroll or hidden critical content.
- [ ] Keyboard/focus, 200% zoom, reduced motion, contrast, readable typography, and representative Draft/Prepared copy/conflict/stale/media states are reviewed.
- [ ] A4 and Letter print previews keep lifecycle labels, blockers, critical events, sources, and readable pagination.

No screenshots, baselines, device automation, or automated accessibility/layout claims are required or implied.

Availability note (2026-08-30): the available in-app browser rejected the local `file://`
artifact before page load under its URL security policy and prohibited an alternate-browser
workaround. No exact-head desktop observation was therefore performed or marked passed.

## Cross-surface user observations

Exactly two observations belong to the single `cross-surface-portability` release scenario and require a user with access to each surface:

- [ ] Chat web: manually transfer the canonical bundle, continue without claiming local helpers, generate/download/open the shared HTML, and record `none` or explicitly limited `ai_reviewed`.
- [ ] Mobile: manually transfer the canonical bundle, continue without claiming local helpers, download/open the same template, exercise available system print, and record `none` or explicitly limited `ai_reviewed`.

These remain pending until real user evidence is supplied. Neither observation proves Codex validation, automatic synchronization, or universal marketplace availability.

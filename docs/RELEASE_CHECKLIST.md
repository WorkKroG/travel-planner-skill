# Travel Planner 0.1.0 release evidence

**Status:** source release candidate; public-directory submission is out of scope

This is a checklist and evidence index, not a runner or an eval framework. Catalog entries remain `not_executed` until their named review or observation is actually performed.

The current targeted catalog has ten inputs, including user reports, planning estimates and luggage handling on lodging-change days. Historical review of eight inputs below does not validate the added inputs or later revisions. Current implementation checks are recorded in [project status](PROJECT_STATUS.md).

## Compact route navigation

The current compact-route branch removes day-summary duplication and day filtering, while preserving full day chapters, scenario controls, readiness and concerns. The committed Japan example uses the new template; a separate local preview uses the latest Japan data from open PR #19. Full suite: **272 passed**; Ruff, dependency check, CLI help, skill validation, JS syntax and diff whitespace checks passed. A clean wheel installation reproduced the example exactly and matched all HTML assets; temporary init/check/render produce only HTML. Both Japan versions retain all 12 detailed chapters, photos and links, with valid anchor/ARIA/SVG references. Independent review found no P0–P2; P3 documentation findings were corrected. Manual browser/mobile/print checks below remain pending.

## Situation and entry reviews

[PR #15](https://github.com/WorkKroG/travel-planner-skill/pull/15) added two explicit preparation reviews to the workflow and new trip template. Results or unknowns, actual review dates, contextual official links and mandatory recheck instructions remain visible in HTML/print. The Japan example deliberately leaves both reviews unresolved. That revision's full suite: **262 passed**; Ruff, dependency check, CLI help, skill validation and diff whitespace checks passed. Independent review found no actionable P0–P2 issues. A clean wheel installation passed temporary init/check/render smokes, created only HTML, reproduced the Japan output byte-for-byte and matched the installed schema/templates to source. This is not a live assessment of Japan, a visa eligibility check, background monitoring or browser QA.

- [ ] Observe both preparation items in desktop/mobile and print, including “Not checked” and the recheck requirement.
- [ ] In the manual route-building scenario, confirm missing traveller/transit details and unavailable official evidence stay unresolved; a completed review still retains recheck instructions.

## Historical HTML-only delivery verification (PR #14)

[PR #14](https://github.com/WorkKroG/travel-planner-skill/pull/14) merged as `df6bf977705c585f54da96adb8b8ca55ef36820f`, removing separate materials lists and per-build inventories. Delivery is one HTML file; research discussion and citations remain in the available planning conversation. Its full suite: **251 passed**. Ruff, dependency check, CLI help, skill validation and diff whitespace checks passed. Independent source review: ready for PR, no P0–P2 findings; its stale visual-spec wording was corrected. Manual browser/mobile/print gates below remain pending.

The new wheel was built and installed in a clean temporary Python 3.12 environment. Temporary init/check/render smokes produce only HTML, and the installed package reproduces the unchanged Japan HTML byte-for-byte. No sources-report template is packaged.

## Historical layout evidence (PR #11)

[PR #11](https://github.com/WorkKroG/travel-planner-skill/pull/11) merged on 2026-09-08 as `58c20e55fa46307f1b5fa09f96dd7a79f25795d9`. Checks below were performed on its implementation head `4251869c0cf8cf8044ea4abe452ef38e6d878e45` before merging:

- [x] Full Python 3.12 suite: **248 passed**, including package, skill, catalogs, render and CLI contracts.
- [x] Ruff, `pip check`, CLI help, JavaScript syntax and `git diff --check`.
- [x] Skill validation, staged plugin validation and source ZIP smoke in temporary folders.
- [x] Clean wheel build/install, installed asset comparison and temporary `init`, `check`, `render` smokes outside the source tree.
- [x] Fixed-time Japan byte determinism, committed output/hash, all 18 embedded photographs, event order, URLs, IDs and ARIA/SVG/anchor references.
- [x] Independent source review after corrections: no open P0–P2 findings; ready for PR.

The historical PR #11 Japan HTML used `--at 2026-09-07T17:44:11+00:00` and SHA-256 `a348c53562959f4c024ba7036b3d8a49510c4e600400dfe316bd4484d24c1d58`. This is deterministic rendering evidence for that revision, not a fresh check of remote travel facts or a browser observation. Later checks are recorded separately, without relabelling these results as a new full run.

## Historical source-list refinement (PR #13)

[PR #13](https://github.com/WorkKroG/travel-planner-skill/pull/13) merged as `bf8bdf2b5c396eb50fd5a7f061806778e6fa86e8`. Its implementation head `de4e3a5` passed 259 tests, lint/dependency/CLI/JS checks, clean-install reproduction of HTML and source inventory, and independent final review after corrections. Those checks describe the former archive mechanism, which the user's later decision removes. The practical links and HTML remain; the current branch has its own verification above.

## Historical automated baseline (PR #7)

For release verification, run the applicable commands on the final candidate head and record the exact commit and results in the PR body.

The checkmarks below retain the PR #7 baseline. They do not independently validate later changes. The local 30-attempt research archive is separate evidence and does not validate the merged September implementation.

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

- [ ] Route bases appear once with dates/night counts; no repeated day summaries or day filters. Closed contents link by date/place to all day chapters, and the cover link skips directly to them.
- [ ] Open decisions have separate rounded outlines, clear spacing and a full-width next action on desktop/mobile; outlines remain visible in print without background graphics.
- [ ] Contents opens; a section link and day link land without obscured heading or focus.
- [ ] Primary/alternative scenario switching works in both directions, supports Arrow/Home/End keys, and announces each state.
- [ ] An induced enhancement failure leaves complete core content, both scenarios, and normal links readable with a concise notice.
- [ ] Opening through `file://` causes no automatic HTTP(S) asset/fetch request; labelled external links are checked separately as user-initiated connectivity actions.
- [ ] 320 px, 390×844, 768×1024, and 1440×900 layouts have no horizontal page scroll or hidden critical content.
- [ ] Days with 0/1/2/3 photographs retain captions and compact linked creator/license credits without a research list; narrow layouts preserve time/icon/text reading order and scenario controls.
- [ ] Keyboard/focus, 200% zoom, reduced motion, contrast, readable typography, and representative Draft/Prepared copy/conflict/stale/media states are reviewed.
- [ ] A4 and Letter print previews keep lifecycle labels, blockers, critical events, all scenarios, event links and photo credits even when event-alternative disclosures were closed; footer and page counters are checked in the chosen browser.

No screenshots, baselines, device automation, or automated accessibility/layout claims are required or implied.

Availability note (recorded during the September implementation tasks): the available in-app browser rejected the local
`file://` artifact before page load under its URL security policy and prohibited an
alternate-browser workaround. No exact-head desktop or mobile observation was therefore
performed or marked passed.

## Next Codex route test

The [new-chat guide](ROUTE_BUILD_TEST.md) prepares a manual end-to-end route build using a current installed copy or an explicitly selected source checkout. It has not yet been run by the user. Record the tested revision/copy, trip workspace, generated artifact and any failures. This observation does not execute the catalogs or satisfy the separate web/mobile gates below.

## Cross-surface user observations

Exactly two observations belong to the single `cross-surface-portability` release scenario and require a user with access to each surface:

- [ ] Chat web: manually transfer the canonical bundle, continue without claiming local helpers, generate/download/open the shared HTML, and record `none` or explicitly limited `ai_reviewed`.
- [ ] Mobile: manually transfer the canonical bundle, continue without claiming local helpers, download/open the same template, exercise available system print, and record `none` or explicitly limited `ai_reviewed`.

These remain pending until real user evidence is supplied. Neither observation proves Codex validation, automatic synchronization, or universal marketplace availability.

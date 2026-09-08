# Versioned technical sources implementation plan

**Status:** Historical implementation of merged PR #13. Superseded by the later user decision to retain research history in the chat and deliver only HTML with contextual links. Separate source reports and per-build inventories are no longer required; do not execute the tasks below.

**Goal:** Keep research indexes outside the reader's HTML, preserve each build's sources for Codex retrieval, and put practical official/map links beside major program points.

**Authority:** User request of 8 September 2026; PRODUCT.md and ARCHITECTURE.md are amended with this behavior. Earlier requirements for source lists inside HTML are superseded.

**Architecture:** Extend the existing Markdown sources projection and CLI render flow. Store immutable `sources/<HTML-SHA256>.md` beside each output, before publishing HTML. Reject a conflicting snapshot for the same HTML instead of silently replacing historical evidence. Keep five canonical files, optional media, existing schema and three CLI commands. The ordinary `sources.md` remains a rebuildable current-state projection.

**Constraints:** No backend, sync, migration, partial rebuild, browser automation or PDF pipeline. Preserve lifecycle truth, unresolved issues, chronological content, all scenarios, RU/EN, no-JS and print readability. Retain compact photograph attribution beside each image. Unknown venues/operators are not invented to fill link coverage.

## Task 1 — practical event links

- Audit `examples/japan-autumn-2026/itinerary.yaml` across primary and alternative timelines and local substitutions.
- Add official and map/route links for named major stops, venues and transport. Reuse suitable recorded URLs; verify newly introduced official URLs from primary sites. Record new source metadata without promoting existing travel claims.
- Preserve IDs, order, times, prices, decisions and all media. Explain unnamed or unresolved points that cannot receive exact links.
- Limit edits to example itinerary/candidates and a concise link-audit note. Parent regenerates derived artifacts.

## Task 2 — reader HTML and technical build snapshot

- Add failing CLI/evidence tests for complete source inventories, exact HTML hash binding, preservation across builds, deterministic repeat and conflict/write failure behavior.
- Update render tests to require no global/day sources or URL appendix; retain event links, photo credit and lifecycle/version footer.
- Extend `evidence.py`; integrate snapshot creation into `cli.py` before HTML publication. Remove source-list template/CSS/copy; move compact photo credit to captions.
- Update runtime planning/render references and active product, architecture, design and user documentation. Require official and map/route links for concrete major points, with explicit unknowns and no false schema/feasibility claims.

## Integration and review

- Run focused red/green checks, full Python suite, Ruff, pip/CLI/JS checks and temporary package/render smokes appropriate to the changed render flow.
- Regenerate the committed Japan output and current sources projection as requested deliverables, preserving photo bytes. Keep one current committed HTML reference/hash and its matching source snapshot.
- Independently review the complete diff, resolve findings, commit and open a feature PR. Manual browser/mobile/print observations remain pending unless actually performed.

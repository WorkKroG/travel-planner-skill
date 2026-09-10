# Verification, lifecycle, and shared HTML

## Surface routing

| Surface | Deterministic helpers | Allowed verification | Required disclosure | Codex validation gate |
| --- | --- | --- | --- | --- |
| `codex` | `init`, `check`, `render` | `none`, `ai_reviewed`, `codex_validated` | Report recorded-data checks actually run; no feasibility guarantee. | `successful_check`, `valid_recorded_data` |
| `chat_web` | `unavailable` | `none`, `ai_reviewed` | AI-review is `probabilistic` and requires `careful_human_review`. | `never` |
| `mobile` | `unavailable` | `none`, `ai_reviewed` | AI-review is `probabilistic` and requires `careful_human_review`. | `never` |

`chat_web` is the canonical identifier for the ChatGPT Chat/Work web surface.

In Codex, run `check` after substantive canonical changes and before lifecycle changes or rendering:

```bash
travel-planner check PATH
```

Exit 0 means recorded data is internally consistent; 2 means a schema/state error; 3 means an invalid recorded value, unresolved declared reference, duplicate ID, or inconsistent document-status fields. This is the `recorded_data_integrity` scope: dates and their recorded order, explicit references, and valid present money values. It does not compute schedule conflicts, buffer adequacy, source truth, or a general route verdict. Missing facts and saved concerns do not fail the command. It never changes state. Only a real successful Codex check permits `verification_level: codex_validated`; substantive changes require another check before reusing that claim.

On Chat/Work/mobile, use the same canonical workflow but assume no Python, internal helper, account, backend, MCP, filesystem, or synchronization. When useful or requested, perform a clearly labelled probabilistic AI-review, set only `ai_reviewed`, and explain its need for careful human review. Never describe AI-review as schema checking or Codex validation.

## Lifecycle

The user owns document status. New trips and intermediate HTML use `document_status: draft`, `finalization_basis: null`, and the verification actually achieved. Successful checking, a selected route, completion of research, or a request to create, download, print, or share HTML does not authorize `final`. Apply this on every surface. The status describes the document, never confirmation of the trip or acceptance of every risk.

When a route has been selected and a reviewable version is ready for handoff, ask once whether to keep it a draft or finalize it. For example: “Зафиксировать текущую версию как финальную?” Deliver requested draft HTML while that choice is pending. If the user defers or keeps draft, wait for a later readiness signal instead of repeating the question after each edit, check, or export. General approval such as “looks good” or “этот вариант подходит” is a reason to offer the choice, not a finalization instruction.

An explicit request such as “finalize this version”, “оформи итоговую копию”, or a clear choice of final in answer to the status question authorizes `document_status: final`. Do not ask again when that choice is already explicit. Silence, a request for a “готовый HTML”, or acceptance of a particular risk is not a status choice. Before changing status, record the user's choice and its scope in the existing `decisions.md`; no new consent field is required. Then apply the appropriate basis below and the checks required by the current surface. Both bases require the user's finalization choice:

| Final basis | Required state | Remaining blockers |
| --- | --- | --- |
| `codex_validated` | `document_status: final`, `verification_level: codex_validated`, `finalization_basis: codex_validated` after an explicit user finalization choice and a successful recorded-data check | Preserve open decisions, readiness, and saved concerns; no individual risk acceptance is required to prepare the document. |
| `user_confirmed` | `document_status: final`, `finalization_basis: user_confirmed` after an explicit user finalization choice; retain only the verification actually achieved | Use `blocker_id`, `accepted_by_user`, `accepted_at`, `rationale` only if the user separately accepts a risk; such an `optional_record` goes in `itinerary.yaml.accepted_blockers`. `duplicate_forbidden`, `orphan_forbidden`; `acceptance_not_replacement`: retain saved `challenge_findings` as `blocking`, `unresolved`, and `visible`. Other concerns need not be accepted to issue the copy. |

When resuming an existing final version, preserve its recorded status. Typographical or formatting corrections keep `final` and need no new status confirmation; perform the normal checks for the edited data. Before a material revision to route, dates, program, budget, or readiness, prepare a concrete explanation of its effects and propose returning to draft in the same [material-change approval](planning.md#changes-and-day-media). Keep the final canonical plan unchanged while that choice is pending. If the user already specified the status for the revision, honor it without another status question; an explicit choice to keep `final` is allowed. A return to `draft` clears `finalization_basis` to `null`, preserves concerns and the verification actually supported, and is recorded in `decisions.md`. Once a revision is draft, finalizing it requires a new explicit choice for that version.

When the user separately accepts a particular risk, preserve that explicit decision without requiring acceptance of every concern. Replace this optional example ID and rationale with the user's actual acceptance:

```yaml
blocker_id: blocker-rail-timetable
accepted_by_user: true
accepted_at: "2026-08-30T09:00:00+00:00"
rationale: "User accepts the unresolved timetable risk and will recheck it before booking."
```

Acceptance never replaces or deletes a concern, and cannot waive an error in the recorded data. A subset of saved concerns may have acceptance records; duplicate records for one concern and records without a matching saved concern are invalid.

Use `brief.yaml.document_language` (`en` or `ru`) for every renderer-owned label. Display `Prepared copy — checked in Codex` / `Prepared copy — requested by user` in English and `Подготовленная копия — данные проверены в Codex` / `Подготовленная копия — по запросу пользователя` in Russian. Show all saved concerns and concrete open actions. Preparing the document does not resolve or accept them.

Never infer acceptance from silence. `ai_reviewed` never equals `codex_validated`. The renderer copies the recorded document status and concerns; it does not promote source truth, resolve concerns, or invent a trip verdict. Invalid recorded data must be corrected before rendering, while an incomplete but valid draft or prepared copy is allowed.

## Shared HTML and continuation

After review, render one self-contained HTML from the explicit workspace:

```bash
travel-planner render PATH --output PATH/outputs/itinerary.html --at <generation-time-iso8601-with-offset>
```

In Codex, use the bundled helper. Where helpers are unavailable but skill assets can be used, build the downloadable HTML from the same bundled `assets/html/itinerary.html.j2`, `styles.css`, `app.js`, and `icons.svg` with the canonical bundle; do not create a second design. Keep verification `none` or `ai_reviewed`. If the surface cannot create a downloadable file, preserve/update the canonical bundle and state that limitation instead of claiming an HTML exists.

Before rendering, review the official-site and map/route links for every concrete main program point, including alternative scenarios, according to [planning](planning.md). Preserve explicit gaps for unselected or unavailable venues. Do not replace missing practical links with a global source list.

Also review the [event field contract](planning.md#event-field-recording) in the generated HTML: material booking conditions, local times, cutoffs, transport estimates and unresolved facts must be readable in the affected primary/scenario events or local alternatives. Compare these summaries with the current readiness and claim records after changes. A valid timestamp or ID link alone is not reader-visible evidence, and a successful data check does not establish this coverage.

On arrival, lodging-change and final-departure days, trace the [luggage chain](planning.md#lodging-transitions-and-luggage) in that HTML: checkout when applicable, who carries or stores each relevant bag, collection/delivery and onward travel, then room access or departure. Check local fallbacks and full scenarios too. Ensure the reader can see unresolved acceptance, service windows and the time needed for detours; a readiness item alone is insufficient. This is a model review of the plan and its displayed text, not a feasibility check performed by the helper.

Before every delivery, perform the two [situation and entry reviews](research.md) and update their separate [preparation items](readiness-and-budget.md). Ensure the result or unknowns, actual review date when available, applicable official links and explicit recheck requirement remain visible in the HTML and print, even for a previously completed review. If research cannot be completed, deliver an honestly incomplete plan with the missing review/details and next actions; do not silently treat the review as passed. Revisit changed/stale evidence, not just the date field. `check`, `render` and `--at` neither fetch current advisories/visa rules nor monitor future changes.

### Research history and delivery

The HTML is the delivered plan. Important official-site and map/route links belong beside their program points, and compact photo credits remain with images. Neither the screen nor print output contains a research index, day source disclosure or URL appendix.

Do not generate a separate bibliography, materials report, `sources.md`, per-build source snapshot or version-to-source manifest on any surface. The Codex `render` command writes only the requested HTML. `--at` is its generation time, not a freshness check or archive identifier.

Explain research findings and cite sources during the planning conversation. If the user asks how a choice was made, refer to that conversation while it is available. If it is unavailable, say so; do not promise to recover the history from an HTML version or automatically create another research artifact. Canonical source/claim metadata serves current checks and photo attribution, not a history archive.

The HTML is derived and opens locally as a self-contained file. It uses one readable column, a closed native contents disclosure, typed chronological day timelines, event-owned links and alternatives, and complete alternative scenario timelines. Use the shared Lemon and Cobalt visual language: yellow cover/day openings, sans-serif place headings, gallery under the day introduction and above compact facts, cobalt controls, semantic icons on a continuous timeline and blue closing fields. Do not infer day phases from ambiguous labels, add full-text search or depend on host icon globals. JavaScript enhances filtering and scenario tabs; without it all content remains readable. If the user wants a PDF, browser Print → Save as PDF is a manual browser action, not an automated product artifact or guarantee.

### Day photographs

The day header shows photo captions and three facts: overnight base, travel and load. Each caption retains a compact creator credit linked to the photo's source and its recorded license, including in print. Source IDs and recorded metadata remain in the canonical working data; no separate report is produced. The timeline uses a separate circular icon column; on small screens its recorded times move above event text. Optional recorded periods, primary-route labels and semantic icons follow the [planning contract](planning.md).

When suitable photographs are available, record 1–3 per day in `itinerary.yaml.days[].media`, in reading order. Keep one or two when that is all the relevant media; omit the field or use `[]` for no imagery. Do not add decorative duplicates. A caption must identify the location and distinguish an alternative scenario when needed. Each record requires:

```yaml
media:
  - path: media/lake.jpg
    mime_type: image/jpeg
    alt: "Lake beneath autumn woodland and mountain slopes"
    caption: "Lake · primary route"
    source_id: photo-lake
    attribution: "Recorded creator credit"
    license: "Recorded reuse licence"
    width: 1280
    height: 853
```

Replace these illustrative values with actual metadata. `source_id` resolves to a `candidates.yaml.sources` entry with an absolute HTTPS source URL. Preserve original credit, licence or generation provenance; importing metadata from a supplied document does not mean its remote page has been rechecked. Source metadata must state that provenance honestly. Every gallery photo needs nonblank alt text, caption, attribution and licence, plus its positive integer pixel dimensions. Only JPEG, PNG, WebP and AVIF are supported; SVG and remote file paths are not.

Place the raster files beneath the trip's `media/` directory. The helper reads only relative files within that directory, rejects traversal/symlink escapes, and embeds bytes directly; it never fetches an image. `check` validates metadata and source references. `render` also checks local file readability and nonempty content before writing; a missing declared file is an explicit build error, while a day with no media renders normally. Browser decoding failure affects only that photograph and preserves its caption/credit and a localized notice. Where helpers are unavailable, use the same shared template with ordered galleries and inline data URLs; never substitute remote image dependencies.

To continue elsewhere, the user manually transfers the five canonical files, the referenced `media/` directory when present, and may also transfer generated HTML. Do not promise invisible sync, server state, or filesystem access unavailable on that surface.

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

Draft uses `document_status: draft`, `finalization_basis: null`, and the verification actually achieved. A user-requested prepared copy keeps the internal `document_status: final`. Its status describes the document, never confirmation of the trip or acceptance of every risk:

| Final basis | Required state | Remaining blockers |
| --- | --- | --- |
| `codex_validated` | `document_status: final`, `verification_level: codex_validated`, `finalization_basis: codex_validated` after a successful recorded-data check | Preserve open decisions, readiness, and saved concerns; no individual risk acceptance is required to prepare the document. |
| `user_confirmed` | `document_status: final`, `finalization_basis: user_confirmed` after an explicit request for the copy | Use `blocker_id`, `accepted_by_user`, `accepted_at`, `rationale` only if the user separately accepts a risk; such an `optional_record` goes in `itinerary.yaml.accepted_blockers`. `duplicate_forbidden`, `orphan_forbidden`; `acceptance_not_replacement`: retain saved `challenge_findings` as `blocking`, `unresolved`, and `visible`. Other concerns need not be accepted to issue the copy. |

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

### Technical sources by build

The reader's HTML and print output contain no research index, day source disclosure or URL appendix. Practical event links and compact photo attribution stay visible. Tell the organiser in the delivery message that the technical materials list for this version can be requested through Codex; do not add that technical explanation or a report link to the HTML.

The Codex `render` command writes a complete source snapshot to `sources/<HTML-SHA256>.md` next to the requested HTML, then publishes the HTML. The snapshot includes generation time, lifecycle fields, hashes of the five canonical input files, every recorded source (even without a linked claim), claims, readiness references, photographs and event links. `--at` is generation time, not a freshness check. Identical builds reuse the same snapshot; a conflicting existing snapshot stops publication and requires a new generation time. Do not delete prior snapshots during a new build.

To answer “show the sources for this version”, identify the supplied HTML or explicit build first, compute its SHA-256 and read the matching snapshot. Never silently substitute the current `candidates.yaml` or current `sources.md` for a missing historical record. `render_sources_markdown` can rebuild the current-state `sources.md`; it does not reconstruct previous versions. Preserve and transfer saved snapshots when their history is needed.

On a surface without helpers, save a separate materials list with the trip ID and generation time and, where file hashing is available, the HTML SHA-256. If the surface cannot save or bind that list, state the limitation and preserve canonical source records for later Codex use; do not claim an archived version exists.

The HTML is derived and opens locally as a self-contained file. It uses one readable column, a closed native contents disclosure, typed chronological day timelines, event-owned links and alternatives, and complete alternative scenario timelines. Use the shared Lemon and Cobalt visual language: yellow cover/day openings, sans-serif place headings, gallery under the day introduction and above compact facts, cobalt controls, semantic icons on a continuous timeline and blue closing fields. Do not infer day phases from ambiguous labels, add full-text search or depend on host icon globals. JavaScript enhances filtering and scenario tabs; without it all content remains readable. If the user wants a PDF, browser Print → Save as PDF is a manual browser action, not an automated product artifact or guarantee.

### Day photographs

The day header shows photo captions and three facts: overnight base, travel and load. Each caption retains a compact creator credit linked to the photo's source and its recorded license, including in print. Technical source IDs, check dates and research provenance remain in the source snapshot. The timeline uses a separate circular icon column; on small screens its recorded times move above event text. Optional recorded periods, primary-route labels and semantic icons follow the [planning contract](planning.md).

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

To continue elsewhere, the user manually transfers the five canonical files, the referenced `media/` directory when present, and may also transfer generated HTML. Include saved source snapshots to retain access to earlier builds' evidence. Do not promise invisible sync, server state, or filesystem access unavailable on that surface.

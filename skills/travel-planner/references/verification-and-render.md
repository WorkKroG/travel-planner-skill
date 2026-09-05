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

Display `Prepared copy — данные проверены в Codex` for the Codex basis and `Prepared copy — по запросу пользователя` for the user-requested basis. These v0.1 badges use those exact labels; the surrounding planning conversation follows the user's language. Show all saved concerns and concrete open actions. Preparing the document does not resolve or accept them.

Never infer acceptance from silence. `ai_reviewed` never equals `codex_validated`. The renderer copies the recorded document status and concerns; it does not promote source truth, resolve concerns, or invent a trip verdict. Invalid recorded data must be corrected before rendering, while an incomplete but valid draft or prepared copy is allowed.

## Shared HTML and continuation

After review, render one self-contained HTML from the explicit workspace:

```bash
travel-planner render PATH --output PATH/outputs/itinerary.html --at <evaluation-time-iso8601-with-offset>
```

In Codex, use the bundled helper. Where helpers are unavailable but skill assets can be used, build the downloadable HTML from the same bundled `assets/html/itinerary.html.j2`, `styles.css`, `app.js`, and `icons.svg` with the canonical bundle; do not create a second design. Keep verification `none` or `ai_reviewed`. If the surface cannot create a downloadable file, preserve/update the canonical bundle and state that limitation instead of claiming an HTML exists.

The HTML is derived and opens locally as a self-contained file. If the user wants a PDF, browser Print → Save as PDF is a manual browser action, not an automated product artifact or guarantee.

To continue elsewhere, the user manually transfers the five canonical files and may also transfer generated HTML. Do not promise invisible sync, server state, or filesystem access unavailable on that surface.

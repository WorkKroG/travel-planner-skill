# Verification, lifecycle, and shared HTML

## Surface routing

| Surface | Deterministic helpers | Allowed verification | Required disclosure | Codex validation gate |
| --- | --- | --- | --- | --- |
| `codex` | `init`, `check`, `render` | `none`, `ai_reviewed`, `codex_validated` | Report the checks actually run. | `successful_check`, `no_blockers` |
| `chat_work` | `unavailable` | `none`, `ai_reviewed` | AI-review is `less_precise` and requires `careful_human_review`. | `never` |
| `mobile` | `unavailable` | `none`, `ai_reviewed` | AI-review is `less_precise` and requires `careful_human_review`. | `never` |

In Codex, run `check` after substantive canonical changes and before lifecycle changes or rendering:

```bash
travel-planner check PATH
```

Exit 0 means structurally consistent state with no lifecycle inconsistency or unaccepted blockers; 2 means a structural/state error; 3 means lifecycle inconsistency or unaccepted blockers. The command does not change state. Only a real successful Codex check permits `verification_level: codex_validated`.

On Chat/Work/mobile, use the same canonical workflow but assume no Python, internal helper, account, backend, MCP, filesystem, or synchronization. When useful or requested, perform a clearly labelled probabilistic AI-review, set only `ai_reviewed`, and tell the user it is less precise and needs careful human review. Never describe AI-review as schema checking, hard checking, or Codex validation.

## Lifecycle

Draft uses `document_status: draft`, `finalization_basis: null`, and the verification actually achieved. Final state follows this contract:

| Final basis | Required state | Remaining blockers |
| --- | --- | --- |
| `codex_validated` | `document_status: final`, `verification_level: codex_validated`, `finalization_basis: codex_validated` after a successful check | None. |
| `user_confirmed` | `document_status: final`, `finalization_basis: user_confirmed` after an explicit request | For every `actual_blocker_id`, add acceptance metadata `accepted_by_user`, `accepted_at`, and `rationale`; keep it `blocking`, `unresolved`, and `visible` in canonical state and HTML. |

Display `Final — проверено в Codex` only for the Codex basis and `Final — подтверждено пользователем` for explicit user confirmation. Enumerate every remaining blocker and obtain explicit acceptance for each actual blocker ID before recording the user-confirmed basis.

Never infer acceptance from silence. `ai_reviewed` never equals `codex_validated`. The renderer copies lifecycle and findings; it does not decide status, resolve blockers, or invent findings.

## Shared HTML and continuation

After review, render one self-contained HTML from the explicit workspace:

```bash
travel-planner render PATH --output PATH/outputs/itinerary.html --at <evaluation-time-iso8601-with-offset>
```

In Codex, use the bundled helper. Where helpers are unavailable but skill assets can be used, build the downloadable HTML from the same bundled `assets/html/itinerary.html.j2`, `styles.css`, `app.js`, and `icons.svg` with the canonical bundle; do not create a second design. Keep verification `none` or `ai_reviewed`. If the surface cannot create a downloadable file, preserve/update the canonical bundle and state that limitation instead of claiming an HTML exists.

The HTML is derived and opens locally as a self-contained file. If the user wants a PDF, browser Print → Save as PDF is a manual browser action, not an automated product artifact or guarantee.

To continue elsewhere, the user manually transfers the five canonical files and may also transfer generated HTML. Do not promise invisible sync, server state, or filesystem access unavailable on that surface.

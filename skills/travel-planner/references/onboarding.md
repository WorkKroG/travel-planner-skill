# Start or resume a trip

One trip uses one explicit workspace. Resolve the exact path before creating local files. Use a path the user supplied or an unambiguous folder they designated for this trip without asking them to confirm it again. If the user explicitly delegated folder selection within a named project, choose a separate unused trip folder there and state the resolved path. Ask about location only when it is missing, ambiguous, or conflicts with existing files or workspace boundaries. The path must not be the installed skill source or another trip workspace. Initialization never overwrites existing workspace files.

Use the user's title and `trip_id` when supplied. Otherwise choose a concise title in the user's language from known trip details; do not invent dates or a destination to name it. Choose a valid stable ID or let `init` generate it by omitting `--trip-id`. Missing title/ID is not a reason for a confirmation question. Report the chosen name and location briefly, then continue. On resume, reuse the recorded `trip_id`; changing the display title does not change that identity.

In a full local Codex environment, initialize once the location is resolved and authorized:

```bash
travel-planner init PATH --title "TITLE" --confirm-path
```

Add `--trip-id TRIP_ID` when preserving a supplied or explicitly chosen ID. `--confirm-path` records deliberate, authorized path selection; it is not a requirement for a second confirmation exchange and does not create or switch a Codex project. A separate folder/local project is recommended, within the location choice made or delegated by the user.

## Bundle ownership

| Path | Ownership |
| --- | --- |
| `brief.yaml` | canonical |
| `candidates.yaml` | canonical |
| `itinerary.yaml` | canonical |
| `readiness.yaml` | canonical |
| `decisions.md` | canonical |
| `outputs/` | generated |

`brief.yaml` owns goals, travellers, dates, constraints, and preferences. `candidates.yaml` owns researched candidates, sources, claims, and comparisons. `itinerary.yaml` owns the selected route, days/timeline, budget, scenarios, blockers, and lifecycle. `readiness.yaml` owns bookings, actions, rechecks, and dependencies. `decisions.md` preserves the rationale and history of material user decisions. Regenerate HTML from canonical data. Research discussion and citations stay in the chat history; no separate bibliography or build inventory is produced. The canonical files own current editable state, not the conversation history.

The table describes the files created by `init`. If days reference local photographs, their files in `media/` are additional canonical resources. Transfer them with the five canonical files when resuming elsewhere or rebuilding; preserve source, attribution and license metadata. The generated HTML embeds photographs for viewing but does not replace this editable bundle.

Deliver only the HTML, as described in [verification and render](verification-and-render.md). Do not create a source archive or require one to continue the trip. Existing files from earlier installations are not deleted automatically.

To resume, require an explicit path or `trip_id`. If several trips match, ask rather than choosing by recency. Read only the canonical files and IDs relevant to the current request, then follow [verification and render](verification-and-render.md) before editing when deterministic helpers are available.

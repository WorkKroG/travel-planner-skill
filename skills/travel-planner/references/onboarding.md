# Start or resume a trip

One trip uses one explicit workspace. Before creating local files, confirm the exact path, title, and stable `trip_id` with the user. The path must not be the installed skill source or another trip workspace. Initialization never overwrites existing workspace files.

In a full local Codex environment, initialize only after that confirmation:

```bash
travel-planner init PATH --title "TITLE" --trip-id TRIP_ID --confirm-path
```

`--confirm-path` records deliberate path selection; it does not create or switch a Codex project. A separate folder/local project is recommended, but the user chooses it.

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

# Compare, select, detail, and revise

When meaningful choices exist, present up to three genuinely different alternatives in geography, bases, pace, cost, or experience mix. Reject alternatives that violate hard constraints, then compare travel time, lodging changes, physical load, weather resilience, cost basis, and preference fit. If only one route is sensible, explain why.

At each route choice and day decision, connect the fact or unknown to its applicability, consequence, and next action. Assess conflicts in context; the data helper does not decide whether a route works. Retain a conditional alternative when the missing fact could change the choice. Do not request scores, required markers, or invented timestamps just to satisfy a program.

Show trade-offs and a recommendation before asking the user to choose. Record the selected option, rejected alternatives, and reasons in `decisions.md`. Store alternatives and the selection in `itinerary.yaml`; a view-only primary/backup switch in HTML does not alter that selection.

Detail only the chosen route. Use `route_stops` and `days[].timeline[]`; every day and timeline event has an ID. Keep human time labels, and add offset-bearing timestamps, operating/service cutoffs, component durations, connection minimums, and buffer markers only when supported. Link days/events to canonical route, overnight, readiness, source, and claim IDs. Unknown stays unknown.

Apply the same day contract in both cases:

| Day contract applicability |
| --- |
| `initial_detail`, `material_change` |

| Day facet | Required content |
| --- | --- |
| `intent` | State a concise day `thesis`. |
| `summary` | Summarize expected `load` and `travel`. |
| `cutoffs` | Identify supported `critical_cutoffs` and the `latest_switch_point`. |
| `scenarios` | Give the `primary` plan and a `realistic_backup`. |
| `context` | Include relevant `meal` and `booking` context. |
| `evidence` | Attach `linked_sources` and preserve `claim_status`. |
| `transport` | Show segments in `local_time`, cover `door_to_door`, and offer a practical `comfortable_alternative` and `budget_alternative` when choices exist. |

Before editing a material user decision, follow this contract:

| Case | Explain before edit | User gate | Update scope | Record |
| --- | --- | --- | --- | --- |
| `material_change` | `route`, `days`, `budget`, `readiness` | `explicit_consent` | `affected_only` | `decisions.md` |

| Situation | Required outcome |
| --- | --- |
| Restaurant or activity substitution | Explain affected timing, location, booking, cost, and fallback; preserve unrelated days. |
| Russia/CIS/Turkey with auto maps | Use Yandex Maps from the internal provider policy unless the user explicitly chose another provider. |
| Cross-border transport | Label contextual map alternatives, but treat the official operator as authority for schedules and border/check-in rules. |

Maps provide place and route context, never proof of schedules, accessibility, border rules, or travel time. Apply automatic provider selection by the destination/leg ISO country code, not the document language or user location. After a substantive saved change, use the review rules in [verification and render](verification-and-render.md).

# Compare, select, detail, and revise

When meaningful choices exist, present up to three genuinely different alternatives in geography, bases, pace, cost, or experience mix. Reject alternatives that violate hard constraints, then compare travel time, lodging changes, physical load, weather resilience, cost basis, and preference fit. If only one route is sensible, explain why.

At each route choice and day decision, connect the fact or unknown to its applicability, consequence, and next action. Assess conflicts in context; the data helper does not decide whether a route works. Retain a conditional alternative when the missing fact could change the choice. Do not request scores, required markers, or invented timestamps just to satisfy a program.

Show trade-offs and a recommendation before asking the user to choose. Record the selected option, rejected alternatives, and reasons in `decisions.md`. Store alternatives and the selection in `itinerary.yaml`; a view-only scenario switch in HTML does not alter that selection.

Detail only the chosen route. Use `route_stops` and `days[].timeline[]`; every day and timeline event has an ID. The primary timeline is the single chronological plan and each event declares a `kind`: `transport`, `activity`, `meal`, `lodging`, `rest`, or `checkpoint`. Keep human time labels, and add offset-bearing timestamps, operating/service cutoffs, component durations, connection minimums, and buffer markers only when supported. Link days/events to canonical route, overnight, readiness, source, and claim IDs. Unknown stays unknown.

Attach maps, route builders, official pages, tickets, and supporting sources to the event they serve through `timeline[].links[]`. Store a local substitution in the owning event's `alternatives[]`, including the reason to choose it and any known price, effort, distance, booking, or links. Never create an orphan day-level link rail.

Use `days[].scenarios[]` only when a material portion of the day changes. The primary plan remains `days[].timeline`; each alternative scenario records its own stable ID, user-facing label, optional summary, and complete timeline. Do not store fragment-only scenarios or duplicate the primary plan as a scenario.

Represent a real decision moment as a `checkpoint` timeline event with both `checkpoint.check` and `checkpoint.adjust_plan`. Normally use no more than two checkpoints per primary day. Keep ordinary caveats beside their event instead of promoting every uncertainty to a checkpoint.

Apply the same day contract in both cases:

| Day contract applicability |
| --- |
| `initial_detail`, `material_change` |

| Day facet | Required content |
| --- | --- |
| `intent` | State a concise day `thesis`. |
| `summary` | Summarize expected `load` and `travel`. |
| `checkpoints` | Put supported cutoffs and switch decisions in the affected timeline position using `checkpoint.check` and `checkpoint.adjust_plan`. |
| `scenarios` | Keep `days[].timeline` as primary; add a complete `days[].scenarios[].timeline` only for a material full-day change. |
| `context` | Put `meal`, `booking`, `links`, and `alternatives` inside the affected timeline event. |
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

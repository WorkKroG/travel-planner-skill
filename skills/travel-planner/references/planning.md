# Compare, select, detail, and revise

When meaningful choices exist, present up to three genuinely different alternatives in geography, bases, pace, cost, or experience mix. Reject alternatives that violate hard constraints, then compare travel time, lodging changes, physical load, weather resilience, cost basis, and preference fit. If only one route is sensible, explain why.

At each route choice and day decision, connect the fact or unknown to its applicability, consequence, and next action. Assess conflicts in context; the data helper does not decide whether a route works. Retain a conditional alternative when the missing fact could change the choice. Do not request scores, required markers, or invented timestamps just to satisfy a program.

Show trade-offs and a recommendation before asking the user to choose. Record the selected option, rejected alternatives, and reasons in `decisions.md`. Store alternatives and the selection in `itinerary.yaml`; a view-only scenario switch in HTML does not alter that selection.

Detail only the chosen route. Use `route_stops` and `days[].timeline[]`; every day and timeline event has an ID. The primary timeline is the single chronological plan and each event declares a `kind`: `transport`, `activity`, `meal`, `lodging`, `rest`, or `checkpoint`. Keep human time labels, and add offset-bearing timestamps, operating/service cutoffs, component durations, connection minimums, and buffer markers only when supported. Link days/events to canonical route, overnight, readiness, source, and claim IDs. Unknown stays unknown.

Every concrete major program point must carry practical links in its own `timeline[].links[]`: the official venue/operator page and a map point (or a route for transport). Apply this to the primary plan, every full alternative scenario and local substitutions. A combined event visiting several places needs clearly labelled links for each place. Use `official`/`tickets` and `map`/`route` kinds; supporting research belongs in canonical `source_ids`/`claim_ids`, not a reader bibliography. Keep source records for every researched link.

Reuse a confirmed official page or verify a new one; never invent a domain or call a directory an operator's official site. When no dedicated site exists, use an authoritative official tourism page and label it accurately. For an unnamed hotel, unselected workshop, unconfirmed meeting point or unavailable official page, keep available links and explicitly record what remains to select or find. Breakfast, packing, rest and other generic actions need no artificial place links. Review this coverage before rendering; schema checks alone cannot judge which points are main or whether a page is official.

Store a local substitution in the owning event's `alternatives[]`, including the reason to choose it and any known price, effort, distance, booking, or links. Never create an orphan day-level link rail.

Use `days[].scenarios[]` only when a material portion of the day changes. The primary plan remains `days[].timeline`; each alternative scenario records its own stable ID, user-facing label, optional summary, and complete timeline. Do not store fragment-only scenarios or duplicate the primary plan as a scenario.

For the day layout, optionally record `timeline[].period` as `morning`, `afternoon`, or `evening` when that reading group is supported by the plan. Leave it absent for unassigned or reservation-dependent timing; the renderer groups only adjacent equal values and never sorts events or derives periods from text or clock time. `timeline[].icon` and `scenarios[].icon` may select a bundled semantic icon from the itinerary schema; otherwise the existing kind/weather icon is used. A day may also record `primary_label`, `primary_summary`, and `primary_icon` to name its main route. These are presentation annotations, not a second timeline or a change to the selected route.

Represent a real decision moment as a `checkpoint` timeline event with both `checkpoint.check` and `checkpoint.adjust_plan`. Normally use no more than two checkpoints per primary day. Keep ordinary caveats beside their event instead of promoting every uncertainty to a checkpoint.

Apply the same day contract in both cases:

| Day contract applicability |
| --- |
| `initial_detail`, `material_change` |

| Day facet | Required content |
| --- | --- |
| `intent` | State a concise day `thesis`. |
| `summary` | Summarize expected `load` and `travel`. |
| `checkpoints` | Put real switch decisions in the affected timeline position using `checkpoint.check` and `checkpoint.adjust_plan`; keep ordinary cutoffs beside their event. |
| `scenarios` | Keep `days[].timeline` as primary; add a complete `days[].scenarios[].timeline` only for a material full-day change. |
| `context` | Meals use `kind: meal`; put their name in `title`, conditions in `detail`, and practical links and substitutions in `links[]` and `alternatives[]`. |
| `evidence` | Attach `source_ids[]` and `claim_ids[]`; explain material uncertainty and its consequence in `detail`. |
| `transport` | Put local time in `time`, door-to-door segments and buffers in `detail`, and comfortable/budget choices in `alternatives[]`. |

## Event field recording

Here, **event** means an entry in `itinerary.yaml.days[].timeline[]` or `days[].scenarios[].timeline[]`. Use the same fields for primary and full alternative days. The paths below identify existing fields; they are not additional YAML keys.

| Information | Working record | Reader-visible content |
| --- | --- | --- |
| Meal | An event with `kind: meal`, `title`, `detail`, `links[]` and nearby `alternatives[]`. | Name the meal/place in `title`; put relevant dietary conditions and unresolved questions in `detail`. |
| Main-event booking | `readiness.yaml.items[]` owns `status`, `next_action`, known `due_at` and evidence. Connect the event with `readiness_ids[]`. | Summarize the booking status and important deadline/conditions in `event.detail`; the preparation item shows the action, status and deadline. |
| Local-alternative booking | `event.alternatives[].booking`; create a readiness item when preparation is required. | The alternative's `booking` text is displayed. A main event has no displayed booking field, so its booking summary belongs in `detail`. |
| Sources | `candidates.yaml.sources[]` owns source records; link events through `source_ids[]` and `claim_ids[]`. Follow [research](research.md) for claim ownership. | Put official-site/ticket and map/route URLs in the event's `links[]` and each local alternative's own `links[]`. IDs alone do not create event links. |
| Fact certainty | The claim's `status` in `candidates.yaml`; an unresolved action belongs in `readiness.yaml`. | State a material unknown/conflict, its consequence and the next action in the affected `event.detail`. Claim status is not automatically displayed there. |
| Local time | `event.time`; supported exact instants additionally use `start_at` and `end_at` with timezone offsets. | `time` is the displayed label, such as “10:30–12:00, local UTC+03:00”. Explain timezone changes. Approximate/unknown times stay descriptive; do not invent dates or offsets. |
| Opening, last entry or last service | Known `operating_start_at`, `operating_end_at`, `last_admission_at` or `last_service_at` on the event. | Explain any consequential cutoff in `event.detail`. For an actual switch decision, use a separate checkpoint event with `checkpoint.check` and `checkpoint.adjust_plan`. |
| Door-to-door transport | A `kind: transport` event; supported `allocated_minutes`, `components_minutes`, `connection`, `buffer_markers` and `required_buffer_markers` may retain structured detail. | Describe the complete trip, walks, waits, changes and buffers in `event.detail`, marking estimates. `days[].travel` is the short day summary. |
| Comfortable/budget alternatives | `event.alternatives[]` with `title`, `reason`, `detail` and known `price`, `effort`, `distance`, `booking`, `links[]`. | Name each alternative and when to choose it. A displayed alternative price is comparison text; only selected recorded expenses belong in `budget_items`. |

Technical timestamps, duration fields and ID links support the working data; they do not populate visible event text automatically. Put every condition that changes what the traveller should do in `time`, `detail`, the checkpoint or the relevant alternative. Keep unknowns explicit without inventing values to fill slots.

When a booking, claim, time or route changes, update its owning record and the affected visible summaries together, including full scenarios and local alternatives. Preserve unrelated events and the normal consent rules. The visible text is a concise reading of the current record, not a separately maintained decision.

### Copyable recording example

This is a fictional illustration, not researched travel advice. Replace its places, facts, IDs, URLs and timestamps with actual trip data. The filename keys below label **fragments to add to the corresponding initialized files**; do not save this wrapper as a new bundle format or replace existing preparation items. It illustrates part of a day, not a complete itinerary; the same event contract applies inside a complete alternative day's timeline. Fill practical official/map links for actual transport and venue choices using the coverage rules above.

```yaml
candidates.yaml:
  sources:
    - {id: demo-museum, url: "https://example.org/museum", source_type: official, publisher: "Example museum", retrieved_at: "2026-09-09T12:00:00+00:00", retrieval_status: ok}
    - {id: demo-map, url: "https://example.org/museum-map", source_type: primary, publisher: "Example map", retrieved_at: "2026-09-09T12:00:00+00:00", retrieval_status: ok}
  claims:
    - {id: demo-return, topic: "Return timetable", status: not_released_yet, source_ids: [demo-museum], value: "Return timetable not yet published"}
readiness.yaml:
  items:
    - id: reserve-museum
      title: Reserve the museum visit
      category: activities
      status: action_needed
      due_at: "2026-11-13T18:00:00+03:00"
      next_action: Reserve by the deadline; record confirmation or choose the fallback.
      source_ids: [demo-museum]
    - id: check-return
      title: Recheck the return timetable
      category: transport
      status: not_released_yet
      next_action: Check the operator before leaving; use a taxi if no departure is confirmed.
      claim_ids: [demo-return]
itinerary.yaml:
  days:
    - id: museum-day
      date: "2026-11-14"
      thesis: Visit the museum with time for lunch and a flexible return.
      load: light
      travel: About 75 minutes to the museum; return service remains unknown.
      timeline:
        - id: museum-transfer
          kind: transport
          title: Hotel to museum
          time: "09:00, local UTC+03:00"
          detail: "Estimate: 75 minutes door to door — 10 min walk + 35 min train + 15 min wait + 15 min bus."
          alternatives:
            - {id: comfortable-taxi, title: Taxi, reason: "Less walking", detail: "About 40 minutes, traffic dependent.", price: "45 EUR per group, estimate", effort: low, booking: "Book the taxi in advance"}
            - {id: budget-bus, title: Bus, reason: "Lower cost", detail: "About 90 minutes, service dependent.", price: "8 EUR per person, estimate"}
        - id: museum-visit
          kind: activity
          title: Museum visit
          time: "10:30–12:00, local UTC+03:00"
          start_at: "2026-11-14T10:30:00+03:00"
          end_at: "2026-11-14T12:00:00+03:00"
          last_admission_at: "2026-11-14T11:00:00+03:00"
          detail: "Last entry 11:00. Not booked; reserve by 18:00 the previous day."
          readiness_ids: [reserve-museum]
          source_ids: [demo-museum, demo-map]
          links:
            - {label: Museum website, url: "https://example.org/museum", kind: official, requires_internet: true}
            - {label: Museum map, url: "https://example.org/museum-map", kind: map, requires_internet: true}
        - id: museum-lunch
          kind: meal
          title: Lunch near the museum
          time: "12:30, local UTC+03:00"
          detail: Ask about nuts before ordering; the restaurant and suitable dishes remain to be selected.
        - id: return-check
          kind: checkpoint
          title: Choose the return transport
          time: Before leaving
          detail: Return timetable not yet published; do not rely on a fixed departure.
          readiness_ids: [check-return]
          claim_ids: [demo-return]
          checkpoint:
            check: Check the operator before leaving.
            adjust_plan: Take a taxi if no departure is confirmed.
```

## Changes and day media

For each day, retain 1–3 available photographs of its main locations when useful. Store the ordered `days[].media` records and local `media/` files using the contract in [verification and render](verification-and-render.md). Preserve the source, licence, creator credit and purposeful alt text; label alternative-scenario locations clearly. Do not pad a one- or two-photo day to three, and leave media absent when no suitable image is available.

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

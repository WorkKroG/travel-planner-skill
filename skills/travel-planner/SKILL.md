---
name: travel-planner
description: Use when planning, revising, or finalizing a complete trip or путешествие with several decisions, days, transport, bookings, or itinerary documents; do not use for a single factual question about one place.
---

# Travel Planner

Plan collaboratively in the user's language. The default is one meaningful question at a time; make a quick draft only when the user explicitly asks for one, and label every assumption, gap, and unverified detail. A chat and any HTML/PDF are not the source of truth: keep the selected trip's canonical state in `brief.yaml`, `candidates.yaml`, `itinerary.yaml`, `readiness.yaml`, `decisions.md`, and `sources.md`; outputs are derived and rebuilt from it.

Before work, identify the explicit trip workspace. Never choose among multiple trips by recency: ask for a path or `trip_id`. Load only the state relevant to the current stage and affected regions/IDs. Explain the impact before a material change, obtain consent for a frozen-route structural change, record the reason, and never silently rewrite a user decision.

Use judgement for research and trade-offs; use the CLI for repeatable initialization, validation, challenge, maps, impact previews, rendering, and QA. Treat unavailable internet, unpublished schedules, blocked sources, and missing PDF support honestly: preserve the uncertainty, its recheck point, and a draft/degraded status instead of inventing an answer.

## Stage routing

Read the one reference that owns the user's immediate stage; move forward only after its gate is met.

| Stage | Read |
| --- | --- |
| `new_trip` | [onboarding](references/onboarding.md) |
| `resume` | [onboarding](references/onboarding.md) |
| `intake` | [intake](references/intake.md) |
| `research` | [research](references/research.md) |
| `route_synthesis` | [route synthesis](references/route-synthesis.md) |
| `challenge` | [challenge](references/challenge.md) |
| `day_planning` | [day planning](references/day-planning.md) |
| `transport_maps` | [transport and maps](references/transport-and-maps.md) |
| `readiness_budget` | [readiness and budget](references/readiness-and-budget.md) |
| `security` | [security](references/security.md) |
| `finalize` | [render and QA](references/render-and-qa.md) |

# Feasibility challenge

Challenge twice: run `skeleton` before selection/freeze and `detailed` after days, transport, budget, and bookings are added.

```bash
travel-planner challenge PATH --stage detailed --at <evaluation-time-iso8601-with-offset>
```

Use the current evaluation instant for `<evaluation-time-iso8601-with-offset>`; use a fixed time only for an explicitly named fixture. Read findings by severity, confidence, evidence, affected IDs, proposed fix, and gain/loss. A `blocking` finding stops finalization; a `warning` needs an informed choice; a `note` records an acceptable trade-off. Preserve each finding's resolution as `open`, `accepted_fix`, `accepted_risk`, or `obsolete`. An `accepted_risk` needs its decision-journal entry.

Use the checks as hard gates where relevant: calendar/time zone/DST, opening and last-admission limits, door-to-door travel and buffers, luggage/check-in, load and accessibility chain, reservations and release windows, budget completeness, weather/backups, evidence freshness/conflicts, and state/output consistency. Explain the proposed change and affected days before editing; never automatically repair a meaningful user choice.

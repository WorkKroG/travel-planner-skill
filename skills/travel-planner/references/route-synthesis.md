# Route synthesis and selection

Build up to three genuinely different route skeletons when choices exist: differences must concern geography, bases, pace, or experience mix. If constraints leave one sensible option, present it with that explanation. Reject a skeleton on hard constraints before comparing softer trade-offs such as travel time, lodging changes, diversity, cost, physical load, weather resilience, and interest fit.

Before asking for a choice, run the skeleton challenge against the explicit workspace:

```bash
travel-planner challenge PATH --stage skeleton --at 2026-08-28T12:00:00+00:00
```

Show the user the alternatives, hard failures, trade-offs, and recommendation. After their choice, record selected/rejected options and reasons in `decisions.md`, then move the route through `draft → challenged → selected → frozen`. Selection and freeze are separate confirmations.

After freeze, geography, overnight, hotel, fixed-event, or flight changes require an impact explanation and explicit consent. Preview a saved before/after workspace with:

```bash
travel-planner impact BEFORE_PATH AFTER_PATH
```

Apply only the approved scope, retain accepted risks in the decision journal, and schedule the required challenge/rebuild. Never make a material route change silently.

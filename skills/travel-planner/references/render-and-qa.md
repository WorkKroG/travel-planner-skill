# Render and quality gates

Canonical YAML and the decision/source files are authoritative. Markdown, self-contained HTML, and PDF are derived; a manual edit to an output is not a route change. Bring a requested change back into state, explain its impact, validate, then rebuild the affected views.

First validate the selected workspace and resolve blocking findings. Render only valid state:

```bash
travel-planner validate PATH
travel-planner challenge PATH --stage detailed --at 2026-08-28T12:00:00+00:00
travel-planner render PATH --format html --output PATH/outputs/itinerary.html --at 2026-08-28T12:00:00+00:00
travel-planner qa PATH/outputs/itinerary.html --profiles phone,tablet,desktop,narrow
```

Only successful validation, detailed challenge, and QA permit a Final label. Otherwise render/describe a Draft with blockers, stale/conflicting/unknown information, rechecks, and degraded capabilities. The HTML must remain useful offline and without JavaScript; its external map/source links still require internet. If PDF support is unavailable, deliver the checked HTML and say that no PDF was created. Create a PDF from a checked HTML only when the adapter is available:

```bash
travel-planner pdf PATH/outputs/itinerary.html --output PATH/outputs/itinerary.pdf
```

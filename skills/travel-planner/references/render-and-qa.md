# Render and quality gates

The four YAML files are canonical machine state; `decisions.md` is the decision-history journal; `sources.md` is a regenerable, read-only projection. Update source facts and freshness in their owning YAML records, not in `sources.md`. Markdown, self-contained HTML, and PDF are derived; a manual edit to an output is not a route change. Bring a requested change back into state, explain its impact, validate, then rebuild the affected views.

First validate the selected workspace and resolve blocking findings. Ordinary `render` always produces a Draft. To publish Final HTML, `finalize` builds a candidate, runs QA on those exact bytes, then publishes those same bytes with an adjacent `<html-file>.qa.json` receipt bound to its SHA-256:

```bash
travel-planner validate PATH
travel-planner challenge PATH --stage detailed --at <evaluation-time-iso8601-with-offset>
travel-planner finalize PATH --output PATH/outputs/itinerary.html --at <evaluation-time-iso8601-with-offset> --profiles phone,tablet,desktop,narrow
```

Replace `<evaluation-time-iso8601-with-offset>` with the current evaluation instant; use a fixed timestamp only for an explicitly named fixture. Only successful validation, detailed challenge, and receipt-bound QA permit a Final label. A changed HTML file no longer matches its receipt and cannot authorize Final PDF export. Otherwise render/describe a Draft with blockers, stale/conflicting/unknown information, rechecks, and degraded capabilities. The HTML must remain useful offline and without JavaScript; its external map/source links still require internet. If PDF support is unavailable, keep the checked Final HTML and say that no PDF was created. Create a PDF from that checked HTML only when the adapter is available:

```bash
travel-planner pdf PATH/outputs/itinerary.html --output PATH/outputs/itinerary.pdf
```

# Japan autumn 2026 example

This is a readable, anonymized trip workspace derived from the Japan scenario fixture. It is an illustrative **draft-quality planning artifact**, not final travel advice: live schedules, seasonal conditions, entry requirements and bookings all retain explicit rechecks.

Create a separate throwaway workspace when testing `init`:

```sh
travel-planner init /tmp/japan-example-smoke --title "Japan example smoke" --trip-id japan-example-smoke --confirm-path
```

Check and render the committed example with the current internal CLI:

```sh
travel-planner check examples/japan-autumn-2026
travel-planner render examples/japan-autumn-2026 --output /tmp/japan-autumn-2026.html --at 2026-08-28T12:00:00+00:00
```

The temporary output path avoids overwriting the committed deterministic artifact.

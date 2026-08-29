# Transport and maps

Treat official operator pages as the schedule authority. Maps are contextual links, not proof of departures, accessibility, border rules, or travel time. Record operational uncertainty and recheck it near the trip instead of guessing.

With `map_provider: auto`, use Yandex Maps for Russia, CIS countries, and Turkey, and Google Maps elsewhere. The rule follows the destination's ISO country code, not document language or the user's location. A user's explicit `yandex` or `google` preference wins. For international routes, choose per location or domestic leg; use two clearly labelled links where a cross-border journey needs a fallback.

Generate a safely encoded place link with the deterministic policy:

```bash
travel-planner map-link --country TR --query "Galata Tower"
```

If a preferred link cannot be made, name the fallback and retain the diagnostic reason. Keep timing, booking, baggage, border, and check-in facts linked to their official source.

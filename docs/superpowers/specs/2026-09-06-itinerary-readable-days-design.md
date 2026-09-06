# Readable Itinerary Days — HTML Design Specification

**Date:** 2026-09-06
**Status:** Approved by user; implementation contract
**Supersedes:** the detailed-day layout, navigation and scenario treatment in `2026-08-28-interactive-itinerary-html-design.md`
**Keeps:** the earlier specification's product scope, lifecycle truth, self-contained local opening, accessibility, responsive and browser-print guarantees

## 1. Outcome

The generated HTML is a calm, readable itinerary rather than a dashboard. The document retains the existing Curated Route / Mineral and Maple identity, but replaces the permanent desktop sidebar and two-column day body with a bounded reading column and a sequence of visually distinct day chapters.

The primary reading task is: understand each day in chronological order, notice the few moments that can change the plan, and open contextual links or alternatives only when needed. Search and filters remain progressive enhancements; they do not determine the visual architecture.

## 2. Page structure and navigation

- The document uses one centred reading column with a maximum readable width and generous section spacing.
- A compact in-flow contents disclosure appears after the cover and is closed by default at every breakpoint. Without JavaScript it remains a native, usable disclosure containing all section and day links.
- There is no permanent sticky left index, fixed bottom contents button or three-column composition.
- The cover keeps trip identity, route, lifecycle status, readiness, recorded expenses and the highest-priority saved concerns, but its supporting facts read as document furniture rather than dashboard cards.
- The day overview remains compact and filterable, with a stacked transformation on narrow screens. The document does not offer full-text search.

## 3. Day chapters

Every day is a distinct chapter with a clear beginning and ending:

1. day number, localized date/weekday and primary region;
2. a one-sentence thesis and overnight/location metadata;
3. scenario tabs only when one or more materially different alternative day timelines exist;
4. one timeline containing every primary event type;
5. optional one-image day portrait with provenance;
6. adjacent-day navigation.

Chapters use a light, repeating three-accent sequence derived from mineral, pale maple and pale brass fields. Accent is structural rather than semantic: important states never rely on the day colour. Large spacing, a top rule, chapter number and a closing rule make the boundaries unmistakable in screen and print.

At most one meaningful image is rendered per day. Missing media produces no empty frame. Failed optional media removes the image surface and retains a concise fallback only when useful. Every embedded image has a purposeful `alt`, source identifier and licence; the HTML has no required remote media.

## 4. Canonical event contract

`days[].timeline` is the selected primary timeline and remains canonical. Each event has:

- stable `id`;
- `kind`: `transport`, `activity`, `meal`, `lodging`, `rest` or `checkpoint`;
- human `time`, `title` and `detail`;
- optional structured timestamps, duration, connection, buffers and canonical references already supported by v0.1;
- optional `links[]` owned by that event;
- optional `alternatives[]` owned by that event;
- for `kind: checkpoint`, required `checkpoint.check` and `checkpoint.adjust_plan`.

Meals, transfers, activities, check-in and rest therefore share one chronological structure. There is no separate Food in context section and no separate day-level Contextual actions column.

### 4.1 Event links

Each event link has `label`, absolute HTTPS `url`, `kind` (`map`, `route`, `official`, `tickets` or `source`) and `requires_internet`. Links are rendered only when present, never as naked URLs, and receive a localized connectivity note. Map/place actions use a localized equivalent of “Open on map”; transport route actions use “Build route”. Official schedule truth remains outside map providers.

### 4.2 Event alternatives

An event alternative has stable `id`, `title`, `reason` and `detail`, with optional `price`, `effort`, `distance`, `booking` and its own `links[]`. It appears inside the owning event in a native disclosure labelled `Alternatives (N)`. Opening or closing it changes only the view and never edits canonical state.

### 4.3 Checkpoints

A checkpoint is a timeline event, not a side rail. It visibly answers:

1. when to decide, using the event time;
2. what to check, using `checkpoint.check`;
3. how to change the plan, using `checkpoint.adjust_plan`.

Strong maple contrast is reserved for checkpoints and lifecycle/blocking truth. Normal caveats stay quiet and adjacent to the affected event. A well-formed day should normally contain no more than two primary checkpoints; the schema permits drafts while the planning instructions set the authoring limit.

## 5. Alternative day scenarios

`days[].scenarios[]` contains alternative day plans only. Each scenario has stable `id`, localized user-facing `label`, optional `summary`, and a complete `timeline[]` using the same event contract. The primary tab is represented by `days[].timeline`; no duplicate primary scenario is stored.

- Tabs appear only when an alternative scenario is recorded because a substantial part of the day changes.
- Tabs use the WAI-ARIA tab pattern with keyboard Left/Right, Home and End navigation.
- Switching tabs replaces the timeline in the same chapter area and announces the visible scenario without changing YAML.
- Without JavaScript, the primary and every alternative timeline remain in source order with explicit headings.
- Print shows the primary timeline in full and each alternative scenario in a compact, clearly labelled block.

## 6. Localization

`brief.yaml.document_language` selects visible system copy. v0.1 supports `en` and `ru`; absence defaults to `en` for simple compatibility. Titles, status explanations, navigation, headings, filters, scenario controls, connectivity notes, dates, weekdays, enum labels, empty states and JavaScript announcements use the selected language. Canonical enum values remain visible only in the lifecycle audit definition list where they are explicitly technical provenance.

User-authored itinerary content is never machine-translated by the renderer. A workspace should therefore author its content in the same language as `document_language`.

## 7. Responsive, accessibility and failure behaviour

- One-column reading flow is preserved from 320 CSS px upward with no horizontal page scrolling.
- Body text is at least 16 CSS px; touch targets are at least 44×44 CSS px.
- Timeline time remains a visually prominent column on wide screens and becomes a labelled block above event content on narrow screens.
- Heading anchors and focus rings are not obscured because no persistent navigation overlaps the reading area.
- Landmarks, heading hierarchy, native details, accessible tab names/states, semantic ordered timelines, live announcements and reduced-motion behaviour are mandatory.
- Core content is visible before JavaScript runs. Enhancement failure exposes a localized concise notice and leaves every timeline and normal link readable.

## 8. Print

- Interactive filters, tab controls and adjacent-day controls are hidden.
- Filtered days and hidden scenario panels are forced visible.
- Each normal day starts on a fresh page when practical and repeats day/date context in its header.
- Primary timeline events, checkpoints and compact alternative scenario blocks avoid page splits when practical.
- The primary timeline prints in full; alternative day scenarios print more compactly but with complete titles, times and details.
- Link labels and source identifiers print without dumping naked URLs into the reading flow; the existing source appendix remains the place for full source URLs.
- Optional imagery obeys the renderer's print-images option and never creates a blank page.

## 9. Data compatibility and non-goals

There is no migration framework. Repository fixtures and the bundled trip template adopt the new event/scenario contract directly. `document_language` is optional and defaults to English. Retaining old day-level `food`, `links`, prose `critical_constraints`, or description-only scenario records is not a goal; pre-release workspaces may remain incomplete drafts and should be regenerated or edited explicitly.

This work does not add an MCP, backend, account, sync, browser automation stack, offline workflow, built-in PDF pipeline, migration system, partial rebuild, eval runner, judge or simulator.

## 10. Acceptance evidence

Automated evidence covers:

- schema acceptance/rejection for typed events, checkpoints, event links, event alternatives and scenario timelines;
- canonical reference checks across primary and alternative timelines;
- immutable localized view-model projection;
- event-owned links and alternatives in HTML;
- no separate food/context/critical side columns;
- ARIA tabs plus complete no-JavaScript and print content;
- one-column/sticky-navigation/static wrapping contracts;
- HTTPS allow-list across event and alternative links;
- deterministic fixed-time Japan render and snapshot hash;
- self-contained asset boundary and optional-media provenance.

One bounded visual QA round inspects the generated Japan example at desktop and mobile widths. One batched correction and at most one confirmation round are allowed. Static tests remain static evidence and do not claim a browser accessibility engine, device farm or automated layout suite.

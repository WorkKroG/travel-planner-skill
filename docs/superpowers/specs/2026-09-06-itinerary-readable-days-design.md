# Readable Itinerary Days — HTML Design Specification

**Date:** 2026-09-06
**Status:** Approved by user; amended on 2026-09-08 for reader HTML without technical source lists and on 2026-09-10 for compact route navigation
**Supersedes:** the detailed-day layout, navigation and scenario treatment in `2026-08-28-interactive-itinerary-html-design.md`
**Keeps:** the earlier specification's product scope, lifecycle truth, self-contained local opening, accessibility, responsive and browser-print guarantees

## 1. Outcome

The generated HTML is a calm, readable itinerary. The document uses the Lemon and Cobalt visual system in [DESIGN.md](../../../DESIGN.md), including the approved 8 September day composition, and replaces the permanent desktop sidebar and two-column day body with a bounded reading column and a sequence of visually distinct day chapters.

The primary reading task is: understand each day in chronological order, notice the few moments that can change the plan, and open contextual links or alternatives only when needed. A compact base sequence gives the trip geography; date-and-place contents links provide direct access to detailed days without a second list of day summaries.

## 2. Page structure and navigation

- The document uses one centred reading column with a maximum readable width and generous section spacing.
- A compact in-flow contents disclosure appears after the cover and is closed by default at every breakpoint. Without JavaScript it remains a native, usable disclosure containing all section and day links.
- There is no permanent sticky left index, fixed bottom contents button or three-column composition.
- The cover keeps trip identity, lifecycle status, readiness, recorded expenses and the highest-priority saved concerns, but its supporting facts read as document furniture rather than dashboard cards. Its primary link goes directly to detailed days.
- The route appears once in a compact sequence of bases, dates and recorded night counts, wrapping on wide screens and forming short rows on narrow screens. Unknown night counts are omitted, never zero-filled. Transfer explanations remain in detailed days and canonical working data rather than expanding this overview.
- Native contents list each day by localized date and place. There is no separate day-summary list, day filtering or full-text search. Day introductions and travel/load facts remain in their chapters; open decisions, readiness and saved concerns retain their sections.

## 3. Day chapters

Every day is a distinct chapter with a clear beginning and ending:

1. large region heading on the left, day number on the right, localized date/weekday and thesis;
2. optional gallery of 1–3 photographs beneath the introduction inside the yellow header;
3. three compact facts beneath the gallery: overnight, travel and load;
4. a localized “How we’ll spend the day” heading on every day; scenario tabs appear only when materially different alternative day timelines exist;
5. one complete chronological timeline with separate time, circular semantic icon and text columns, optionally grouped by recorded periods;
6. adjacent-day navigation in a light-blue closing field; compact photo credits remain beside their captions, research history stays in the planning conversation without a separate materials list.

The [approved 7 September specification](2026-09-07-html-visual-redesign-design.md) replaces the earlier three-accent chapter cycle with Lemon and Cobalt throughout the complete document. Chapter openings, generous spacing and closing fields establish boundaries; semantic states remain explicit in text.

The user-approved amendment of 7 September replaces the one-image limit: each day may show 1–3 meaningful photographs of its main locations, including clearly captioned alternative-scenario locations. Use the available one or two images without padding the gallery to three. Missing media produces no empty frame. Failed optional media removes only the affected image surface and retains its caption and a concise localized fallback. Every embedded image has a purposeful nonblank `alt`, caption, source identifier, attribution, licence and recorded dimensions; the HTML has no required remote media.

`days[].media` is an ordered array, omitted or empty when no suitable media is available, with a maximum of three records. Each record has `path` (relative POSIX file path beneath the trip's `media/`, no traversal or symlink escape), `mime_type` (`image/jpeg`, `image/png`, `image/webp`, `image/avif`), `alt`, `caption`, `source_id` (resolves to `candidates.yaml.sources`), `attribution` (creator credit or generation provenance), `license`, and positive integer `width`/`height` in pixels. Source URLs must be absolute HTTPS links. Existing local sources may be imported without claiming a fresh remote verification. Keep their original attribution and licence; do not infer a licence from the repository's MIT licence.

The gallery appears in the day header after the thesis and before metadata, scenario controls and timelines. Checkpoints remain in chronological order before the events they govern; the header gallery does not remove or collapse their instructions. One photograph fills the available reading width; two or three form equally sized columns on wide screens. Three-photo galleries stack at 760 CSS px and below; all galleries stack at 460 CSS px and below. Captions immediately follow images, with a compact linked creator credit and recorded license that remain available without JavaScript. There are no empty columns, carousel or lightbox. Print uses at most two columns with bounded image height, keeps each image and caption together when practical, and honors the existing no-image option. Photo credits stay inside each printed figure. Neither screen nor print contains a source index or a separate URL appendix.

## 4. Canonical event contract

`days[].timeline` is the selected primary timeline and remains canonical. Each event has:

- stable `id`;
- `kind`: `transport`, `activity`, `meal`, `lodging`, `rest` or `checkpoint`;
- human `time`, `title` and `detail`;
- optional structured timestamps, duration, connection, buffers and canonical references already supported by v0.1;
- optional `links[]` owned by that event;
- optional `alternatives[]` owned by that event;
- optional `period` (`morning`, `afternoon`, `evening`) and `icon` from the bundled schema enum;
- for `kind: checkpoint`, required `checkpoint.check` and `checkpoint.adjust_plan`.

Meals, transfers, activities, check-in and rest therefore share one chronological structure. There is no separate Food in context section and no separate day-level Contextual actions column.

Period headings group only adjacent equal recorded values, preserving source order. Missing periods produce unlabelled groups; the renderer never derives periods from IDs, titles or clock times. An omitted icon retains the existing kind-based fallback. These optional annotations do not alter scheduling or require a migration.

### 4.1 Event links

Each event link has `label`, absolute HTTPS `url`, `kind` (`map`, `route`, `official`, `tickets` or `source`) and `requires_internet`. Links are rendered only when present, never as naked URLs, and receive a localized connectivity note. Every concrete major point must be authored with an official venue/operator link and a map point or transport route, including full scenarios and local alternatives. Combined visits carry links for each named place. Unknown venues or unavailable official pages stay explicit; the renderer does not invent links and the schema does not classify main points. Map/place actions use a localized equivalent of “Open on map”; transport route actions use “Build route”. Official schedule truth remains outside map providers.

### 4.2 Event alternatives

An event alternative has stable `id`, `title`, `reason` and `detail`, with optional `price`, `effort`, `distance`, `booking` and its own `links[]`. It appears inside the owning event in a native disclosure labelled `Alternatives (N)`. The source disclosure is open so content survives absent or failed JavaScript; successful enhancement collapses it until requested. A separate print-only projection preserves the same alternative content regardless of disclosure state. Opening or closing the disclosure changes only the view and never edits canonical state.

### 4.3 Checkpoints

A checkpoint is a timeline event, not a side rail. It visibly answers:

1. when to decide, using the event time;
2. what to check, using `checkpoint.check`;
3. how to change the plan, using `checkpoint.adjust_plan`.

A light-yellow field and labelled semantic icon identify checkpoints; lifecycle and blocking truth retain explicit distinct status wording. Normal caveats stay quiet and adjacent to the affected event. A well-formed day should normally contain no more than two primary checkpoints; the schema permits drafts while the planning instructions set the authoring limit.

## 5. Alternative day scenarios

`days[].scenarios[]` contains alternative day plans only. Each scenario has stable `id`, localized user-facing `label`, optional `summary` and bundled `icon`, and a complete `timeline[]` using the same event contract. The primary tab is represented by `days[].timeline`; optional day fields `primary_label`, `primary_summary` and `primary_icon` customize its presentation. No duplicate primary scenario is stored.

- Tabs appear only when an alternative scenario is recorded because a substantial part of the day changes.
- Tabs use the WAI-ARIA tab pattern with keyboard Left/Right, Home and End navigation.
- Switching tabs replaces the timeline in the same chapter area and announces the visible scenario without changing YAML.
- Without JavaScript, the primary and every alternative timeline remain in source order with explicit headings.
- Print shows the primary timeline in full and each alternative scenario in a compact, clearly labelled block.

## 6. Localization

`brief.yaml.document_language` selects visible system copy. v0.1 supports `en` and `ru`; absence defaults to `en` for simple compatibility. Titles, status explanations, navigation, headings, scenario controls, connectivity notes, dates, weekdays, enum labels, empty states and JavaScript announcements use the selected language. Canonical lifecycle values remain in the working data and footer data attributes; visible status labels remain localized.

User-authored itinerary content is never machine-translated by the renderer. A workspace should therefore author its content in the same language as `document_language`.

## 7. Responsive, accessibility and failure behaviour

- One-column reading flow is preserved from 320 CSS px upward with no horizontal page scrolling.
- Body text is at least 16 CSS px; touch targets are at least 44×44 CSS px.
- Timeline time remains a visually prominent column on wide screens and becomes a labelled block above event content on narrow screens.
- Heading anchors and focus rings are not obscured because no persistent navigation overlaps the reading area.
- Landmarks, heading hierarchy, native details, accessible tab names/states, semantic ordered timelines, live announcements and reduced-motion behaviour are mandatory.
- Core content is visible before JavaScript runs. Enhancement failure exposes a localized concise notice and leaves every timeline and normal link readable.

## 8. Print

- Tab controls and adjacent-day controls are hidden. The compact base sequence remains; all detailed days print in order.
- Hidden scenario panels are forced visible; full day chapters are always present.
- Each normal day starts on a fresh page when practical; every printed event repeats a compact day/date/region context so continuation pages remain identifiable in browsers without paged-media string support.
- Print CSS defines a fixed trip/version/status footer; page counters use `@page` margin boxes. Browser support and actual repetition/pagination require the manual print observations in the [release checklist](../../RELEASE_CHECKLIST.md); source tests alone do not establish them.
- Primary timeline events, checkpoints and compact alternative scenario blocks avoid page splits when practical.
- The primary timeline prints in full; alternative day scenarios print more compactly but with complete titles, times and details.
- Practical links stay beside their events; linked photo credits stay with images. Technical source identifiers, source lists and a full-URL appendix are not part of HTML or print.
- Optional imagery obeys the renderer's print-images option and never creates a blank page.

## 9. Research history and practical links

The HTML is the delivered plan. Research discussion and citations stay in the planning conversation, available only while that history is accessible. No separate bibliography, source snapshot or version-to-source archive is created on any surface. Current canonical source records support claims and photograph attribution without promising recovery of past research. This supersedes the earlier per-build inventory requirement.

## 10. Data compatibility and non-goals

There is no migration framework. Repository fixtures and the bundled trip template adopt the new event/scenario contract directly. `document_language` is optional and defaults to English. Retaining old day-level `food`, `links`, prose `critical_constraints`, or description-only scenario records is not a goal; pre-release workspaces may remain incomplete drafts and should be regenerated or edited explicitly.

This work does not add an MCP, backend, account, sync, browser automation stack, offline workflow, built-in PDF pipeline, migration system, partial rebuild, eval runner, judge or simulator.

## 11. Acceptance evidence

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

Manual visual QA should inspect the generated Japan example at desktop and mobile widths and in print preview. These observations remain pending in the [release checklist](../../RELEASE_CHECKLIST.md). Static tests remain static evidence and do not claim a browser accessibility engine, device farm or automated layout suite.

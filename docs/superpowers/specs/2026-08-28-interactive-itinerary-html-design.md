# Interactive Itinerary HTML — UX/UI Design Specification

**Date:** 2026-08-28  
**Status:** Approved by user; ready as input for the implementation plan  
**Design process:** Impeccable `shape`  
**Reference case:** Japan, 2–13 November 2026

> **Superseded details:** [Readable Itinerary Days — HTML Design Specification](2026-09-06-itinerary-readable-days-design.md), amended through 8 September, replaces this document's navigation model, detailed-day layout, event context, scenario representation, and localization details. [DESIGN.md](../../../DESIGN.md) records the implemented visual system from the 7 September redesign and 8 September day composition, including typography, colours, photo placement and source disclosure. The later 8 September source-list amendment removes research indexes, day source disclosures and the URL appendix from HTML/print; technical inventories are saved per build for Codex retrieval. Other scope, lifecycle, accessibility, self-contained, responsive and print requirements remain active, subject to PRODUCT.md and ARCHITECTURE.md. This original design is retained for scope and decision history, not as a pending implementation plan.

## 1. Purpose and scope

This document specifies the user experience and visual design of the self-contained interactive HTML itinerary produced by Travel Planner Skill. It is a design input for a later implementation plan, not an implementation plan itself.

The itinerary is primarily a **pre-trip planning and review document**. It helps an organiser and other travellers understand the proposed trip, evaluate its feasibility, inspect evidence and alternatives, see what remains unresolved, and agree on the plan before departure.

Using the HTML as an in-trip live companion is outside the current scope. There is no “Today” mode, live navigation, live alerting, location tracking, booking mutation, account, backend, or cross-device synchronisation in this version.

Canonical trip data lives in YAML and Markdown. HTML is a reproducible derived artefact and never becomes the source of truth.

## 2. Design outcome

The selected design direction is **Curated Route**: an editorial travel guide with the discipline of a museum exhibition guide. It should feel considered, calm and place-specific while keeping feasibility, evidence and uncertainty more prominent than decoration.

The first screen answers, within roughly 30 seconds:

1. What is this trip?
2. Where does it go and in what order?
3. Is it ready enough to agree or book?
4. What are the most important warnings or unresolved decisions?
5. Where should the reader go next?

The page is not a generic dashboard. It is a readable document with restrained controls layered onto it.

## 3. Surface mode

### Primary: Read

The dominant task is to understand and evaluate a complex itinerary. Content order, typography, progressive disclosure and print quality therefore take priority over control density.

### Secondary: Operate

Lightweight operations help the reader inspect the document:

- navigate to a day or section;
- filter days locally;
- filter days by meaningful planning conditions;
- expand supporting detail;
- compare the primary and backup scenarios;
- follow external links to maps, official sites, tickets and sources.

These operations change only the view. They never change canonical readiness, booking, decision or itinerary status.

## 4. Directions considered

### A. Curated Route — selected

Editorial hierarchy, exhibition-guide pacing, generous whitespace, a strong route sequence and contextual evidence. It supports both careful reading and quick scanning without disguising uncertainty.

**Strengths:** distinctive, calm, printable, well suited to a pre-trip decision document.  
**Trade-off:** requires disciplined content hierarchy so that atmosphere never pushes warnings below the fold.

### B. Field Atlas

A denser field notebook with annotations, marginalia, evidence cards and cartographic texture.

**Strengths:** communicates research depth and provenance.  
**Trade-off:** visually busy on phones, weaker for group review, and prone to turning every uncertainty into equal-weight annotation.

### C. Transit Control Room

A utility-first dashboard built around schedules, readiness metrics, transfer status and filters.

**Strengths:** rapid operational scanning and comparison.  
**Trade-off:** too close to a generic dashboard, overstates precision, prints poorly, and serves in-trip operations better than the agreed pre-trip use case.

The Curated Route direction is chosen because it best balances comprehension, judgement, character, local opening and print.

## 5. Information architecture

The document uses this order:

1. Trip summary
2. Route and day overview
3. Open decisions
4. Detailed days
5. Preparation: bookings and readiness
6. Budget
7. Risks and backup plans
8. Sources, provenance and document version

Food recommendations live within the relevant days, after the itinerary has established the day’s geography and timing. A large standalone food section does not precede the route.

### Navigation model

- **Wide screens:** sticky left contents index with current-section indication.
- **Medium screens:** compact top contents strip.
- **Phones:** a 52 px “Contents” control positioned above the bottom safe area; opening it reveals section and day links.
- Without JavaScript, the same links remain visible as a normal in-flow contents block near the top of the document.
- Semantic anchors and URL fragments make every day and major section directly addressable.
- Previous/next-day navigation closes each day.
- Sticky elements must not obscure headings when an anchor receives focus.

## 6. First screen

The first screen contains, in priority order:

- trip title, dates, party summary and Draft/Final state;
- the trip thesis in one short paragraph;
- a prominent text-based route sequence;
- a readiness snapshot;
- one to three highest-priority warnings or blockers;
- budget range and confidence/quality of the estimate;
- links to the day overview and unresolved decisions.

The route sequence is information, not decoration. It remains readable text at every breakpoint and in print.

### Postage-stamp motif

One fictional travel-stamp illustration may appear as a small decorative accent:

- on wide screens, in the upper-right area of the first screen with a very slight rotation;
- on phones, below the title and right-aligned so it does not compress the heading;
- never as a replacement for the route, summary, status or warnings;
- its absence must collapse cleanly without leaving an empty reserved area.

The stamp uses a destination-specific object taken from the actual route, not an automatic national stereotype. The Japan reference may use an autumn maple leaf, but the final object remains a trip-content choice. The style is a restrained two-colour print or engraving that works as compact inline vector art and in greyscale. It must not contain a denomination or imitate an official postal issue.

The illustration is decorative. It receives empty alternative text unless it carries unique information, in which case that information must also appear as visible text.

## 7. Route and map treatment

### Route overview

Use a linear route ribbon or sequence of place names with dates/nights and transfer boundaries. On phones it becomes a vertical sequence. It must never require horizontal scrolling.

### Explicit exclusion: overview geographic schematic

Do not include an overview pseudo-map. It duplicates the route sequence, suggests geographic accuracy that the artefact cannot guarantee, and adds cognitive load without helping the agreed planning task.

### Transfer diagrams

An optional compact schematic is allowed only for genuinely complex multi-segment transfers. It may show:

- segment order;
- mode;
- expected duration;
- transfer buffer;
- hard departure or check-in constraints.

It is a sequence diagram, not a geographic map, and must be removable if it does not add clarity.

Exact location context is provided through external map links attached to the relevant activity, lodging or transfer.

The link provider follows the main architecture policy: Yandex Maps by default for Russia, CIS countries and Turkey; Google Maps by default elsewhere; an explicit trip-level user preference overrides automatic selection. International itineraries may use different providers per location or domestic segment.

## 8. Day overview

Immediately after the first screen, show all days in a compact overview. Each item includes:

- day number, date and weekday;
- primary region or city;
- short day thesis;
- overnight location;
- travel/load indicator;
- booking, warning or unresolved marker where applicable.

On desktop this may use a compact table-like composition. On phones it becomes a stacked list with the same information and no horizontal overflow.

The overview must remain useful for a 30-day route. It supports fast filtering rather than shrinking text or creating a long horizontal control strip.

## 9. Detailed day anatomy

Each day contains:

1. Date, weekday, region and overnight location
2. One-sentence day thesis
3. Summary row: load, travel, weather sensitivity and booking state
4. Critical constraints and cut-off points
5. Primary timeline
6. Optional complex-transfer diagram
7. Primary and backup scenarios
8. Food recommendations in geographic context
9. Relevant readiness items
10. Map, official site, ticket and evidence links
11. Sources and last-checked date
12. Previous/next-day navigation

Critical constraints include hard departures, last admission, check-in windows and the latest point at which the plan should switch to a backup. They appear before or immediately beside the affected event, never hidden after a photo gallery.

### Layout

- **Wide:** main timeline plus a narrow context rail for constraints, status and evidence.
- **Medium and compact:** one column; each constraint appears before the event it governs.

The primary plan and critical warnings are expanded by default. Alternatives, fine transport detail and source detail may be collapsed. Disclosure labels state what is inside; avoid vague labels such as “More”.

### Scenario comparison

A primary/backup switch changes the visible scenario only. It does not save a choice as canonical data. The current scenario is announced in text and to assistive technology. Print renders primary and backup together rather than printing an ambiguous switched state.

## 10. Planning support sections

### Open decisions

Show a short decision queue before the detailed days. Sort blockers and time-sensitive choices first. Each item states the question, why it matters, the affected days or bookings, the decision trigger/deadline when known, and the next action. Do not turn this into an editable task manager.

### Bookings and readiness

Group readiness by meaningful planning domain such as transport, lodging, timed entry and required documents. Show confirmed count and total count in text; a progress graphic may support but never replace the numbers. Blockers remain separately visible rather than being averaged into a reassuring percentage.

### Budget

Show the expected range, base currency, major category totals, inclusions/exclusions, unknown amounts and confidence. Every total must distinguish confirmed values from estimates. Currency conversion date and assumptions appear when conversion is used.

### Risks and backup plans

Each material risk states its trigger, likely consequence, fallback and latest practical switch point. Backups are attached to the day or decision they protect and may also be summarised here; they are not a detached list of generic travel advice.

### Sources and version

Provide stable source identifiers, recognisable titles/domains, source type, last-checked date and stale/conflict state. The document footer identifies trip, generation time, Draft/Final state and artefact version so readers can tell whether two copies differ.

## 11. External links

Activities and practical objects may expose these contextual actions:

- Map
- Official site
- Tickets / booking
- Source

Rules:

- show the selected provider name explicitly rather than a generic unlabelled map icon;
- for a cross-border leg where neither provider is clearly sufficient alone, allow labelled primary and alternative map links while keeping the official operator link authoritative for schedules;
- official destinations are visually distinguished from secondary sources;
- the destination domain or recognisable service name is visible before leaving the file;
- all targets are at least 44×44 CSS px;
- links that require connectivity are labelled “Internet required” or receive an equivalent accessible description;
- critical timing, address and constraint information is duplicated in the HTML rather than available only behind a link;
- stale and conflicting links or claims display their status in text;
- print shows a short source/site name and source identifier inline, with full URLs in an appendix.

## 12. Interactivity without a backend

### Included

- anchor navigation by section and day;
- filters for all days, unresolved items, weather-sensitive items, transfers and warnings;
- semantic disclosure controls;
- view-only primary/backup scenario switching;
- copying or opening external links using normal browser behaviour.

### Persistence

Active filters, open disclosures and selected scenario are session-level view state. The first version does not persist them between browser launches and does not require `localStorage`. Any later persistence remains explicitly non-canonical and must offer an obvious reset.

### Progressive enhancement

Core reading order, all primary itinerary information, links and print content remain available when JavaScript is absent or fails. JavaScript enhances filtering, disclosures and scenario presentation; it does not gate the document.

## 13. Responsive behaviour

### Wide: 1024 px and above

- split editorial first screen;
- sticky left contents index;
- route remains prominent text;
- detailed days use timeline plus context rail;
- floating summary panels may sit beside the main reading column.

### Medium: 640–1023 px

- first screen may retain a two-part composition only while headings and route remain comfortable;
- contents moves to the top;
- detailed days become one column;
- controls wrap into short, logical groups.

### Compact: below 640 px

- single-column reading flow;
- identity, route, critical status and supporting summary appear in that order;
- day overview becomes a stacked list;
- route becomes vertical;
- no timeline, table, chip group or source URL causes horizontal scrolling;
- the stamp moves below the title and aligns right;
- fixed controls respect `safe-area-inset-*` and do not cover content.

### Phone ergonomics

- minimum interactive target: 44×44 CSS px;
- main text: at least 16 CSS px; secondary text: at least 14 CSS px;
- important actions stay reachable with one hand near the lower portion of the screen;
- critical information is not conveyed through hover;
- the default light theme maintains legibility in bright conditions;
- dark mode is not required for the first version.

## 14. Visual system

### Direction and colour roles

The approved direction is **Lemon and Cobalt**, as fixed by the [7 September specification](2026-09-07-html-visual-redesign-design.md) and its supplied HTML compositions. It applies to the cover, route overview, contents, every day, existing filters, decisions, readiness, budget, risks, sources and print.

- Day and cover header: `#FFE785`
- Reading paper: `#FFFEF8`
- Main text: `#153369`; secondary text: `#3B5271`
- Actions: `#1649B5`; selected controls: `#1747AB` with white text
- Checkpoint field: `#FFF0B7`; timeline line: `#ACBEE0`
- Closing information field: `#E7EFFF`

Statuses retain explicit wording, icon/shape and distinct danger, attention and confirmation treatments; hue never carries meaning alone. Text and functional graphics require WCAG AA contrast. There is no theme selector or alternate dark palette.

### Composition, shape and spacing

Use a bounded centred reading column. Broad yellow openings and blue closing fields define days. At the reference width of 736 px, a day uses 32 px internal padding, a 66 px region title and 16 px event text. Controls are at least 44 px high. Layout adapts down to 320 px and tolerates long names, mixed scripts and unknown times.

Photos have 16 px corners and 12 px gaps. One photo is wide (`2.8 / 1`); two equal photos use `1.65 / 1`; three equal photos use `1.3 / 1`. At compact widths they form one column in authored order (`1.9 / 1`). Checkpoint event bodies have a light-yellow field; ordinary events sit on paper with small icons on a continuous vertical line.

### Typography and icons

Use large sans-serif headings matching the supplied composition, with local/system fallbacks (Avenir Next, Segoe UI, sans-serif for display; Inter and system sans for body). Do not require remote fonts. Time and money use tabular numerals. Secondary text remains at least 14 px and body text 16 px on screen.

Use the bundled outline SVG symbols. Select an event icon from its canonical kind, independent of IDs or array positions. Scenario controls show recorded primary/alternative semantics and retain visible labels. No external icon library, CDN or host global is required. Do not infer phases or invent timing from ambiguous source text.

### Motion

Motion is functional and restrained: short disclosure and focus transitions, approximately 120–180 ms, without parallax or route animation. Under `prefers-reduced-motion`, non-essential transitions are removed and state changes are immediate.

## 15. Imagery policy

Photography helps comparison and decision-making. The user-approved amendment of 7 September permits a gallery of 1–3 useful images of the main locations of each day; the detailed storage and layout contract is in section 3 of the Readable Itinerary Days specification. There is no hard megabyte cap.

- use one representative image for a primary location when it clarifies atmosphere, scale, season or activity choice;
- use the one or two suitable images available without padding to three; avoid repetitive decorative landscapes;
- place the gallery in the yellow day header beneath its introduction; keep every checkpoint in its chronological timeline position before the action it governs;
- secondary stops do not require imagery;
- reserve dimensions to prevent layout shift;
- optimise and embed assets so the HTML remains self-contained;
- record source, licence or generation provenance;
- provide purposeful nonblank alternative text for every gallery photograph; decorative stamp art remains separate;
- missing optional media collapses cleanly without blocking content.

Embedded media remains optional and must not introduce a required network dependency or compromise scrolling and print reliability.

## 16. Status and exceptional states

### Draft and Final

- **Draft:** visible status label, blocker count and generated/checked date.
- **Final — проверено в Codex:** used only for `finalization_basis=codex_validated`; it requires `verification_level=codex_validated` and no blocking finding.
- **Final — подтверждено пользователем:** used only for `finalization_basis=user_confirmed`; remaining blockers are allowed only when every one has an explicit canonical `accepted_blockers` record.
- An accepted blocker remains visible, blocking and unresolved in HTML and browser print. The UI may add “принят пользователем”, but must not call it fixed, resolved or passed.
- Accepted and unaccepted blockers are shown separately, or with equally clear persistent wording, and are never available only inside collapsed content.
- If a renderer receives a contradictory Final state/report combination, it shows an explicit inconsistency warning and does not use successful Final presentation. It does not create findings or mutate canonical state.
- The distinction appears in text, repeated document furniture and print, never only in colour.

### Stale

Show the date last checked, why rechecking is required and the next action. Do not silently dim the item.

### Conflicting

Show both claims, their sources and dates, and what must resolve the conflict. Do not collapse them into a false single answer.

### External connectivity

The self-contained file opens locally without required network assets. External map, site and booking actions retain their destination but are marked as requiring a connection. This is an artefact property, not a separate offline workflow or status.

### Empty or unknown

State explicitly that no item exists or that the value is unknown. Where useful, include the reason and next step. Never display a blank card or misleading zero.

### Loading

The self-contained core document has no application loading shell or skeleton screen: it renders as ordinary content. Optional images reserve their space and may show a quiet neutral placeholder while decoding. A renderer must finish and validate the document before publishing it rather than exporting a partially loaded “Final” artefact.

### Error

A generation or validation error prevents Final status and produces an explicit build report outside the artefact. At runtime, failure of filtering or another enhancement leaves the full document readable and may show a concise inline notice near the failed control. Do not replace the itinerary with a generic error screen.

### Optional media failure

Remove the broken visual surface and preserve its caption only if the caption carries information. Layout and reading order remain intact.

### JavaScript failure

Render the core document and all primary/backup content in readable order. Enhanced controls may become unavailable without hiding information.

## 17. Accessibility

- Semantic landmarks: header, navigation, main, sections, articles and footer.
- One clear page heading and a logical heading hierarchy.
- Skip link to main content.
- All operations available from the keyboard in a predictable order.
- Visible focus indicator at least 3 CSS px where practical, with sufficient contrast and no clipping.
- WCAG 2.2 AA contrast for text and functional graphics.
- Status is communicated through text plus icon/shape, not colour alone.
- Native controls and disclosure semantics are preferred; custom controls expose name, role, value and state.
- Filter changes and scenario changes receive restrained screen-reader announcements.
- Timeline order is meaningful in the DOM and does not depend on a visual line.
- Images have appropriate alt text; decorative stamp art is hidden from assistive technology.
- At 200% zoom, no content or operation is lost.
- `prefers-reduced-motion` is honoured.
- Touch targets are at least 44×44 CSS px.

## 18. Browser print and Save as PDF

Browser print uses the same information model with dedicated print CSS. There is no built-in PDF command, adapter, separate PDF data pipeline or automatic PDF guarantee; users may choose Print → Save as PDF in their browser.

### Page structure

- Optimise for A4 portrait; Letter must remain usable.
- Page 1: trip identity, route, readiness and top warnings, with the optional stamp as a cover accent.
- Next: day overview and open decisions.
- A normal-length day begins on a new page; two short days may share a page when this does not harm scanning.
- Long days continue with repeated day/date context.
- Each page includes trip name, version/status and page number.

### Print transformations

- hide interactive navigation, filters and button chrome;
- print primary and backup scenarios together;
- prevent critical blocks, timeline events and compact tables from splitting where possible;
- repeat table headers;
- replace sticky/fixed positioning with normal flow;
- show short source/site names and IDs inline, with full URLs in an appendix;
- use lines, labels and hatching so greyscale remains meaningful;
- keep Draft/Final visible in header/footer rather than through colour alone;
- allow the day's gallery in at most two print columns with bounded image height, or an economical no-image print option.

Print QA rejects clipped URLs, orphan headings, blank pages, split critical events and content hidden by interactive state.

## 19. Self-contained local-open requirements

- The artefact opens directly as a local file without a server.
- No network request is required for content, fonts, CSS, scripts, icons or media.
- Core content remains readable without JavaScript.
- Optional images reserve their dimensions and decode without shifting the document.
- All external actions are identifiable before activation and clearly state that they require an Internet connection.
- One automated test verifies that no required `http(s)` asset URL, import or request exists. External source and map links remain allowed as user-activated links.
- No offline status, offline UI, offline challenge, offline eval or network-disabled workflow is introduced.

## 20. Quality assurance matrix

The user-visible requirements below remain unchanged. Their evidence is split by what the
test method can truthfully observe; removing a browser runner does not convert layout,
accessibility or visual behaviour into a source-code assertion.

### Deterministic Python and static checks

Automated checks cover:

- one fixed-time Japan render and committed reference hash;
- self-contained assets, escaping and the external-link URL allow-list;
- lifecycle labels plus visible accepted and unaccepted blockers;
- semantic source order, navigation and complete primary/backup content without JavaScript;
- print declarations that preserve critical content and separate control-only elements;
- source-level long-content wrapping/min-width declarations;
- header galleries after the day introduction, with complete checkpoints and their actions preserved in chronological timeline order;
- scenario-heading and day-metadata wrappers used by print;
- the data contract of eight independent-review inputs and exactly three unexecuted release scenarios.

These checks do not execute a model, browser layout engine, accessibility engine, viewport
matrix, screenshot comparison, touch-target calculation or Chromium error collection.

### Manual PR7 reference observations

Inspect in a normal desktop browser at minimum:

- 390×844 phone;
- 768×1024 tablet;
- 1440×900 desktop;
- 320 px narrow-width stress check;
- A4 print preview and Letter print preview.

Required representative states include summary, a normal day, a transfer-heavy day, a conflict, a stale item, optional-media loading/error, enhancement failure, external-connectivity labelling, Draft and both Final bases.

The following shared PR7 interaction and local-open checklist is entirely
`not_executed` until the corresponding browser observation is recorded. Static tests may
confirm that the necessary source hooks and fallback content exist, but do not satisfy or
partially execute any item in this checklist:

- Filters: exercise All days, unresolved items, weather-sensitive items, transfers and
  warnings one at a time; for every filter, record that detailed days and the day overview
  remain synchronized, then reset.
- Contents: open the Contents control and follow both a section link and a day link; record
  arrival at the labelled targets without obscured headings or focus.
- Scenarios: switch primary to backup and back; record the corresponding visible panel and
  the restrained screen-reader announcement for each change.
- Enhancement failure: induce an enhancement failure and record that the complete core
  document, both scenarios and normal links remain readable, with the failure notice kept
  concise and no generic replacement error screen.
- Local-open network boundary: open the artifact through `file://` with browser network
  evidence and record that initial load and automatic operation issue no HTTP(S) asset or
  fetch requests. Afterwards, activate representative labelled external links separately
  and record those user-initiated navigations as connectivity-dependent actions, not as
  automatic artifact dependencies.

The release scenario also records exactly two manual cross-surface smoke observations in PR7:
generate/download/open the shared HTML once in Chat web and once on mobile. Those two
observations are evidence within one cross-surface release scenario, not an automated device
matrix and not a claim of Codex validation.

### Responsive acceptance

- no horizontal page scrolling at any control width;
- no obscured anchor targets or focus rings;
- 44 px touch targets;
- route and day overview transform rather than scale down;
- safe-area spacing works on compact devices;
- long controls wrap without becoming ambiguous.

### Accessibility acceptance

- manual inspection finds no critical or serious accessibility barrier in the reviewed path;
- complete keyboard walkthrough succeeds;
- VoiceOver or equivalent screen-reader walkthrough covers summary, contents, one day, scenario switch and sources;
- contrast is measured for every token pair and state;
- 200% zoom and reduced-motion modes preserve all content and operations.

### Self-contained local-open acceptance

- open from `file://` in a normal desktop browser;
- capture the PR7 network evidence from the shared checklist: no automatic HTTP(S) asset or
  fetch requests on initial load or automatic operation;
- activate external links only as separate user actions and verify that they remain
  identifiable, labelled and explicitly connectivity-dependent;
- disable JavaScript and confirm complete core reading order and print content.

### Content edge cases

- 30 days and many regions;
- long place, hotel and activity names;
- Cyrillic, Latin and Japanese characters in the same block;
- zero, one and many warnings;
- missing budget, missing time and unknown price;
- stale source and two conflicting sources;
- long source titles and URLs;
- one day with many timeline events;
- primary scenario without a viable backup;
- no optional imagery;
- unusually long accessibility text or source note.

### Print acceptance

- no clipped or overlapping content;
- no blank print-preview pages;
- no orphan headings;
- no critical event divided across pages;
- repeated headers and page furniture are correct;
- greyscale remains comprehensible;
- source appendix URLs remain readable and selectable in browser print output.

## 21. Canonical-data boundaries

The HTML may display but must not author canonical values. This includes:

- booking and readiness state;
- budget figures and confidence;
- selected primary route;
- approval/finalisation state;
- warnings, blockers and open decisions;
- source verification date and conflict resolution;
- selected destination motif and image provenance when those become project assets.

The generated page must never instruct the user to edit the HTML to fix trip data. It should direct changes back to the trip workspace and regeneration workflow.

## 22. Explicit non-goals

- production renderer or skill implementation;
- implementation plan;
- backend, accounts or synchronisation;
- editable canonical statuses in HTML;
- in-trip “Today” mode;
- live timetable, weather or booking updates;
- embedded third-party interactive maps;
- overview pseudo-map;
- automatic country theming based on stereotypes;
- carousel/lightbox interactions beyond the simple 1–3-image day gallery;
- dark mode in the first release;
- redesign of the main Travel Planner architecture specification.

## 23. Self-review record

The completed design was reviewed against the four requested dimensions:

- **Contradictions:** the decorative postage stamp is explicitly separated from the Draft/Final status label and cannot replace the route; interactive scenario state cannot leak into print or canonical data; the overview pseudo-map remains excluded while narrowly scoped transfer sequences remain allowed.
- **Responsive behaviour:** the route, day overview, timeline/context rail, stamp and contents navigation all have explicit transformations; the 320 px and 30-day cases catch overflow and excessive-density failures.
- **Accessibility:** core content survives without JavaScript, semantic and keyboard behaviour is specified, state never relies only on colour, and print/local-file paths preserve meaning.
- **Scope:** no renderer, production HTML, implementation plan, backend or in-trip mode is introduced. This design task did not modify the main architecture specification; the approved document is linked into that specification by a separate integration step.

No unresolved contradiction blocks design approval. The destination object used inside the decorative stamp remains a per-trip content choice rather than a system-level visual decision.

## 24. Final design acceptance checklist

The design is ready for a later implementation plan when:

- the first screen communicates route, readiness and blockers without relying on the stamp or photography;
- every day can be understood and compared with its backup;
- critical constraints precede the decisions they govern;
- external links are contextual, honest about connectivity and printable;
- mobile, keyboard, screen-reader, local-file and print paths preserve the same core meaning;
- Draft/Final, stale, conflicting, unknown and blocker states cannot be confused;
- the 12-day Japan reference and 30-day/long-content cases receive the defined static and manual evidence;
- HTML remains a derived, non-authoritative representation of canonical YAML/Markdown.

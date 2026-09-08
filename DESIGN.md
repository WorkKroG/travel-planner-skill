---
name: Travel Planner
description: "Lemon and Cobalt — a bright travel guide with yellow destination openings and a continuous chronological line."
colors:
  paper: "#fffef8"
  heading-field: "#ffe785"
  ink: "#153369"
  ink-soft: "#3b5271"
  accent: "#1649b5"
  selected: "#1747ab"
  selected-ink: "#fff"
  checkpoint-field: "#fff0b7"
  timeline-line: "#acbee0"
  info-field: "#e7efff"
  heading-line: "#c2a844"
  line: "#d6dddf"
  danger: "#8b3028"
  danger-ink: "#7a281d"
  warning: "#70430c"
  attention-ink: "#65470f"
  success: "#355442"
  danger-field: "#fff0e8"
  attention-field: "#fff0b7"
  success-field: "#edf5ed"
  focus: "#1649b5"
typography:
  display:
    fontFamily: '"Avenir Next", "Segoe UI", sans-serif'
    fontSize: "clamp(2.75rem, 6vw, 4.5rem)"
    fontWeight: 750
    lineHeight: 1.04
    letterSpacing: "-0.035em"
  headline:
    fontFamily: '"Avenir Next", "Segoe UI", sans-serif'
    fontSize: "clamp(2rem, 4vw, 3rem)"
    fontWeight: 750
    lineHeight: 1.12
    letterSpacing: "-0.035em"
  title:
    fontFamily: '"Avenir Next", "Segoe UI", sans-serif'
    fontSize: "clamp(2.25rem, 6vw, 4.125rem)"
    fontWeight: 750
    lineHeight: 1.04
    letterSpacing: "-0.04em"
  day-number:
    fontFamily: '"Avenir Next", "Segoe UI", sans-serif'
    fontSize: "3.375rem"
    fontWeight: 750
    lineHeight: 1
    letterSpacing: "-0.035em"
  body:
    fontFamily: '"Avenir Next", Avenir, "Segoe UI", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: '"Avenir Next", Avenir, "Segoe UI", sans-serif'
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.65
  control:
    fontFamily: '"Avenir Next", Avenir, "Segoe UI", sans-serif'
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.4
  status:
    fontFamily: '"Avenir Next", Avenir, "Segoe UI", sans-serif'
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: 1.4
rounded:
  control: "6px"
  notice: "12px"
  photo: "12px"
  checkpoint: "12px"
  pill: "999px"
  circle: "50%"
spacing:
  1: "0.5rem"
  2: "1rem"
  3: "1.5rem"
  4: "2rem"
  6: "3rem"
  8: "4rem"
  10: "5rem"
components:
  button-document:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0.65rem 0.9rem"
  button-document-active:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.selected-ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0.65rem 0.9rem"
  lifecycle-pill:
    backgroundColor: "{colors.danger-field}"
    textColor: "{colors.danger-ink}"
    typography: "{typography.status}"
    rounded: "{rounded.pill}"
    padding: "0.2rem 0.7rem"
  contents:
    backgroundColor: "{colors.info-field}"
    textColor: "{colors.ink}"
    padding: "0 1rem"
  day-heading:
    backgroundColor: "{colors.heading-field}"
    textColor: "{colors.ink}"
    padding: "2rem"
  timeline-activity:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    padding: "0.375rem 0 0"
  checkpoint:
    backgroundColor: "{colors.checkpoint-field}"
    textColor: "{colors.ink}"
    rounded: "{rounded.checkpoint}"
    padding: "0.75rem 1rem"
---

# Design System: Travel Planner

## Overview

**Creative North Star: "Lemon and Cobalt"**

Travel Planner is a bright, readable travel guide. Lemon fields introduce the trip and each destination; cobalt links and time anchors carry the reader through warm paper. Large sans-serif place names, real photographs and a continuous timeline give each day a clear opening and a dependable reading rhythm.

The same visual language covers the whole document: cover, route overview, contents, days, open decisions, preparation, budget, risks, sources and footer. Controls stay in the reading flow. Information hierarchy comes from type, spacing, thin rules and a few purposeful color fields.

This document records the implemented shared template in `skills/travel-planner/assets/html/styles.css` and `itinerary.html.j2`, following the [approved September 7 visual specification](docs/superpowers/specs/2026-09-07-html-visual-redesign-design.md) and the one-day Hakone composition approved for the full template on September 8. The latter governs the three-fact header, larger circular markers, recorded day periods and closing source disclosure. It describes source-level properties; it does not record a completed browser review.

**Key Characteristics:**

- Lemon cover and destination openings on warm paper.
- Large sans-serif titles with cobalt actions and time anchors.
- Optional galleries inside the day opening, before compact facts.
- Continuous chronological lines with semantic outline SVG icons.
- Pale yellow checkpoints and pale blue navigation fields.
- Accessible reading with progressive controls and a complete print layout.

## Colors

The palette is sunny and legible, with deep blue text, clear cobalt actions and restrained semantic notices.

### Primary

- **Lemon / Heading Field:** Cover and day openings, plus budget-table headings.
- **Cobalt / Accent:** Links, route accents, scenario headings, activity titles and timeline time anchors.
- **Selected Cobalt / Selected Ink:** Selected or hovered buttons use cobalt fill with white text.
- **Focus:** The accent cobalt also supplies visible keyboard focus.

### Secondary

- **Checkpoint Field:** Pale yellow emphasizes a concrete decision inside the timeline.
- **Information Field:** Pale blue frames the contents, adjacent-day navigation and document footer.
- **Timeline Line:** Cool blue joins events and separates navigation, scenario and disclosure areas.
- **Heading Line:** Muted gold separates facts within yellow openings.

### Tertiary

- **Danger / Danger Ink / Danger Field:** Reddish borders and pale notices distinguish saved blockers, conflicting information and draft or inconsistent lifecycle labels.
- **Warning / Attention Ink / Attention Field:** Brown labels and yellow notices distinguish recheck, stale and unknown states, accepted concerns and unavailable-photo feedback.
- **Success / Success Field:** Green labels and pale green fills distinguish confirmed, ready and prepared-copy states; their text retains the specific meaning.

### Neutral

- **Paper:** Page, reading body and unselected controls.
- **Ink:** Main text and major section rules.
- **Soft Ink:** Explanations, dates, captions and metadata.
- **Line:** Quiet list and table dividers.

**The Meaning in Text Rule.** Color supports explicit labels, icons and document structure; it never establishes a status or resolves an uncertainty by itself.

## Typography

**Display Font:** Avenir Next, with Segoe UI and sans-serif fallbacks.

**Body and Label Font:** Avenir Next, with Avenir, Segoe UI and sans-serif fallbacks.

Both are CSS font stacks using available local fonts. The document downloads no web fonts, and exact letterforms can vary across devices.

### Hierarchy

- **Display:** The trip title, limited to 17ch on wide screens.
- **Headline:** Major document sections.
- **Title:** The day destination; closely led and balanced, with the day number aligned to its right.
- **Day Number:** A compact, bold chapter anchor in selected cobalt.
- **Body:** Continuous reading at a maximum measure of 72ch; day introductions use 1.125rem, 1.5 line height and a 48ch measure.
- **Label:** Event kinds, dates, captions and compact metadata in sentence case. Labels have no global uppercase or tracking treatment.
- **Control / Status:** Short labels with the stronger weights in the frontmatter.

Ordinary event headings use 1.25rem, weight 700 and 1.25 line height. Activity headings grow to `clamp(1.25rem, 3vw, 1.6875rem)`, use cobalt and keep 1.2 line height. Day-body copy uses 1.4 line height; supporting document prose retains 1.65. Times and monetary totals use tabular numerals.

**The Sans-Serif Rule.** Use the local sans-serif stacks throughout the guide; place names gain hierarchy through scale and weight.

**The Small-Type Boundary Rule.** Sub-body sizes are for short labels and metadata only, never for continuous reading.

## Layout

The cover, document shell and footer share a centred maximum width of 58rem, with a 1rem outer margin on wide screens. Main content is bounded at 54rem; paragraphs retain a 72ch maximum. The shell has 1rem horizontal padding; the cover uses `clamp(2rem, 5vw, 4rem)` padding. Sections use 4rem vertical spacing, and adjacent days have a 4rem gap.

A day opens with a yellow header padded by 2rem. The destination and date are on the left, two-digit day number on the right; introduction, optional gallery and three facts (overnight base, travel, load) follow. “How we’ll spend the day” introduces scenario controls and complete timelines. Source links, photo credits and last-check date sit in a closed native disclosure in the blue closing field, followed by previous/next links.

The timeline has separate time, icon and text columns: 5.5rem, 3.5rem and the remaining width, with 1.125rem gaps. A thin line connects the centres of circular markers. Adjacent recorded periods form reading groups without sorting events; unassigned events keep their own unlabelled group.

At and below 760px, the outer document fills the viewport with 1rem horizontal padding. Day openings reach its edges and retain the title/number arrangement. The day number shrinks to 2.75rem; time and icon columns narrow to 4.5rem and 3rem. Three-photo galleries, facts and supporting grids stack. At and below 460px, all galleries and scenario buttons stack; recorded times move above event text next to 2.625rem markers, following the same DOM reading order. Budget rows become labelled blocks. Long text wraps, and the CSS minimum page width is 20rem.

The contents remains a closed native disclosure in normal flow. Page anchors use smooth scrolling, with automatic scrolling restored for reduced-motion preferences.

## Elevation & Depth

The system uses no ambient drop shadows. Yellow openings, paper event bodies, blue closing fields and thin rules create separation. The narrow-screen route uses `inset 3px 0 0 var(--ink)` solely to draw its vertical rule.

**The Flat Document Rule.** Keep reading surfaces flat; use fields, rules and spacing to express hierarchy.

## Shapes

Major document surfaces and day openings have square edges. Buttons use restrained corners; photographs, notices and checkpoint text fields use soft corners. Status labels are pills. Timeline markers are outlined circles laid over the line; checkpoint text is inset in a separate pale yellow field.

## Components

### Buttons and Scenario Tabs

Buttons have paper fill, ink text, a one-pixel timeline-colored border and a minimum height of 2.75rem. Hover, `aria-pressed="true"` and `aria-selected="true"` apply selected cobalt with white text. Keyboard focus has a three-pixel cobalt outline with a three-pixel offset; there is no animated lift or scaling.

The existing day filters cover all days, unresolved bookings, weather, transfers and warnings. Scenario tabs appear only when full alternatives exist. They retain text labels and semantic SVGs, `tablist` / `tab` / `tabpanel` relationships, selected state, roving focus, ArrowLeft/ArrowRight/Home/End navigation and polite live announcements. There is no search field or theme selector.

### Status Labels and Notices

Status pills have a current-color border, compact sentence-case text and semantic fills. Saved blockers use bordered pale notices with explicit severity, affected items and unresolved state. Accepted concerns retain their recorded meaning and acceptance text. Lifecycle labels remain separate from verification text.

### Navigation and Supporting Sections

The closed contents disclosure uses a pale blue field and a bold summary with a menu icon. Its links form two columns on wide screens and one on compact screens. The route uses a horizontal sequence that becomes vertical on compact screens. Open decisions, preparation, risks and sources use divided reading rows. Budget totals use a two-column summary and a yellow-headed table. The footer repeats document provenance in a blue field.

### Day Galleries

A day has zero to three ordered photographs. No gallery markup is emitted when there are none. The gallery sits inside the yellow header after the introduction and before compact facts; it is never a trailing appendix.

| Photos | Wide-screen composition | Image aspect ratio |
| --- | --- | --- |
| 1 | One full-width photograph | 2.8 / 1 |
| 2 | Two equal photographs | 1.42 / 1 |
| 3 | Three equal photographs | 1.3 / 1 |

The gap is 0.75rem, photographs use the photo radius and `object-fit: cover`. At 760px, photographs use a 1.9 / 1 ratio and three-photo galleries stack; two-photo galleries stack at 460px. Captions remain below each photograph. Attribution, license and source links move to the day disclosure and its independent print projection. Images are embedded, with dimensions, lazy loading and asynchronous decoding hints. A decoding failure shows a localized fallback while caption and provenance remain available; native alt text is retained without JavaScript.

### Timelines and Checkpoints

Each contiguous event group is an ordered list. Bundled decorative SVGs distinguish event kinds; optional recorded icons add coffee, bus, train, mountain, museum, onsen, craft and weather imagery. Event-kind text remains available to assistive technology. Icons are 2rem inside 3.5rem outlined circular markers on wide screens.

Events retain their recorded order and displayed times, including unknown values. Morning, afternoon and evening groups appear only from optional recorded `period` annotations; the renderer never guesses from titles, IDs or times. Links and local alternatives remain inside their event; full scenarios retain their own timelines. Links use simple underlined text while preserving the shared minimum touch target.

Checkpoint copy sits in a pale yellow text field beside a brown marker. A compact definition list states what to check and how to adjust the plan.

### Reading Without JavaScript and Printing

Without JavaScript, enhancement controls are hidden, all full timelines remain visible and event alternatives start expanded. The contents disclosure and anchors remain native controls. If enhancement initialization fails, the template has an explicit notice and restores scenario and alternative visibility. No external icon library, host global or browser runtime package is required.

Print CSS uses A4 portrait, a white page, 10.5pt body text and clear rules. The cover and each day start separate page sections. Filters, scenario controls, contents and adjacent-day navigation are removed; all days, scenarios and event alternatives are included regardless of screen selection. Event context, source URLs, linked-action URLs and document provenance are printed. Critical groups avoid internal page breaks, and table layout is restored.

Gallery printing follows the existing print-images option. When enabled, one photo fills its row and multiple photos use two columns; images preserve their full proportions, lose rounded corners and keep caption, attribution, license and source ID. This is browser Print behavior, with PDF saving performed by the reader.

## Do's and Don'ts

### Do:

- **Do** apply Lemon and Cobalt consistently across the whole document.
- **Do** preserve a bounded reading column, clear day openings and continuous time anchors.
- **Do** place zero to three real photographs inside the day header and preserve their order and provenance.
- **Do** keep meaning in text alongside color and semantic icons.
- **Do** preserve full reading content without JavaScript and in print.

### Don't:

- **Don't** restore the mineral/maple palette, alternating day tints or serif headings.
- **Don't** introduce permanent side rails, sticky indexes or floating reading cards.
- **Don't** move galleries below the timeline or add empty photo placeholders.
- **Don't** add search, a theme selector, remote fonts or an external icon runtime.
- **Don't** invent event times, day-phase groups or missing photographs to fit the composition.

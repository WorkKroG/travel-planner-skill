---
name: Travel Planner
description: "Curated Route — a calm editorial travel guide shaped by mineral, maple, and warm paper."
colors:
  mineral-margin: "#edf1ec"
  warm-paper: "#fffdf7"
  deep-teal: "#173c44"
  maple: "#a93f2e"
  brass: "#9b6b12"
  moss: "#496b58"
  soft-ink: "#456068"
  quiet-line: "#bdcac6"
  focus-blue: "#075fa8"
  maple-wash: "#fff0ea"
  brass-wash: "#fff7da"
  moss-wash: "#edf5ed"
typography:
  display:
    fontFamily: '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", Georgia, serif'
    fontSize: "clamp(3rem, 7vw, 5.8rem)"
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: "-0.025em"
  headline:
    fontFamily: '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", Georgia, serif'
    fontSize: "clamp(2rem, 4vw, 3.25rem)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.025em"
  title:
    fontFamily: '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", Georgia, serif'
    fontSize: "clamp(2rem, 4vw, 3.4rem)"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.025em"
  body:
    fontFamily: 'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: 'Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "0.78rem"
    fontWeight: 750
    lineHeight: 1.2
    letterSpacing: "0.06em"
rounded:
  control: "8px"
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
    backgroundColor: "{colors.warm-paper}"
    textColor: "{colors.deep-teal}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0.55rem 0.9rem"
    height: "2.75rem"
  button-document-active:
    backgroundColor: "{colors.deep-teal}"
    textColor: "{colors.warm-paper}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0.55rem 0.9rem"
    height: "2.75rem"
  lifecycle-pill:
    backgroundColor: "{colors.maple-wash}"
    textColor: "{colors.maple}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0.2rem 0.7rem"
    height: "2rem"
  day-chapter:
    backgroundColor: "{colors.mineral-margin}"
    textColor: "{colors.deep-teal}"
    padding: "clamp(2rem, 5vw, 4.5rem) clamp(1rem, 4vw, 3rem)"
  checkpoint:
    backgroundColor: "{colors.maple-wash}"
    textColor: "{colors.maple}"
    padding: "1.5rem"
---

# Design System: Travel Planner

## Overview

**Creative North Star: "The Curated Route"**

Travel Planner is an editorial travel guide, not a dashboard. Warm paper sits inside cool mineral margins, deep teal supplies the document's structure, and Source Serif gives route and day headings the authority of a carefully edited journey book. The mood is calm, literate, useful, and quietly crafted.

The interface earns attention through pacing rather than chrome: bounded reading widths, generous sectional pauses, crisp rules, and repeating day chapters. Controls remain modest and in flow. Color carries hierarchy sparingly, while maple appears with force only when the document must tell the truth about a checkpoint or consequential state.

**Key Characteristics:**

- Editorial reading flow with a bounded paper sheet.
- Mineral and warm-paper material contrast.
- Deep-teal structure with rare, semantic maple emphasis.
- Serif-led hierarchy paired with practical sans-serif controls.
- Day chapters separated by generous rhythm and quiet tinted fields.
- Progressive controls that recede behind the guide itself.

## Colors

The palette feels botanical and archival: cool mineral, inked teal, warm paper, and restrained natural accents.

### Primary

- **Deep Teal:** The structural ink for body copy, major rules, controls, and primary interaction states.
- **Mineral Margin:** The cool page surround and the first field in the repeating day-chapter sequence.

### Secondary

- **Maple:** The consequential accent, reserved for checkpoints, blocking truth, and document states that demand attention.
- **Maple Wash:** A warm, pale field that keeps consequential content readable without turning it into an alarm panel.

### Tertiary

- **Quiet Brass:** A restrained signal for stale, unknown, recheck, and optional-media fallback states.
- **Moss:** A calm confirmation accent for ready and confirmed states.
- **Focus Blue:** A dedicated accessibility accent for visible keyboard focus, not a general brand color.

### Neutral

- **Warm Paper:** The principal reading surface and default control fill.
- **Soft Ink:** Supporting text, metadata, captions, and explanatory copy.
- **Quiet Line:** Dividers and low-emphasis structural boundaries.
- **Brass Wash:** The pale field paired with brass notices.
- **Moss Wash:** The pale field paired with confirmed states.

### Named Rules

**The Maple Reserve Rule.** Use maple only for checkpoints, lifecycle truth, and blocking information; its rarity is what gives it authority.

**The Quiet Accent Rule.** Brass communicates review and uncertainty, moss communicates confirmation, and focus blue belongs only to keyboard focus.

## Typography

**Display Font:** Source Serif 4, with Iowan Old Style, Palatino Linotype, Georgia, and serif fallbacks
**Body Font:** Inter, with system sans-serif fallbacks
**Label Font:** Inter, with system sans-serif fallbacks

**Character:** The serif is cultivated and literary without becoming nostalgic; the sans-serif is compact, neutral, and exact. Together they make the artifact feel edited rather than app-like.

### Hierarchy

- **Display:** The trip title; large, closely led, balanced, and constrained to a short measure.
- **Headline:** Major document sections; authoritative but quieter than the cover.
- **Title:** Day-region chapter titles and other strong editorial moments.
- **Body:** The continuous reading voice; keep prose at a comfortable measure of no more than 72 characters.
- **Label:** Uppercase event kinds, facts, statuses, and metadata; compact, tracked, and used in short phrases only.

### Named Rules

**The Two-Voice Rule.** Serif carries narrative hierarchy and route character; sans-serif carries reading copy, metadata, controls, and audit detail.

**The Small-Type Boundary Rule.** Sub-body sizes are for short labels and metadata only, never for continuous reading.

## Layout

The page is a centred document with two nested bounds: the cover and footer can extend to 88rem, the paper shell stops at 76rem, and primary content stops at 68rem. Long prose stays within 72ch. A compact, closed contents disclosure remains in normal flow; there are no permanent side rails or fixed navigation controls.

The spatial rhythm follows the seven-step spacing scale, with large pauses between sections and day chapters and small, regular increments within events. Day chapters may bleed slightly into the shell padding so their tinted fields read as chapter boundaries, while their text remains aligned to the reading column.

At and below 760px, all grids resolve to one reading column. Day metadata stacks, the timeline time moves above event content with a visible label, the route becomes a vertical sequence, tabular data becomes labelled blocks, and every interactive target retains a 2.75rem minimum height. The page remains usable from 320 CSS px without horizontal page scrolling.

**The Chapter Boundary Rule.** Every day begins with a strong top rule, number, date, place, and thesis, then ends with a closing navigation rule and generous space.

## Elevation & Depth

The system is flat by design and uses no ambient drop shadows. Depth comes from the contrast between mineral margins and warm paper, alternating chapter fields, border weight, and the overlap implied by slight chapter bleeds. The inset rule on the narrow-screen route sequence is structural, not elevation.

**The Flat Document Rule.** Never float core reading surfaces as shadowed app cards; use tonal fields, rules, and spacing to express hierarchy.

## Shapes

The form language is mostly rectilinear and editorial. Reading surfaces, warnings, chapters, and route structures keep square edges; restrained controls use gently curved corners (8px). Lifecycle labels use a full pill, and timeline or route markers use true circles. Borders are deliberate and usually one pixel, becoming heavier only for chapter starts or consequential states.

**The Square Page Rule.** Rounded geometry belongs to controls and compact statuses, not to the paper sheet or major content containers.

## Components

### Buttons

- **Shape:** Restrained control corners with a 2.75rem minimum height.
- **Primary:** Warm-paper fill, deep-teal text and border, compact sans-serif label, and modest horizontal padding.
- **Hover / Focus:** Hover, pressed, and selected states reverse to deep teal on warm paper; keyboard focus uses the dedicated blue outline with clear offset.
- **Active:** Active controls may retain the reversed state, but should not gain shadow or scale effects.

### Chips

- **Style:** Full pills with a fine current-color border, uppercase tracked label, and a pale semantic wash.
- **State:** Maple marks blocking or draft truth, moss marks confirmed or ready truth, and brass marks stale, unknown, or recheck truth.

### Cards / Containers

- **Corner Style:** Square-edged document fields and list blocks.
- **Background:** Warm paper for the reading sheet; mineral, pale maple, and pale brass for the repeating day sequence.
- **Shadow Strategy:** No ambient shadow; see the Flat Document Rule.
- **Border:** Fine quiet-line dividers, deep-teal section rules, and heavier maple rules only for consequential content.
- **Internal Padding:** Follow the spacing scale; chapter fields use substantially more air than list rows.

### Inputs / Fields

- **Style:** Warm-paper fill, deep-teal one-pixel stroke, restrained control corners, and full body typography.
- **Focus:** A three-pixel focus-blue outline with a three-pixel offset.
- **Disabled:** If introduced, retain legible text and structure; never communicate state through opacity alone.

### Navigation

The contents is a native disclosure with deep-teal block rules, a bold summary row, and link rows separated by quiet lines. Adjacent-day navigation is an in-flow text pair at the end of each chapter. Navigation never becomes a permanent rail or overlays the reading column.

### Day Chapters and Timelines

Day chapters repeat mineral, pale maple, and pale brass fields as structural rhythm, never as semantic status. A large serif day number anchors a typed, chronological timeline. Wide layouts retain a prominent time column; narrow layouts place the labelled time above event copy. Links and alternatives stay inside the event they describe.

### Checkpoints

Checkpoints interrupt the timeline with maple wash, stronger horizontal rules, and a compact two-part contract. They are the visual high point of a day and should remain rare enough to be unmistakable.

## Do's and Don'ts

### Do:

- **Do** preserve a centred, bounded reading column with generous chapter spacing.
- **Do** use deep teal for structure and warm paper for sustained reading.
- **Do** keep controls restrained, accessible, and subordinate to the itinerary.
- **Do** use chapter tints as rhythm while keeping meaning in text, labels, and structure.
- **Do** reserve maple emphasis for checkpoints and consequential lifecycle truth.

### Don't:

- **Don't** introduce permanent dashboard rails, sticky indexes, or fixed navigation furniture.
- **Don't** turn each fact or event into a rounded, shadowed card.
- **Don't** use maple as a general decorative accent.
- **Don't** use small label typography for paragraphs or essential instructions.
- **Don't** let optional imagery or controls compete with the chronological reading flow.

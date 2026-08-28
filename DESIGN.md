---
name: Travel Planner — Curated Route
description: An evidence-first itinerary document shaped like a contemporary museum guide.
colors:
  mineral: "#edf1ec"
  warm-paper: "#fffdf7"
  deep-teal: "#173c44"
  maple: "#bd4a36"
  brass: "#d1a044"
  moss: "#496b58"
  soft-ink: "#456068"
  divider: "#bdcac6"
  focus-blue: "#0b67b2"
  critical-text: "#8c2d20"
  ready-text: "#355442"
  stale-text: "#68501a"
  critical-wash: "#fff1ec"
  warning-wash: "#fff4ef"
  ready-wash: "#edf5ed"
  attention-wash: "#fff7db"
typography:
  display:
    fontFamily: '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", Georgia, serif'
    fontSize: "clamp(3rem, 7vw, 6rem)"
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: "-0.025em"
  headline:
    fontFamily: '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", Georgia, serif'
    fontSize: "clamp(2rem, 4vw, 3.5rem)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.025em"
  title:
    fontFamily: '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", Georgia, serif'
    fontSize: "clamp(1.4rem, 2.5vw, 2rem)"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  thesis:
    fontFamily: '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", Georgia, serif'
    fontSize: "clamp(1.25rem, 2.2vw, 1.65rem)"
    fontWeight: 600
    lineHeight: 1.45
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
  structural: "0"
  control: "8px"
  floating: "12px"
  pill: "999px"
spacing:
  space-1: "0.5rem"
  space-2: "1rem"
  space-3: "1.5rem"
  space-4: "2rem"
  space-6: "3rem"
  space-8: "4rem"
components:
  button-default:
    backgroundColor: "{colors.warm-paper}"
    textColor: "{colors.deep-teal}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0.55rem 0.9rem"
    height: "2.75rem"
  button-selected:
    backgroundColor: "{colors.deep-teal}"
    textColor: "{colors.warm-paper}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0.55rem 0.9rem"
    height: "2.75rem"
  search-field:
    backgroundColor: "{colors.warm-paper}"
    textColor: "{colors.deep-teal}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "0.65rem 0.9rem"
    height: "2.75rem"
  status-draft:
    backgroundColor: "{colors.critical-wash}"
    textColor: "{colors.critical-text}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0.2rem 0.7rem"
  status-final:
    backgroundColor: "{colors.ready-wash}"
    textColor: "{colors.ready-text}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0.2rem 0.7rem"
  summary-panel:
    backgroundColor: "{colors.mineral}"
    textColor: "{colors.deep-teal}"
    rounded: "{rounded.floating}"
    padding: "1.5rem"
  warning-block:
    backgroundColor: "{colors.warning-wash}"
    textColor: "{colors.deep-teal}"
    rounded: "{rounded.structural}"
    padding: "1rem 1.5rem"
---

# Design System: Travel Planner — Curated Route

## Overview

**Creative North Star: "The Curated Route"**

Curated Route makes feasibility legible before decoration. Its visual world combines the calm pacing of a contemporary museum guide with the evidentiary discipline of a planning dossier: warm paper holds the narrative, deep-teal rules establish order, and restrained autumn accents identify warnings, uncertainty, and readiness without turning the document into a metric dashboard.

The story begins with identity and judgement. In the first viewport, a large editorial trip title and a text route carry the main column; readiness, budget confidence, the highest-priority blockers, and a small destination-specific stamp form a supporting rail. From there the reader reviews all days and open decisions, compares primary and backup scenarios, then verifies preparation, budget, risks, provenance, and document version. Controls remain secondary to the reading flow and never imply that the derived HTML can mutate canonical trip data.

The world is calm, exact, and place-aware, but never themed. Evidence, uncertainty, offline truth, and print legibility outrank atmosphere. The baseline implementation is the authority for density and responsive transformations; the approved interactive-itinerary specification is the authority for intent.

**Key Characteristics:**

- Editorial hierarchy on warm paper, organised by deep-teal rules rather than card grids.
- A route-first first viewport that answers identity, sequence, readiness, blockers, and next action quickly.
- Restrained maple, brass, and moss accents paired with text, icons, and shape so state never depends on hue alone.
- Progressive enhancement: the complete document survives missing JavaScript, media, and network access.
- One information model expressed deliberately across wide, compact, and print compositions.

**The Evidence Before Atmosphere Rule.** Route, constraints, readiness, blockers, and provenance appear before decorative imagery or flourish.

## Colors

Mineral and Maple is a quiet, high-contrast palette: a cool mineral surround frames warm paper pages, deep teal supplies the document's structural voice, and autumn accents are reserved for meaningful state.

### Primary

- **Deep Teal:** Primary text, document rules, route structure, active controls, and mobile contents chrome. It is the system's dominant voice.
- **Warm Paper:** The readable document surface and default control fill. It keeps long-form content warmer and less clinical than pure white.

### Secondary

- **Maple:** Actions, day-number accents, stamp linework, blockers, and critical leading rules. Its rarity preserves urgency.
- **Muted Brass:** Attention, stale/recheck states, and enhancement-failure borders.
- **Moss:** The confirmed/ready family and its semantic direction, always reinforced by wording.

### Neutral

- **Mineral:** The page surround, summary-panel surface, image placeholder, and subtle environmental texture.
- **Soft Ink:** Secondary metadata, captions, network labels, and explanatory text.
- **Divider:** Quiet separators inside lists, timelines, contents, and tables.
- **Focus Blue:** A deliberately distinct keyboard focus ring that remains visible against both paper and tinted surfaces.
- **State Washes:** Critical, warning, ready, and attention washes create restrained semantic fields behind explicit labels.

**The One Structural Voice Rule.** Deep teal owns structure; accent colors identify meaning and never compete as equal navigation colors.

**The Paired-State Rule.** Draft, Final, stale, conflict, blocker, unknown, and offline states use text plus icon or shape in addition to color.

## Typography

**Display Font:** Source Serif 4, with Iowan Old Style, Palatino Linotype, Georgia, and serif fallbacks.

**Body Font:** Inter, with the local system sans-serif stack as fallback.

**Character:** The serif makes trip identity, route theses, and section openings feel editorial and considered. The sans-serif keeps controls, evidence, metadata, times, prices, and status precise. Fonts are local or system-resolved; the document makes no runtime font request and tolerates substitution, including mixed Latin, Cyrillic, and Japanese text.

### Hierarchy

- **Display** (600, responsive 3–6rem, 0.98 line height): One trip title, balanced and capped near 13 characters per line on wide screens.
- **Headline** (600, responsive 2–3.5rem, 1.08 line height): Major document sections with decisive whitespace above and below.
- **Title** (600, responsive 1.4–2rem, 1.2 line height): Day headings and significant local sections.
- **Thesis** (600, responsive 1.25–1.65rem, 1.45 line height): Short route and day propositions; never a substitute for body detail.
- **Body** (400, 1rem, 1.65 line height): Reading copy with a general maximum of 72ch.
- **Label** (750, 0.78rem, 0.06em tracking, uppercase where semantic): Statuses, day numbers, scenario kinds, and table headings.
- **Numeric data:** Times, durations, prices, counts, and date-sensitive values use tabular numerals.

**The Two-Voice Rule.** Serif establishes narrative importance; sans-serif carries operation and evidence. Do not introduce a third decorative type voice.

## Layout

The web artifact is a warm-paper document inside a mineral surround. Its shell is capped at 90rem with a 1rem outer gutter. The wide hero is a split composition: a 1.6fr narrative field and a 0.7fr evidence rail, separated by a fluid 2–6rem gap. The title, thesis, text route, and review links lead; the stamp, readiness, budget, and blockers support them. A faint fixed registration line at 6% of the viewport gives the surround a printmaking character without becoming content.

Below the hero, the wide document uses a 16rem sticky contents column and a flexible reading column. Major sections are separated by rules and 4rem vertical intervals rather than boxed into cards. Detailed days use a main timeline plus a narrow context rail; critical constraints sit in that rail beside the events they govern. The route sequence is horizontal and text-first on wide screens, while overview rows behave like an editorial index rather than a dashboard table.

### Responsive composition

- **Wide (1024px and above):** Keep the split first viewport, sticky left contents, route sequence, and two-column day anatomy.
- **Medium (640–1023px):** Move contents into normal flow, arrange its links in three columns, collapse detailed days to one column, and place constraints before the timeline.
- **Compact (below 640px):** Use a single reading column. The stamp becomes a 3.25rem accent at the title's upper right; route stops become a vertical ruled sequence; overview rows and budget tables stack; contents becomes a 52px bottom control after the hero and respects the bottom safe area.
- **Narrow stress case (320px):** Preserve 16px body text, 14px secondary text, 44px targets, complete labels, and zero horizontal page scrolling. Transform structures rather than scaling them down.

### Print and PDF composition

Print is an alternate composition of the same information model. It targets A4 portrait with 16mm/14mm/18mm page margins, uses white and near-black for reliable output, and keeps trip title/status plus page numbers in page furniture where the engine supports them. The hero becomes a cover and breaks after page one. Contents, search, filters, day navigation, skip links, and button chrome disappear; both scenarios print together; day articles begin on new pages; critical blocks and timeline events avoid internal breaks. External links append stable source identifiers, and images print only when the renderer explicitly enables them.

**The Transform, Don't Shrink Rule.** At each breakpoint, route, overview, timeline, contents, and budget change composition; they do not become miniature desktop UI.

## Elevation & Depth

The system is flat by default. Hierarchy comes from paper-versus-mineral layering, strong rules, whitespace, and tinted semantic fields. Soft teal ambient shadows are reserved for floating summary panels and the compact contents control/menu; they communicate an element that sits above the reading plane, not a generic card style. The desktop summary shadow is broad and quiet; compact shadows tighten, while the mobile contents control receives the strongest elevation because it floats over the document.

**The Flat Document Rule.** Major sections, route structures, tables, timelines, and list items stay flat; a shadow must correspond to actual floating behavior.

## Shapes

The form language distinguishes document structure from controls. Major sections, route structures, tables, warnings, and scenario panels have square corners. Native controls use gently rounded 8px corners. Only floating desktop summary panels use 12px corners. Short statuses and compact filter chips may use the full pill. Warnings remain straight-edged with a strong 4px maple leading rule, while route nodes use small circles only when the sequence becomes vertical.

### Earned exceptions

- Compact summary panels reduce from 12px to 8px because they join the dense single-column flow rather than floating as a separate rail.
- The decorative stamp alone may rotate by 3 degrees; other panels remain aligned to the document grid.
- Tight 4px gaps are allowed only for internal alignment, such as stacked timeline copy; the reusable spacing scale otherwise begins at 8px.
- Print deliberately switches the screen palette to white and near-black for economical, dependable output while preserving state through labels and rules.

**The Radius Has Meaning Rule.** Square means document structure, 8px means control, 12px means floating summary, and full pill means compact state.

## Components

### Buttons and filters

- **Shape:** 8px corners, a 1px deep-teal border, and a minimum 44px height.
- **Default:** Warm paper with deep-teal text; compact, bold sans-serif label.
- **Hover / selected:** Deep teal fills the control and reverses text to warm paper. `aria-pressed` exposes selection independently of color.
- **Focus:** A 3px blue outline with 3px offset remains unclipped and distinct from hover/selected state.

### Search field

The search field is an ordinary native search input with a paper fill, deep-teal 1px stroke, 8px corners, 44px minimum height, and a visible label for assistive technology. Search filters the day overview and detailed day articles together; the result count is announced politely. An empty result is explicit and offers a reset action.

### Status chips

Statuses are bordered full pills with compact uppercase labels. Draft/blocking/conflicting, Final/confirmed/ready, and stale/recheck/unknown families each use their own text and wash pairing. Status names remain visible in headings, furniture, and print; icons supplement but never replace wording.

### Summary panels

Readiness and budget panels are the only recurring floating cards. On wide screens they use a mineral fill, 12px corners, 1.5rem internal padding, and a low ambient shadow. On phones they compact to 8px corners and tighter padding. Their serif value line gives one judgement at a glance; blockers stay outside these panels so a reassuring count cannot conceal them.

### Warning and constraint blocks

Warnings are square, pale-maple fields with a 4px maple leading rule and explicit severity text. Critical constraints use the same grammar and appear before or beside the timeline event they govern. They never sit below optional photography.

### Route sequence and day overview

The route is semantic text, not a pseudo-map. Wide route stops share a strong top rule with restrained arrow joints; compact stops become a vertical deep-teal rule with paper-and-maple nodes. Day overview rows are ruled, linkable index entries. On phones each row becomes a two-column stack without hiding the thesis, travel/load information, or state.

### Timeline and scenario comparison

Timeline events use a fixed time column with tabular numerals and a flexible description column; compact screens stack time above description. Scenario controls are view-only pressed buttons. The primary scenario is selected initially when JavaScript runs, screen readers receive a textual announcement, and print forces both primary and backup panels visible.

### Contents navigation

Wide contents are sticky and quiet, built from native disclosure and anchor links. Medium contents return to normal document flow. Compact enhanced contents become a fixed deep-teal bottom control only after the hero has passed; without JavaScript, the same links remain visible near the top. Anchor targets reserve scroll space so headings and focus rings are not obscured.

### Failure and offline states

If enhancement fails, hide only the unavailable enhanced controls and show a concise brass-bordered notice; the itinerary remains readable. If optional media fails, remove the broken image and show a mineral text fallback while preserving any useful caption. External links keep recognizable destinations and explicit “Internet required” labels. There is no loading shell or generic error screen for the self-contained core document.

**The Derived Artifact Rule.** Search, filters, disclosure, and scenario switching change only the local view; no component authors booking, readiness, decision, budget, or Final status.

## Do's and Don'ts

### Do:

- **Do** lead the first viewport with trip identity, text route, readiness, blockers, budget confidence, and clear next links.
- **Do** use the 8px rhythm, 32–64px section separations, and rules to create editorial pacing.
- **Do** keep body copy readable at 16px or larger on phones, secondary copy at 14px or larger, and controls at least 44×44 CSS px.
- **Do** pair every state color with explicit wording and, where useful, the shared outline icon vocabulary.
- **Do** preserve semantic landmarks, logical heading order, keyboard access, a 3px visible focus ring, 200% zoom, and reduced-motion behavior.
- **Do** keep core content, navigation, primary and backup information, and print meaning available without JavaScript or network access.
- **Do** place one representative image only when it supports a decision, with reserved dimensions, provenance, and appropriate alternative text.

### Don't:

- **Don't** turn the itinerary into a generic dashboard, a grid of interchangeable rounded cards, or an AI-gradient interface.
- **Don't** introduce an overview pseudo-map, horizontal route scrolling, decorative transport glyph clouds, mixed icon families, or emoji status markers.
- **Don't** let photography, the stamp, readiness percentages, or atmosphere precede or conceal a blocker, cut-off, unresolved decision, or source conflict.
- **Don't** use hover, color, switched scenario state, or an external link as the sole carrier of critical information.
- **Don't** add runtime font, icon, media, CSS, script, or map dependencies to the self-contained artifact.
- **Don't** persist view preferences as canonical data or imply that editing the HTML changes the trip workspace.
- **Don't** add parallax, route animation, skeleton screens, generic error pages, or decorative motion; transitions remain functional, brief, and removable under reduced motion.

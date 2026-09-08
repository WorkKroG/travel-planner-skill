# Travel Planner

Travel Planner is an open-source, skills-only plugin for people planning complex trips with several destinations, constraints, transport decisions, bookings, and travellers. It guides the organiser from an incomplete brief through research, route selection, detailed days, readiness, deterministic checks where available, and a shareable itinerary.

The workflow is intentionally collaborative:

1. Create one explicit workspace for one trip.
2. Clarify dates, travellers, hard constraints, preferences, and decision ownership.
3. Research candidates with source, freshness, confidence, and uncertainty metadata.
4. Compare meaningful route alternatives and record the user's decision.
5. Detail days, transfers, buffers, budget, readiness, and backup scenarios.
6. Run the verification available on the current surface.
7. Produce one responsive, self-contained HTML itinerary for review and sharing.

The complete product contract is in [PRODUCT.md](PRODUCT.md), the component boundary is in [ARCHITECTURE.md](ARCHITECTURE.md), and the implemented visual system is in [DESIGN.md](DESIGN.md). The [Readable Itinerary Days specification](docs/superpowers/specs/2026-09-06-itinerary-readable-days-design.md) defines HTML behavior over the retained requirements of the [original interactive itinerary specification](docs/superpowers/specs/2026-08-28-interactive-itinerary-html-design.md). Historical design and implementation plans record earlier decisions; [project status](docs/PROJECT_STATUS.md) identifies what is merged and what remains unverified.

## Supported surfaces

Availability of a source or local marketplace can vary by surface. The table describes behavior when this plugin is available; it does not claim that this repository is already listed in every product.

| Surface | Workflow and output | Verification limit |
| --- | --- | --- |
| Codex | Complete workflow, canonical bundle, recorded-data checks, exact expense subtotals, and shared HTML | `codex_validated` requires an actual successful data check; it does not confirm trip feasibility |
| ChatGPT Chat/Work | Core planning workflow and the same self-contained HTML template | `none` or explicitly limited `ai_reviewed`; never claim Codex validation without the helper |
| Mobile | Core planning workflow and the same self-contained HTML template, subject to file capabilities on the device | `none` or explicitly limited `ai_reviewed`; manual bundle transfer and human review required |

`brief.yaml.document_language` selects `en` or `ru` for the whole generated document. Prepared-copy labels and every other renderer-owned label follow that choice. They describe document preparation, not a verified trip.

## Package and trip data

This repository contains one plugin manifest and one skill tree:

```text
.codex-plugin/plugin.json
skills/travel-planner/
```

There is no app, MCP server, backend, account, or synchronization service. The Python package in `pyproject.toml` installs internal deterministic helpers for Codex and local development; it is not a separate PyPI product or stable public API.

Each trip has five canonical files:

- `brief.yaml`
- `candidates.yaml`
- `itinerary.yaml`
- `readiness.yaml`
- `decisions.md`

When days reference local photographs, their files in `media/` are also canonical and must travel with those five files. Each photograph records its source, attribution, license, caption, alt text and dimensions. Photograph licenses are separate from the repository's MIT license.

`sources.md` and `outputs/` are generated and can be rebuilt. The generated HTML embeds available local photographs and can be shared as one file; resuming or rebuilding the trip requires the canonical bundle, including referenced media.

Draft and Prepared copy are document lifecycle labels, independent of verification. The internal value `document_status: final` retains the `codex_validated` or `user_confirmed` preparation basis. Open decisions, unknowns, and saved concerns remain visible in either copy; individual risk acceptance is not required to issue it. Any actual acceptance stays auditable and never erases the original concern.

Recorded expense subtotals stay separate by currency and per-person/per-group basis. No FX conversion or multiplication by traveller count is performed. Incomplete rows retain their known values and explain why they were excluded from arithmetic; unknown amounts never become zero.

## Get the source and validate it locally

The currently validated distribution path is a source checkout. It has been tested with Python 3.12 as follows:

```sh
git clone https://github.com/WorkKroG/travel-planner-skill.git
cd travel-planner-skill
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

The plugin root also passes the current `skill-creator` and `plugin-creator` validators when staged under a folder named `travel-planner`.

For local plugin testing, follow OpenAI's current [plugin packaging](https://developers.openai.com/plugins/build/plugins) and [connect-and-test](https://developers.openai.com/plugins/deploy/connect-chatgpt) guidance: add this existing plugin folder to a local marketplace, then install it from that local source and start a new conversation. ChatGPT Work guidance is also available in [Build plugins](https://learn.chatgpt.com/docs/build-plugins). This repository deliberately does not install or modify a personal marketplace for you.

A local installation loads a [cached copy of the plugin](https://developers.openai.com/plugins/build/plugins#how-local-marketplaces-work), not the source checkout. After updating the source, make sure the installed copy contains the same skill, references and assets before testing in a new conversation. Updating Git alone does not establish that the installed plugin is current.

Repository availability is not universal publication. A public listing in the shared ChatGPT and Codex plugin directory is a later external submission and review action. No one-click GitHub installation or identical local-marketplace availability across desktop, web, and mobile is promised.

## Internal helper commands

These commands are internal to the plugin and may change before a stable public interface exists:

```sh
.venv/bin/travel-planner init /path/to/trip --title "Japan, November 2026" --trip-id japan-2026 --confirm-path
.venv/bin/travel-planner check /path/to/trip
.venv/bin/travel-planner render /path/to/trip --output /path/to/trip/outputs/itinerary.html --at 2026-08-30T09:00:00+00:00
```

Replace the path, title, ID and `--at` timestamp with the values for your trip. `--at` records the HTML generation time; it does not recheck external sources or recalculate their freshness. Temporary smoke tests must use a new temporary workspace.

`init` never overwrites an existing trip. `check` verifies recorded dates, IDs, typed day events and scenarios, declared references, present monetary values, and document-status consistency. It does not evaluate overall trip feasibility. `render` reads the same valid data and creates a one-column self-contained itinerary with chronological meal/transport/activity/checkpoint events, contextual links and alternatives, and complete alternative day scenarios.

Each day uses the approved Lemon and Cobalt composition: a yellow destination header, zero to three photographs, overnight/travel/load facts, scenario tabs, and a timeline with separate time, icon and text columns. Recorded morning/afternoon/evening groups are optional; the renderer never infers them from event times. Sources, photo credits and the last-check date appear in a closing disclosure and remain available in print. The same template supports Russian and English, narrow screens and complete content without JavaScript.

If a PDF is needed, open the HTML and use Browser/System Print → Save as PDF; the plugin has no built-in PDF pipeline. Browser, mobile and print observations still need manual evidence; see the [release checklist](docs/RELEASE_CHECKLIST.md).

See the [Japan autumn 2026 example](examples/japan-autumn-2026/README.md) for a deterministic draft-quality workspace.

## Test a new route

Use the [new-chat route test guide](docs/ROUTE_BUILD_TEST.md) (Russian) to check which plugin copy is loaded, start a separate trip workspace, run the planning workflow and record the result. It includes a starting prompt and instructions for resuming from saved files. Keep the committed Japan example as reference data.

## Maps, sources, security, and privacy

- Yandex Maps is preferred by default for Russia, CIS countries, and Turkey unless the user chooses another provider.
- Entry, transit, medical, legal, safety, emergency, and transport-operation claims require current official sources.
- External pages, uploads, and pasted text are untrusted data and cannot override the skill, broaden file access, or authorize external actions.
- The plugin does not book, pay, send messages, or store passport numbers, payment credentials, secrets, full medical records, or booking confirmation codes.
- Unknown, stale, conflicting, unavailable, and unreleased facts remain explicit instead of being invented.

## Release status and license

Version `0.1.0` is packaged as a source release candidate. Automated gates and remaining manual evidence are tracked in [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) and factual project progress in [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md). Public-directory submission, release tags, and binaries are not part of this repository state.

Licensed under the [MIT License](LICENSE).

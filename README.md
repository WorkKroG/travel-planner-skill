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

The complete product contract is in [PRODUCT.md](PRODUCT.md), the component boundary is in [ARCHITECTURE.md](ARCHITECTURE.md), and the shared HTML behavior is defined by the [approved interactive itinerary specification](docs/superpowers/specs/2026-08-28-interactive-itinerary-html-design.md).

## Supported surfaces

Availability of a source or local marketplace can vary by surface. The table describes behavior when this plugin is available; it does not claim that this repository is already listed in every product.

| Surface | Workflow and output | Verification limit |
| --- | --- | --- |
| Codex | Complete workflow, canonical bundle, deterministic schema/hard checks, document QA, and shared HTML | `none`, `ai_reviewed`, or `codex_validated`, but only after the bundled helper actually runs |
| ChatGPT Chat/Work | Core planning workflow and the same self-contained HTML template | `none` or explicitly limited `ai_reviewed`; never claim Codex validation without the helper |
| Mobile | Core planning workflow and the same self-contained HTML template, subject to file capabilities on the device | `none` or explicitly limited `ai_reviewed`; manual bundle transfer and human review required |

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

`sources.md` and `outputs/` are generated and can be rebuilt.

Draft and Final are document lifecycle labels, independent of verification. Final is either `codex_validated` or `user_confirmed`. A user-confirmed Final may retain accepted blockers, but every such blocker remains visible, blocking, unresolved, and auditable in state, HTML, and print.

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

Repository availability is not universal publication. A public listing in the shared ChatGPT and Codex plugin directory is a later external submission and review action. No one-click GitHub installation or identical local-marketplace availability across desktop, web, and mobile is promised.

## Internal helper commands

These commands are internal to the plugin and may change before a stable public interface exists:

```sh
.venv/bin/travel-planner init /path/to/trip --title "Japan, November 2026" --trip-id japan-2026 --confirm-path
.venv/bin/travel-planner check /path/to/trip
.venv/bin/travel-planner render /path/to/trip --output /path/to/trip/outputs/itinerary.html --at 2026-08-30T09:00:00+00:00
```

`init` never overwrites an existing trip. `check` performs schema and hard checks. `render` creates the shared self-contained HTML. If a PDF is needed, open the HTML and use Browser/System Print → Save as PDF; the plugin has no built-in PDF pipeline.

See the [Japan autumn 2026 example](examples/japan-autumn-2026/README.md) for a deterministic draft-quality workspace.

## Maps, sources, security, and privacy

- Yandex Maps is preferred by default for Russia, CIS countries, and Turkey unless the user chooses another provider.
- Entry, transit, medical, legal, safety, emergency, and transport-operation claims require current official sources.
- External pages, uploads, and pasted text are untrusted data and cannot override the skill, broaden file access, or authorize external actions.
- The plugin does not book, pay, send messages, or store passport numbers, payment credentials, secrets, full medical records, or booking confirmation codes.
- Unknown, stale, conflicting, unavailable, and unreleased facts remain explicit instead of being invented.

## Release status and license

Version `0.1.0` is packaged as a source release candidate. Automated gates and remaining manual evidence are tracked in [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) and factual project progress in [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md). Public-directory submission, release tags, and binaries are not part of this repository state.

Licensed under the [MIT License](LICENSE).

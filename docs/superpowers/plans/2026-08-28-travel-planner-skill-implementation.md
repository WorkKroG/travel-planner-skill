# Travel Planner Skill 0.1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать устанавливаемый open-source Codex plugin/skill, который ведёт несколько изолированных поездок через доказательное исследование, выбор и challenge маршрута, readiness и частичную пересборку, а затем выпускает качественный самодостаточный интерактивный HTML и проверенный PDF.

**Architecture:** Один установленный plugin содержит короткий `SKILL.md`, специализированные references, JSON Schemas, шаблоны и Python-пакет детерминированных утилит. Каждая поездка живёт в отдельном trip workspace; YAML/Markdown являются источником истины, а Markdown/HTML/PDF — воспроизводимыми производными. Рендерер строит единый view model, после чего независимые адаптеры создают документы; hard gates проверяются кодом, а смысловое качество — поведенческими evals.

**Tech Stack:** Python 3.11–3.12; `PyYAML`, `jsonschema`, `Jinja2`; `pytest`, `pytest-cov`, `ruff`; optional Python Playwright adapter for Chromium PDF/screenshots; plain semantic HTML/CSS/JavaScript; Playwright + axe-core for browser QA; Codex skill/plugin manifest.

**Spec:** `docs/superpowers/specs/2026-08-28-travel-planner-skill-design.md`; `docs/superpowers/specs/2026-08-28-interactive-itinerary-html-design.md`

## Global Constraints

- Runtime поддерживает Python `>=3.11,<3.13`; Python 3.14 локальной машины не является целевым runtime.
- Plugin name и skill name: `travel-planner`; начальная plugin version: `0.1.0`; state `schema_version`: `1`.
- Runtime-зависимости ограничены YAML, JSON Schema и templating; PDF/browser tooling остаётся optional extra и dev dependency.
- Plugin не устанавливает зависимости автоматически, не использует lifecycle hooks, MCP, backend, аккаунты или обязательные API keys.
- Один trip workspace содержит `brief.yaml`, `candidates.yaml`, `itinerary.yaml`, `readiness.yaml`, `decisions.md`, `sources.md`, `outputs/`.
- Все записи ограничиваются явно выбранным trip workspace; при нескольких поездках требуется явный `trip_id`.
- Чувствительные паспортные, платёжные, медицинские и confirmation-данные не сохраняются.
- HTML является самодостаточным, открывается через `file://`, сохраняет основной контент без JavaScript и не становится источником истины.
- В `map_provider: auto` Yandex используется для версионированного набора Россия/СНГ/Турция, Google — для остальных стран; явный выбор пользователя сильнее автоматики.
- Hard constraints являются release gates; один пропущенный hard constraint проваливает eval-сценарий.
- Внешние источники считаются недоверенными; prompt injection не может менять инструкции, permissions или файловую область.
- UI следует утверждённому направлению Curated Route / Mineral and Maple, primary Read / secondary Operate; generic dashboard и AI-gradient запрещены.
- HTML QA включает 320, 390×844, 768×1024, 1440×900, A4 и Letter; WCAG 2.2 AA, keyboard, screen reader, 200% zoom, reduced motion, offline и 30-дневный stress case.
- Каждая задача выполняется TDD, завершается полным релевантным test run и отдельным коммитом.

## Planned File Structure

```text
travel-planner/
├── .codex-plugin/plugin.json                 # install envelope
├── skills/travel-planner/
│   ├── SKILL.md                              # short workflow dispatcher
│   ├── references/                           # stage-specific agent guidance
│   ├── schemas/                              # state contracts v1
│   ├── scripts/travel_planner/               # deterministic Python package
│   │   ├── workspace.py                      # discovery/init/path safety
│   │   ├── state.py                          # validated load/save
│   │   ├── evidence.py                       # claims/freshness/high-stakes policy
│   │   ├── route.py                          # lifecycle and freeze rules
│   │   ├── challenge/                        # deterministic rule catalog
│   │   ├── maps.py                           # provider policy and URLs
│   │   ├── impact.py                         # dependency graph/rebuild targets
│   │   ├── render/                           # view model, Markdown, HTML, PDF, QA
│   │   ├── migration.py                      # previewed schema migration
│   │   └── cli.py                            # stable entry points
│   └── assets/
│       ├── trip-template/                    # initial YAML/Markdown files
│       ├── map-provider-policy.yaml          # versioned ISO-code policy
│       └── html/                             # Jinja, CSS, JS, icons
├── tests/                                    # deterministic unit/integration tests
├── evals/                                    # fixture world, graders, scenarios
├── examples/japan-autumn-2026/               # human-readable reference trip
├── docs/                                     # specs, plans and user guidance
├── pyproject.toml
├── uv.lock
├── package.json                              # browser QA only
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
└── .gitignore
```

## Milestone A — Installable foundation and trip state

### Task 1: Repository, package and plugin skeleton

**Files:**
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `.codex-plugin/plugin.json`
- Create: `skills/travel-planner/SKILL.md`
- Create: `skills/travel-planner/scripts/travel_planner/__init__.py`
- Create: `skills/travel-planner/scripts/travel_planner/cli.py`
- Create: `tests/test_package_layout.py`

**Interfaces:**
- Produces: console command `travel-planner`; package constant `__version__ = "0.1.0"`; manifest skill root `./skills/`.
- Consumes: no earlier task.

- [x] **Step 1: Initialize Git and write the failing layout test**

```python
from pathlib import Path
import json

ROOT = Path(__file__).parents[1]

def test_plugin_layout_and_version_agree():
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    assert manifest["name"] == "travel-planner"
    assert manifest["version"] == "0.1.0"
    assert manifest["skills"] == "./skills/"
    assert (ROOT / "skills/travel-planner/SKILL.md").exists()
```

- [x] **Step 2: Run the test and confirm the empty repository fails**

Run: `python3 -m pytest tests/test_package_layout.py -v`  
Expected: FAIL because manifest/package files do not exist.

- [x] **Step 3: Add the minimal package, manifest, CLI and dependency configuration**

Before fixing the manifest contract, verify the current Codex plugin and skill packaging fields against the official OpenAI documentation; record any spec-driven adjustment in the task commit rather than guessing an unstable field.

```python
# skills/travel-planner/scripts/travel_planner/cli.py
from . import __version__

def main() -> int:
    print(f"travel-planner {__version__}")
    return 0
```

Declare `PyYAML`, `jsonschema`, `Jinja2` as runtime dependencies; `pytest`, `pytest-cov`, `ruff`, `playwright` as extras; configure package discovery from `skills/travel-planner/scripts`; generate and commit `uv.lock` with Python 3.11 resolution.

- [x] **Step 4: Verify package, CLI and manifest**

Run: `uv sync --all-extras --locked`  
Run: `uv run pytest tests/test_package_layout.py -v`  
Run: `uv run travel-planner`  
Expected: PASS and `travel-planner 0.1.0`.

- [x] **Step 5: Commit**

```bash
git add .gitignore LICENSE pyproject.toml uv.lock .codex-plugin skills tests/test_package_layout.py
git commit -m "chore: bootstrap travel planner plugin"
```

### Task 2: Trip workspace onboarding and safe initialization

**Files:**
- Create: `skills/travel-planner/scripts/travel_planner/workspace.py`
- Create: `skills/travel-planner/assets/trip-template/brief.yaml`
- Create: `skills/travel-planner/assets/trip-template/candidates.yaml`
- Create: `skills/travel-planner/assets/trip-template/itinerary.yaml`
- Create: `skills/travel-planner/assets/trip-template/readiness.yaml`
- Create: `skills/travel-planner/assets/trip-template/decisions.md`
- Create: `skills/travel-planner/assets/trip-template/sources.md`
- Create: `tests/workspace/test_workspace.py`
- Modify: `skills/travel-planner/scripts/travel_planner/cli.py`

**Interfaces:**
- Produces: `TripPaths`, `discover_trip_roots(start: Path) -> list[Path]`, `initialize_trip(root: Path, title: str, trip_id: str | None = None) -> TripPaths`.
- Consumes: package/version from Task 1.

- [x] **Step 1: Write tests for empty, existing and ambiguous folders**

```python
def test_initialize_trip_never_overwrites_an_existing_trip(tmp_path):
    initialize_trip(tmp_path, "Japan 2026", "japan-2026")
    with pytest.raises(WorkspaceExistsError):
        initialize_trip(tmp_path, "Iceland 2027", "iceland-2027")

def test_discovery_requires_explicit_choice_for_two_trips(tmp_path):
    initialize_trip(tmp_path / "a", "A", "trip-a")
    initialize_trip(tmp_path / "b", "B", "trip-b")
    assert [p.name for p in discover_trip_roots(tmp_path)] == ["a", "b"]
```

- [x] **Step 2: Verify failure before implementation**

Run: `uv run pytest tests/workspace/test_workspace.py -v`  
Expected: FAIL because workspace interfaces do not exist.

- [x] **Step 3: Implement atomic initialization and the project reminder contract**

```python
@dataclass(frozen=True)
class TripPaths:
    root: Path
    brief: Path
    candidates: Path
    itinerary: Path
    readiness: Path
    decisions: Path
    sources: Path
    outputs: Path

PROJECT_REMINDER = (
    "Для новой поездки рекомендуется отдельная папка и локальный Codex project. "
    "Подтвердите выбранный путь перед созданием файлов."
)
```

Write all files into a sibling temporary directory, validate that the target is not the skill source or another trip, then rename atomically. Add `travel-planner init PATH --title TITLE --trip-id ID --confirm-path` and refuse initialization without `--confirm-path`.

- [x] **Step 4: Verify isolation and CLI behaviour**

Run: `uv run pytest tests/workspace/test_workspace.py -v`  
Run: `uv run travel-planner init /tmp/example-trip --title "Example" --trip-id example --confirm-path`  
Expected: tests PASS; CLI creates exactly one workspace and prints its `trip_id`.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/assets/trip-template skills/travel-planner/scripts/travel_planner tests/workspace
git commit -m "feat: add safe trip workspace initialization"
```

### Task 3: Versioned schemas and validated state I/O

**Files:**
- Create: `skills/travel-planner/schemas/brief.schema.json`
- Create: `skills/travel-planner/schemas/candidates.schema.json`
- Create: `skills/travel-planner/schemas/itinerary.schema.json`
- Create: `skills/travel-planner/schemas/readiness.schema.json`
- Create: `skills/travel-planner/scripts/travel_planner/state.py`
- Create: `tests/state/test_schema_validation.py`
- Create: `tests/fixtures/minimal-trip/`
- Modify: `skills/travel-planner/scripts/travel_planner/cli.py`

**Interfaces:**
- Produces: `TripState`, `ValidationIssue`, `ValidationReport`, `load_trip(root: Path) -> TripState`, `validate_trip(root: Path) -> ValidationReport`, `write_state_file(path: Path, value: Mapping[str, Any]) -> None`.
- Consumes: `TripPaths` from Task 2.

- [x] **Step 1: Write schema and round-trip failure tests**

```python
def test_unknown_readiness_status_reports_exact_path(minimal_trip):
    data = yaml.safe_load((minimal_trip / "readiness.yaml").read_text())
    data["items"] = [{"id": "r1", "status": "done-ish", "category": "entry"}]
    write_state_file(minimal_trip / "readiness.yaml", data)
    report = validate_trip(minimal_trip)
    assert report.ok is False
    assert report.issues[0].path == "readiness.yaml.items[0].status"

def test_candidate_keeps_fact_popularity_assessment_and_verdict_separate(minimal_trip):
    candidate = load_trip(minimal_trip).candidates["items"][0]
    assert {"claims", "popularity_signals", "assessments", "verdict"} <= candidate.keys()
    assert candidate["verdict"] not in candidate["claims"]
```

- [x] **Step 2: Run the test and confirm missing schemas fail**

Run: `uv run pytest tests/state/test_schema_validation.py -v`  
Expected: FAIL because `validate_trip` and schemas are absent.

- [x] **Step 3: Implement schema v1, stable ordering and atomic writes**

```python
@dataclass(frozen=True)
class ValidationIssue:
    file: str
    path: str
    message: str

@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]
    @property
    def ok(self) -> bool:
        return not self.issues
```

Schemas must encode route states, claim/freshness statuses, traveler IDs, budget amount types, readiness statuses and referential ID patterns. Preserve semantic mapping order and write via temporary sibling + `replace`.

- [x] **Step 4: Verify validation and CLI diagnostics**

Run: `uv run pytest tests/state -v`  
Run: `uv run travel-planner validate tests/fixtures/minimal-trip`  
Expected: PASS and CLI exits `0`; corrupt fixture exits `2` with file and field.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/schemas skills/travel-planner/scripts/travel_planner/state.py skills/travel-planner/scripts/travel_planner/cli.py tests/state tests/fixtures/minimal-trip
git commit -m "feat: add versioned trip state validation"
```

### Task 4: Evidence, freshness and readiness policy

**Files:**
- Create: `skills/travel-planner/scripts/travel_planner/evidence.py`
- Create: `skills/travel-planner/scripts/travel_planner/readiness.py`
- Create: `tests/evidence/test_evidence.py`
- Create: `tests/evidence/test_readiness.py`

**Interfaces:**
- Produces: `assess_claim(claim, sources, now) -> ClaimAssessment`, `critical_evidence_findings(state, now) -> tuple[Finding, ...]`, `next_recheck(item, trip_start) -> datetime | None`, `render_sources_markdown(state) -> str`.
- Consumes: `TripState` and schema enums from Task 3; `Finding` protocol is introduced here and reused by challenge tasks.

- [x] **Step 1: Write high-stakes and uncertainty tests**

```python
def test_visa_claim_without_official_source_creates_blocker(state):
    state.candidates["claims"] = [{
        "id": "claim-visa", "topic": "entry", "status": "reported",
        "source_ids": ["blog-1"], "applies_to": ["traveler-1"]
    }]
    findings = critical_evidence_findings(state, NOW)
    assert findings[0].rule_id == "EVID-001"
    assert findings[0].severity == "blocking"

def test_future_schedule_is_not_invented():
    assessment = assess_claim({"status": "not_released_yet"}, {}, NOW)
    assert assessment.value is None
    assert assessment.next_check_at is not None

def test_sources_projection_includes_readiness_claims(state):
    state.candidates["claims"] = [{
        "id": "claim-visa", "status": "reported", "source_ids": ["official-1"]
    }]
    state.readiness["items"] = [{
        "id": "ready-entry", "category": "entry", "status": "recheck",
        "source_ids": ["official-1"], "claim_ids": ["claim-visa"]
    }]
    markdown = render_sources_markdown(state)
    assert "claim-visa" in markdown
    assert "last checked" in markdown.lower()
```

- [x] **Step 2: Verify tests fail**

Run: `uv run pytest tests/evidence -v`  
Expected: FAIL because policy functions are absent.

- [x] **Step 3: Implement typed findings and official-source gates**

```python
@dataclass(frozen=True)
class ClaimAssessment:
    status: str
    value: Any | None
    confidence: Literal["high", "medium", "low"]
    next_check_at: datetime | None

@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Literal["blocking", "warning", "note"]
    confidence: Literal["high", "medium", "low"]
    affected_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    message: str
    proposed_patch: Mapping[str, Any] | None = None
```

Require official primary sources for entry/transit, medication legality, health, advisories, emergency and transport operations; never store long quotes or secrets. Create or update readiness items without overwriting owner decisions. Regenerate `sources.md` from candidates, itinerary and readiness references with stable IDs, conflicts and recheck dates.

- [x] **Step 4: Verify deterministic policy output**

Run: `uv run pytest tests/evidence -v`  
Expected: PASS, including clock-controlled stale/recheck cases.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/scripts/travel_planner/evidence.py skills/travel-planner/scripts/travel_planner/readiness.py tests/evidence
git commit -m "feat: add evidence and readiness policy"
```

### Task 5: Route lifecycle, alternatives and decision journal

**Files:**
- Create: `skills/travel-planner/scripts/travel_planner/route.py`
- Create: `skills/travel-planner/scripts/travel_planner/decisions.py`
- Create: `tests/route/test_lifecycle.py`
- Create: `tests/route/test_decisions.py`

**Interfaces:**
- Produces: `RouteChange`, `DecisionRecord`, `SkeletonComparison`, `FrozenRouteError`, `transition_route(state, target, decision) -> TripState`, `compare_skeletons(skeletons) -> SkeletonComparison`, `append_decision(path, DecisionRecord) -> None`.
- Consumes: `TripState`, `Finding`; emits immutable IDs referenced by impact analysis and renderers.

- [x] **Step 1: Write transition and silent-mutation tests**

```python
def test_frozen_route_requires_impact_and_consent(frozen_state):
    request = RouteChange(kind="hotel", affected_ids=("night-4",), consent=False)
    with pytest.raises(FrozenRouteError):
        transition_route(frozen_state, "frozen", request)

def test_skeletons_must_differ_structurally():
    comparison = compare_skeletons([same_geo_a, same_geo_b])
    assert comparison.distinct is False
```

- [x] **Step 2: Verify tests fail**

Run: `uv run pytest tests/route -v`  
Expected: FAIL because lifecycle interfaces are absent.

- [x] **Step 3: Implement the state machine and append-only journal formatting**

```python
ALLOWED = {
    "draft": {"challenged"},
    "challenged": {"selected", "draft"},
    "selected": {"frozen", "challenged"},
    "frozen": {"challenged"},
}
```

Structural comparison must inspect geography, bases, pace and experience mix. `decisions.md` records date, selected option, rejected alternatives, reason and affected IDs; YAML remains current state.

- [x] **Step 4: Verify lifecycle invariants**

Run: `uv run pytest tests/route -v`  
Expected: PASS; frozen changes without consent remain rejected.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/scripts/travel_planner/route.py skills/travel-planner/scripts/travel_planner/decisions.py tests/route
git commit -m "feat: add controlled route lifecycle"
```

## Milestone B — Deterministic challenge and controlled updates

### Task 6: Challenge framework and stable rule catalog

**Files:**
- Create: `skills/travel-planner/scripts/travel_planner/challenge/__init__.py`
- Create: `skills/travel-planner/scripts/travel_planner/challenge/base.py`
- Create: `skills/travel-planner/scripts/travel_planner/challenge/catalog.py`
- Create: `tests/challenge/test_framework.py`
- Modify: `skills/travel-planner/scripts/travel_planner/cli.py`

**Interfaces:**
- Produces: `ChallengeStage = Literal["skeleton", "detailed"]`, `ChallengeContext`, `ChallengeReport`, `Rule`, `run_challenge(state, stage, now) -> ChallengeReport`.
- Consumes: `TripState` and `Finding`; later tasks register `CAL`, `OPS`, `LEG`, `LOAD`, `ACC`, `BOOK`, `BUD`, `RISK`, `EVID`, `STATE` rules.

- [x] **Step 1: Write framework ordering and macro-gate tests**

```python
def test_report_is_stable_and_blocking_fails_macro_gate(state):
    rules = [FakeRule("LEG-002", "warning"), FakeRule("CAL-001", "blocking")]
    report = run_challenge(state, "skeleton", NOW, rules=rules)
    assert [f.rule_id for f in report.findings] == ["CAL-001", "LEG-002"]
    assert report.hard_pass is False
```

- [x] **Step 2: Verify failure**

Run: `uv run pytest tests/challenge/test_framework.py -v`  
Expected: FAIL because challenge framework is absent.

- [x] **Step 3: Implement registry, versioned rules and report serialization**

```python
class Rule(Protocol):
    rule_id: str
    version: int
    stages: frozenset[ChallengeStage]
    def evaluate(self, ctx: ChallengeContext) -> Iterable[Finding]: ...
```

Findings sort by severity, rule ID and affected entity. Add CLI `challenge PATH --stage skeleton|detailed --at ISO_DATETIME`; exit `3` when `hard_pass` is false.

- [x] **Step 4: Verify framework and CLI exit codes**

Run: `uv run pytest tests/challenge/test_framework.py -v`  
Expected: PASS and stable serialized output.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/scripts/travel_planner/challenge skills/travel-planner/scripts/travel_planner/cli.py tests/challenge/test_framework.py
git commit -m "feat: add versioned challenge framework"
```

### Task 7: Calendar, timezone and door-to-door logistics rules

**Files:**
- Create: `skills/travel-planner/scripts/travel_planner/challenge/calendar.py`
- Create: `skills/travel-planner/scripts/travel_planner/challenge/logistics.py`
- Create: `tests/challenge/test_calendar.py`
- Create: `tests/challenge/test_logistics.py`
- Create: `tests/fixtures/logistics-world.yaml`
- Modify: `skills/travel-planner/scripts/travel_planner/challenge/catalog.py`

**Interfaces:**
- Produces: rules `CAL-001..004`, `OPS-001..004`, `LEG-001..006` operating on timezone-aware ISO timestamps.
- Consumes: `ChallengeContext`; fixture world supplies deterministic hours, last admission, minimum connection, storage and schedule horizon.

- [x] **Step 1: Write DST, overnight and last-admission tests**

```python
def test_last_admission_is_not_closing_time(ctx):
    ctx.arrival = "2026-11-06T16:45:00+09:00"
    ctx.venue = {"closes_at": "18:00", "last_admission": "16:30"}
    finding = LastAdmissionRule().evaluate(ctx)[0]
    assert finding.rule_id == "OPS-002"
    assert finding.severity == "blocking"

def test_overnight_leg_updates_local_date(ctx):
    report = OvernightRolloverRule().evaluate(ctx)
    assert report[0].affected_ids == ("day-5", "night-5")
```

- [x] **Step 2: Verify failures**

Run: `uv run pytest tests/challenge/test_calendar.py tests/challenge/test_logistics.py -v`  
Expected: FAIL because rules are absent.

- [x] **Step 3: Implement rules using `zoneinfo` and explicit fixture facts**

```python
def local_dt(value: str, timezone: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
    return parsed.astimezone(ZoneInfo(timezone))
```

Check weekday, holiday/operating date, DST, rollover, last service/admission, door-to-door components, border/security/check-in buffers, hotel check-in/out, luggage storage and `not_released_yet` without inventing times.

- [x] **Step 4: Verify logistics suite**

Run: `uv run pytest tests/challenge/test_calendar.py tests/challenge/test_logistics.py -v`  
Expected: PASS for all deterministic edge cases.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/scripts/travel_planner/challenge tests/challenge tests/fixtures/logistics-world.yaml
git commit -m "feat: validate timezone aware trip logistics"
```

### Task 8: Budget, booking, accessibility and load rules

**Files:**
- Create: `skills/travel-planner/scripts/travel_planner/challenge/budget.py`
- Create: `skills/travel-planner/scripts/travel_planner/challenge/readiness.py`
- Create: `skills/travel-planner/scripts/travel_planner/challenge/load.py`
- Create: `tests/challenge/test_budget.py`
- Create: `tests/challenge/test_readiness.py`
- Create: `tests/challenge/test_load.py`
- Modify: `skills/travel-planner/scripts/travel_planner/challenge/catalog.py`

**Interfaces:**
- Produces: normalized `MoneyAmount`, rules `BUD-*`, `BOOK-*`, `ACC-*`, `LOAD-*`.
- Consumes: state budget/readiness/travelers and `ChallengeContext`.

- [x] **Step 1: Write basis-mismatch, booking-window and accessibility tests**

```python
def test_per_person_and_group_prices_are_not_summed_without_normalization(ctx):
    findings = BudgetBasisRule().evaluate(ctx)
    assert findings[0].rule_id == "BUD-002"
    assert findings[0].severity == "blocking"

def test_unknown_wheelchair_transfer_creates_readiness_action(ctx):
    findings = AccessibilityChainRule().evaluate(ctx)
    assert findings[0].rule_id == "ACC-001"
    assert findings[0].proposed_patch["status"] == "action_needed"
```

- [x] **Step 2: Verify failures**

Run: `uv run pytest tests/challenge/test_budget.py tests/challenge/test_readiness.py tests/challenge/test_load.py -v`  
Expected: FAIL because rules are absent.

- [x] **Step 3: Implement explicit amount quality and readiness dependencies**

```python
@dataclass(frozen=True)
class MoneyAmount:
    amount: Decimal
    currency: str
    amount_type: Literal["estimate", "observed_price", "quote", "booked", "paid"]
    basis: Literal["person", "group"]
    taxes_included: bool | None
```

Check FX source/date/rate, mandatory category coverage, contingency, release/due timezone, dependency cycles, capacity, cancellation summary, cumulative activity load and minimum v0.1 accessibility unknowns.

- [x] **Step 4: Verify all registered rules**

Run: `uv run pytest tests/challenge -v`  
Expected: PASS; rule IDs remain unique and versioned.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/scripts/travel_planner/challenge tests/challenge
git commit -m "feat: add budget readiness and load gates"
```

### Task 9: Yandex/Google map provider policy and safe URLs

**Files:**
- Create: `skills/travel-planner/assets/map-provider-policy.yaml`
- Create: `skills/travel-planner/scripts/travel_planner/maps.py`
- Create: `tests/maps/test_policy.py`
- Create: `tests/maps/test_urls.py`
- Modify: `skills/travel-planner/scripts/travel_planner/cli.py`

**Interfaces:**
- Produces: `MapProvider`, `select_provider(country_code, preference, policy) -> MapProvider`, `build_place_url(provider, place) -> str`, `build_route_urls(leg, preference, policy) -> tuple[MapLink, ...]`.
- Consumes: country codes and `brief.map_provider` from state.

- [x] **Step 1: Write provider, override and cross-border tests**

```python
@pytest.mark.parametrize(("country", "expected"), [
    ("RU", "yandex"), ("KZ", "yandex"), ("TR", "yandex"),
    ("JP", "google"), ("FR", "google"),
])
def test_auto_provider(country, expected, policy):
    assert select_provider(country, "auto", policy).value == expected

def test_explicit_google_override_wins_in_russia(policy):
    assert select_provider("RU", "google", policy).value == "google"

def test_cross_border_leg_can_return_labelled_alternative(policy):
    links = build_route_urls(LEG_KZ_TR, "auto", policy)
    assert {link.provider.value for link in links} == {"yandex", "google"}
```

- [x] **Step 2: Verify failures**

Run: `uv run pytest tests/maps -v`  
Expected: FAIL because policy and builders are absent.

- [x] **Step 3: Implement versioned ISO-code policy and encoded URLs**

```yaml
policy_version: 1
yandex_preferred_country_codes:
  [AM, AZ, BY, KZ, KG, MD, RU, TJ, TM, TR, UZ]
default_provider: google
```

The list is a product routing policy, not a geopolitical assertion; future changes require a policy-version change, changelog entry and test update.

```python
class MapProvider(str, Enum):
    AUTO = "auto"
    YANDEX = "yandex"
    GOOGLE = "google"

@dataclass(frozen=True)
class MapLink:
    provider: MapProvider
    label: str
    url: str
    requires_internet: bool = True
```

Reject non-HTTPS schemes, encode user text with `urllib.parse`, prefer coordinates plus readable label, and expose fallback diagnostics instead of silently changing provider.

- [x] **Step 4: Verify URL safety and CLI output**

Run: `uv run pytest tests/maps -v`  
Run: `uv run travel-planner map-link --country RU --query "Казанский кремль"`  
Expected: PASS and a labelled Yandex URL.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/assets/map-provider-policy.yaml skills/travel-planner/scripts/travel_planner/maps.py skills/travel-planner/scripts/travel_planner/cli.py tests/maps
git commit -m "feat: select maps by destination policy"
```

### Task 10: Impact graph, partial rebuild and schema migrations

**Files:**
- Create: `skills/travel-planner/scripts/travel_planner/impact.py`
- Create: `skills/travel-planner/scripts/travel_planner/migration.py`
- Create: `tests/impact/test_impact.py`
- Create: `tests/impact/test_partial_rebuild.py`
- Create: `tests/migration/test_migration.py`
- Modify: `skills/travel-planner/scripts/travel_planner/cli.py`

**Interfaces:**
- Produces: `ImpactTarget`, `semantic_hash(value) -> str`, `analyze_change(before, after) -> ImpactReport`, `select_rebuild_targets(report) -> tuple[ImpactTarget, ...]`, `preview_migration(root, target_version) -> MigrationPlan`, `apply_migration(plan, confirmed) -> None`.
- Consumes: validated `TripState`; later renderers consume rebuild targets.

- [x] **Step 1: Write semantic preservation and preview tests**

```python
def test_restaurant_change_does_not_touch_unrelated_days(before, after):
    report = analyze_change(before, after)
    assert report.targets == (ImpactTarget("day", "day-4"), ImpactTarget("outputs", "all"))
    assert "day-5" not in report.changed_ids

def test_migration_requires_preview_and_confirmation(trip_v1):
    plan = preview_migration(trip_v1, 2)
    with pytest.raises(ConfirmationRequired):
        apply_migration(plan, confirmed=False)
```

- [x] **Step 2: Verify failures**

Run: `uv run pytest tests/impact tests/migration -v`  
Expected: FAIL because graph/migration interfaces are absent.

- [x] **Step 3: Implement stable semantic hashes, dependency edges and recoverable backup**

```python
@dataclass(frozen=True, order=True)
class ImpactTarget:
    kind: Literal["candidate", "day", "leg", "readiness", "route", "outputs"]
    entity_id: str
```

Ignore declared temporal metadata when hashing. Migration apply creates a timestamped sibling backup, validates migrated state, and restores on failure.

- [x] **Step 4: Run mutation and idempotence tests**

Run: `uv run pytest tests/impact tests/migration -v`  
Expected: PASS; second rebuild has an empty semantic diff.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/scripts/travel_planner/impact.py skills/travel-planner/scripts/travel_planner/migration.py skills/travel-planner/scripts/travel_planner/cli.py tests/impact tests/migration
git commit -m "feat: add safe partial rebuild planning"
```

## Milestone C — Curated Route documents and browser quality

### Task 11: Canonical render view model and Markdown output

**Files:**
- Create: `skills/travel-planner/scripts/travel_planner/render/__init__.py`
- Create: `skills/travel-planner/scripts/travel_planner/render/viewmodel.py`
- Create: `skills/travel-planner/scripts/travel_planner/render/markdown.py`
- Create: `tests/render/test_viewmodel.py`
- Create: `tests/render/test_markdown.py`
- Create: `tests/fixtures/japan-reference/`
- Modify: `skills/travel-planner/scripts/travel_planner/cli.py`

**Interfaces:**
- Produces: `ItineraryView`, `SummaryView`, `RouteStopView`, `DecisionView`, `DayView`, `ReadinessView`, `BudgetView`, `SourceView`, `build_view(state, challenge, generated_at) -> ItineraryView`, `render_markdown(view) -> str`.
- Consumes: validated state, findings, map links and readiness; HTML/PDF adapters consume only `ItineraryView`.

- [x] **Step 1: Write first-screen ordering and state-boundary tests**

```python
def test_view_places_blockers_before_day_details(japan_state):
    view = build_view(japan_state, japan_report, GENERATED_AT)
    assert view.summary.blockers[0].severity == "blocking"
    assert view.days[0].day_id == "day-1"

def test_view_does_not_mutate_canonical_state(japan_state):
    before = semantic_hash(japan_state)
    build_view(japan_state, japan_report, GENERATED_AT)
    assert semantic_hash(japan_state) == before
```

- [x] **Step 2: Verify failure**

Run: `uv run pytest tests/render/test_viewmodel.py tests/render/test_markdown.py -v`  
Expected: FAIL because view/render modules are absent.

- [x] **Step 3: Implement immutable view dataclasses and deterministic Markdown**

```python
@dataclass(frozen=True)
class ItineraryView:
    trip_id: str
    title: str
    status: Literal["draft", "final"]
    summary: SummaryView
    route: tuple[RouteStopView, ...]
    open_decisions: tuple[DecisionView, ...]
    days: tuple[DayView, ...]
    readiness: tuple[ReadinessView, ...]
    budget: BudgetView
    sources: tuple[SourceView, ...]
    generated_at: datetime
```

Order summary → route/day overview → decisions → days → readiness → budget → risks → sources. Print Draft/Final, stale/conflicting/unknown and last-checked text explicitly.

- [x] **Step 4: Verify deterministic snapshots**

Run: `uv run pytest tests/render/test_viewmodel.py tests/render/test_markdown.py -v`  
Expected: PASS; identical inputs and fixed clock produce byte-identical Markdown.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/scripts/travel_planner/render skills/travel-planner/scripts/travel_planner/cli.py tests/render tests/fixtures/japan-reference
git commit -m "feat: add canonical itinerary render model"
```

### Task 12: Self-contained Curated Route HTML renderer

**Files:**
- Create: `skills/travel-planner/assets/html/itinerary.html.j2`
- Create: `skills/travel-planner/assets/html/styles.css`
- Create: `skills/travel-planner/assets/html/app.js`
- Create: `skills/travel-planner/assets/html/icons.svg`
- Create: `skills/travel-planner/scripts/travel_planner/render/html.py`
- Create: `tests/render/test_html_structure.py`
- Create: `tests/render/test_html_no_js.py`
- Create: `tests/render/snapshots/japan.html.sha256`
- Modify: `skills/travel-planner/scripts/travel_planner/cli.py`

**Interfaces:**
- Produces: `HtmlOptions`, `MediaAsset`, `render_html(view, media, options) -> str`, `write_html(view, target, options) -> Path`.
- Consumes: `ItineraryView`; embeds CSS/JS/icons/media and emits no required network requests.

- [x] **Step 1: Write semantic structure and progressive-enhancement tests**

```python
def test_html_contains_required_reading_order(japan_view):
    html = render_html(japan_view, media={}, options=DEFAULTS)
    assert html.index('id="trip-summary"') < html.index('id="route-overview"')
    assert html.index('id="open-decisions"') < html.index('id="day-1"')
    assert 'src="http' not in html and 'href="http' in html

def test_primary_and_backup_exist_without_javascript(japan_view):
    html = render_html(japan_view, media={}, options=DEFAULTS)
    assert 'data-scenario="primary"' in html
    assert 'data-scenario="backup"' in html
```

- [x] **Step 2: Verify failure**

Run: `uv run pytest tests/render/test_html_structure.py tests/render/test_html_no_js.py -v`  
Expected: FAIL because HTML renderer/assets are absent.

- [x] **Step 3: Implement the approved visual and interaction contract**

```python
@dataclass(frozen=True)
class HtmlOptions:
    include_optional_media: bool = True
    print_images: bool = True

@dataclass(frozen=True)
class MediaAsset:
    content: bytes
    mime_type: str
    alt: str
    source_id: str
    license: str

def render_html(view: ItineraryView, media: Mapping[str, MediaAsset], options: HtmlOptions) -> str:
    env = Environment(loader=FileSystemLoader(ASSET_DIR), autoescape=True)
    return env.get_template("itinerary.html.j2").render(
        view=view,
        css=(ASSET_DIR / "styles.css").read_text(),
        js=(ASSET_DIR / "app.js").read_text(),
        icons=(ASSET_DIR / "icons.svg").read_text(),
        media=embed_media(media),
    )
```

Use exact design tokens `#EDF1EC`, `#FFFDF7`, `#173C44`, `#BD4A36`, `#D1A044`, `#496B58`; 8 px spacing rhythm; 0/8/12/full radii by the approved shape grammar; Source Serif 4/Inter with embedded or system fallbacks and no runtime font request.

Implement semantic landmarks, skip link, text route ribbon, day overview, sticky/flow contents, 44 px controls, a 52 px phone Contents control above the safe area, search, filters, disclosures, view-only scenario switch, map provider labels, status text+icons, optional stamp/photo collapse, `prefers-reduced-motion`, 320/640/1024 breakpoints and print CSS. Do not use `localStorage` in v0.1. `embed_media` rejects optional photographs without source/license provenance and collapses missing media. No pseudo-map, gallery, dark mode or canonical edits.

- [x] **Step 4: Verify structure, determinism and offline assets**

Run: `uv run pytest tests/render/test_html_structure.py tests/render/test_html_no_js.py -v`  
Run: `uv run travel-planner render tests/fixtures/japan-reference --format html --output /tmp/japan.html --at 2026-08-28T12:00:00Z`  
Expected: PASS; `/tmp/japan.html` opens through `file://` with all styles/scripts inline.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/assets/html skills/travel-planner/scripts/travel_planner/render/html.py skills/travel-planner/scripts/travel_planner/cli.py tests/render
git commit -m "feat: render interactive curated route html"
```

### Task 13: Browser QA, accessibility, performance and PDF adapter

**Files:**
- Create: `package.json`
- Create: `package-lock.json`
- Create: `tests/ui/qa.mjs`
- Create: `tests/ui/axe.config.mjs`
- Create: `tests/ui/visual-baselines/`
- Create: `skills/travel-planner/scripts/travel_planner/render/pdf.py`
- Create: `skills/travel-planner/scripts/travel_planner/render/qa.py`
- Create: `tests/render/test_pdf_adapter.py`
- Create: `tests/render/test_qa_report.py`
- Modify: `skills/travel-planner/scripts/travel_planner/cli.py`

**Interfaces:**
- Produces: `PdfAdapter`, `PdfResult`, `QaReport`, `render_pdf(html_path, pdf_path) -> PdfResult`, `run_document_qa(html_path, profiles) -> QaReport`; Node command `npm run qa:ui -- PATH`.
- Consumes: self-contained HTML from Task 12; Playwright is optional for end users but required in release environment.

- [x] **Step 1: Write missing-adapter and QA hard-gate tests**

```python
def test_missing_pdf_adapter_returns_html_success_but_not_pdf_success(tmp_path, monkeypatch):
    monkeypatch.setattr(PdfAdapter, "available", lambda self: False)
    result = render_pdf(tmp_path / "trip.html", tmp_path / "trip.pdf")
    assert result.created is False
    assert result.code == "PDF_ADAPTER_MISSING"

def test_serious_accessibility_finding_blocks_final_status():
    report = QaReport(accessibility_serious=1)
    assert report.final_allowed is False
```

- [x] **Step 2: Verify failure**

Run: `uv run pytest tests/render/test_pdf_adapter.py tests/render/test_qa_report.py -v`  
Expected: FAIL because adapters and report do not exist.

- [x] **Step 3: Implement bounded browser QA and print adapter**

```javascript
const sizes = [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 900 },
  { name: "narrow", width: 320, height: 800 }
];
```

Use Playwright and `@axe-core/playwright` to capture summary/day/conflict/stale/Draft/Final, test keyboard-visible focus, zero critical/serious axe results, no horizontal scroll, 200% zoom, reduced motion, disabled-network and disabled-JS reading, A4/Letter PDF, performance timings, file size and 30-day memory. Enforce first useful screen `<2.5 s`, cumulative layout shift `<0.1` and local interaction response `<200 ms` on the representative mobile profile. Run one batched desktop+mobile inspection, one batched fix pass, and at most one confirmation pass.

Generate and commit the lockfile with `npm install --package-lock-only` before the first clean `npm ci`, so release QA installs exactly the reviewed dependency graph.

- [ ] **Step 4: Run browser, PDF and print checks**

Automated browser, accessibility, responsive, offline/no-JS, state-matrix, A4/Letter PDF,
performance, touch-target and 30-day stress checks pass. The manual VoiceOver walkthrough remains
an explicit release checkpoint because local UI control was unavailable in this session.

Run: `npm ci`  
Run: `npx playwright install chromium`  
Run: `npm run qa:ui -- /tmp/japan.html`  
Run: `uv run pytest tests/render/test_pdf_adapter.py tests/render/test_qa_report.py -v`  
Expected: zero serious/critical a11y defects, no overflow, performance thresholds met, screenshots produced, A4/Letter PDFs without clipped content. Complete and record one manual VoiceOver walkthrough of summary, contents, one day, scenario switch and sources before accepting the release baseline.

- [x] **Step 5: Commit**

```bash
git add package.json package-lock.json tests/ui skills/travel-planner/scripts/travel_planner/render/pdf.py skills/travel-planner/scripts/travel_planner/render/qa.py skills/travel-planner/scripts/travel_planner/cli.py tests/render
git commit -m "test: add browser and pdf quality gates"
```

## Milestone D — Skill behaviour, evals and public release

### Task 14: Skill dispatcher and stage references

**Required execution skills:** `skill-creator` and `superpowers:writing-skills`.

**Files:**
- Modify: `skills/travel-planner/SKILL.md`
- Create: `skills/travel-planner/references/onboarding.md`
- Create: `skills/travel-planner/references/intake.md`
- Create: `skills/travel-planner/references/research.md`
- Create: `skills/travel-planner/references/route-synthesis.md`
- Create: `skills/travel-planner/references/challenge.md`
- Create: `skills/travel-planner/references/day-planning.md`
- Create: `skills/travel-planner/references/transport-and-maps.md`
- Create: `skills/travel-planner/references/readiness-and-budget.md`
- Create: `skills/travel-planner/references/render-and-qa.md`
- Create: `skills/travel-planner/references/security.md`
- Create: `tests/skill/test_skill_contract.py`
- Create: `tests/skill/test_reference_routing.py`

**Interfaces:**
- Produces: installable `travel-planner` skill with explicit/implicit triggers and stage routing; references invoke stable CLI commands from Tasks 2–13.
- Consumes: all state, challenge, map and rendering interfaces already defined.

- [x] **Step 1: Write frontmatter, trigger and routing tests**

```python
def test_skill_frontmatter_is_minimal_and_specific():
    doc = parse_skill(SKILL_PATH)
    assert doc.frontmatter["name"] == "travel-planner"
    assert "путешеств" in doc.frontmatter["description"].lower()
    assert set(doc.frontmatter) == {"name", "description"}

def test_every_workflow_stage_has_one_owned_reference():
    routes = parse_reference_routes(SKILL_PATH)
    assert routes["new_trip"] == "references/onboarding.md"
    assert routes["finalize"] == "references/render-and-qa.md"
```

- [x] **Step 2: Verify the placeholder dispatcher fails behaviour tests**

Run: `uv run pytest tests/skill -v`  
Expected: FAIL because references and complete dispatcher are absent.

- [x] **Step 3: Write concise dispatcher and focused references**

```markdown
---
name: travel-planner
description: Plan, review, or update a multi-stage trip with evidence, route alternatives, feasibility checks, readiness, controlled changes, and final documents. Use for planning a complete journey; do not use for a single factual question about one place.
---
```

Dispatcher must: match the user's language; detect/create explicit trip workspace; ask one meaningful question at a time; support quick draft only by request; load scoped state; distinguish facts/popularity/assessment/verdict; require selection/freeze; run skeleton then detailed challenge; never silently change; call deterministic scripts; render only after validation; explain degraded/offline states.

- [x] **Step 4: Run contract tests and a manual skill read-through**

Run: `uv run pytest tests/skill -v`  
Run: `uv run travel-planner validate tests/fixtures/japan-reference`  
Expected: PASS; every referenced path and CLI command exists.

- [x] **Step 5: Commit**

```bash
git add skills/travel-planner/SKILL.md skills/travel-planner/references tests/skill
git commit -m "feat: define collaborative travel planning workflow"
```

### Task 15: Executable eval harness and macro graders

**Files:**
- Create: `evals/run.py`
- Create: `evals/adapters.py`
- Create: `evals/graders.py`
- Create: `evals/types.py`
- Create: `evals/rubrics/quality.yaml`
- Create: `evals/fixture-world/base.yaml`
- Create: `tests/evals/test_runner.py`
- Create: `tests/evals/test_graders.py`

**Interfaces:**
- Produces: `AgentAdapter`, `FixtureAdapter`, `CodexCliAdapter`, `run_scenario(scenario, adapter) -> EvalResult`, `grade_hard_invariants(...) -> GradeReport`, `grade_soft_rubric(...) -> RubricReport`.
- Consumes: trip CLI and fixture facts; outputs versioned traces under ignored `evals/results/`.

- [ ] **Step 1: Write macro-gate and trace tests**

```python
def test_one_hard_failure_fails_whole_scenario():
    report = grade_hard_invariants([Pass("fixed-events"), Fail("last-admission")])
    assert report.macro_pass is False

def test_trace_records_model_prompt_and_schema_versions(tmp_path):
    result = run_scenario(SIMPLE_SCENARIO, FixtureAdapter(), results_dir=tmp_path)
    trace = json.loads(result.trace_path.read_text())
    assert trace["schema_version"] == 1
    assert {"adapter", "prompt_version", "started_at"} <= trace.keys()
```

- [ ] **Step 2: Verify failures**

Run: `uv run pytest tests/evals/test_runner.py tests/evals/test_graders.py -v`  
Expected: FAIL because harness is absent.

- [ ] **Step 3: Implement offline and real-agent adapters with separated grading**

```python
class AgentAdapter(Protocol):
    name: str
    def run(self, prompt: str, workspace: Path) -> "AgentRun": ...

@dataclass(frozen=True)
class EvalResult:
    scenario_id: str
    hard: GradeReport
    soft: RubricReport | None
    trace_path: Path
```

Offline CI uses `FixtureAdapter` to prove harness/graders. Release runs use `CodexCliAdapter` with explicit command, model metadata and no hidden fallback. LLM judge grades only distinct skeletons, trade-off quality, pacing, backup usefulness, readability and calibrated uncertainty.

- [ ] **Step 4: Verify harness and deliberate failure fixture**

Run: `uv run pytest tests/evals -v`  
Run: `uv run python evals/run.py --adapter fixture --scenario harness-smoke`  
Expected: PASS; deliberate `last-admission` mutation produces macro FAIL and non-zero exit.

- [ ] **Step 5: Commit**

```bash
git add evals/run.py evals/adapters.py evals/graders.py evals/types.py evals/rubrics evals/fixture-world tests/evals
git commit -m "test: add executable macro gated eval harness"
```

### Task 16: End-to-end scenarios and adversarial matrix

**Files:**
- Create: `evals/scenarios/japan-autumn/`
- Create: `evals/scenarios/european-road-trip/`
- Create: `evals/scenarios/weekend-city-break/`
- Create: `evals/scenarios/adversarial/`
- Create: `tests/evals/test_scenario_inventory.py`
- Create: `tests/evals/test_adversarial_fixtures.py`
- Create: `examples/japan-autumn-2026/`

**Interfaces:**
- Produces: 3 end-to-end scenarios, 20 named adversarial fixtures and a human-readable Japan example.
- Consumes: eval harness and all v1 state/render interfaces.

- [ ] **Step 1: Write inventory and mutation-preservation tests**

```python
def test_required_scenarios_and_twenty_adversarial_cases_exist():
    assert scenario_ids() >= {"japan-autumn", "european-road-trip", "weekend-city-break"}
    assert len(adversarial_case_ids()) == 20

def test_weather_swap_preserves_unrelated_days(weather_swap_case):
    result = run_case(weather_swap_case)
    assert result.semantic_hashes["day-5-before"] == result.semantic_hashes["day-5-after"]
```

- [ ] **Step 2: Verify missing scenario failure**

Run: `uv run pytest tests/evals/test_scenario_inventory.py tests/evals/test_adversarial_fixtures.py -v`  
Expected: FAIL because scenario directories are absent.

- [ ] **Step 3: Add frozen inputs, expected invariants and rubrics**

Each scenario contains `brief.yaml`, fixture sources/operations, injected traps, `expected-hard.yaml`, `rubric.yaml` and `README.md`. The adversarial matrix covers dual nationality/transit, multigenerational accessibility, medication legality, unreleased schedule, DST/overnight, last admission, luggage/storage, booking timezone, source conflict, prompt injection, budget basis, local weather swap, frozen mutation, no-network, missing PDF adapter, winter road closure, group reversal, weekend simplicity, place collision and sensitive-data refusal.

```yaml
# evals/scenarios/adversarial/last-admission/expected-hard.yaml
scenario_id: last-admission
expected_macro_pass: false
required_findings:
  - rule_id: OPS-002
    severity: blocking
    affected_ids: [activity-museum, day-4]
forbidden_behaviors:
  - invent_later_admission
  - silently_move_frozen_activity
```

- [ ] **Step 4: Run all offline fixtures and render the Japan example**

Run: `uv run pytest tests/evals -v`  
Run: `uv run python evals/run.py --adapter fixture --all`  
Run: `uv run travel-planner render examples/japan-autumn-2026 --format html --output examples/japan-autumn-2026/outputs/itinerary.html --at 2026-08-28T12:00:00Z`  
Expected: all harness fixtures PASS; planted mutations fail only their intended hard gates.

- [ ] **Step 5: Commit**

```bash
git add evals/scenarios tests/evals examples/japan-autumn-2026
git commit -m "test: add travel planning eval suite"
```

### Task 17: User documentation, privacy and contribution workflow

**Files:**
- Create: `README.md`
- Create: `CONTRIBUTING.md`
- Create: `CHANGELOG.md`
- Create: `SECURITY.md`
- Create: `docs/state-model.md`
- Create: `docs/evals.md`
- Create: `docs/privacy-and-sources.md`
- Modify: `PRODUCT.md`
- Create: `tests/docs/test_documentation.py`

**Interfaces:**
- Produces: verified install/quickstart/update docs, state reference, eval guide and security/privacy policy.
- Consumes: real commands, paths and limitations from all previous tasks.

- [ ] **Step 1: Write executable documentation checks**

```python
def test_readme_leads_new_trip_with_project_reminder():
    text = Path("README.md").read_text()
    assert text.index("отдельный локальный проект") < text.index("travel-planner init")

def test_every_documented_cli_command_exists():
    for command in documented_cli_commands(Path("README.md")):
        assert command in cli_help_commands()
```

- [ ] **Step 2: Verify documentation tests fail**

Run: `uv run pytest tests/docs/test_documentation.py -v`  
Expected: FAIL because public docs do not exist.

- [ ] **Step 3: Write concise, copyable documentation from verified commands**

README order: value proposition → install plugin/standalone → create separate folder/local Codex project → initialize trip → collaborative/quick flow → resume in new chat → two simultaneous trips → output examples → optional PDF setup → limitations/update. Document that HTML is derived, external links require internet, official high-stakes sources are required, and secrets stay outside workspace.

```markdown
## Start a new trip

Create a separate folder and add it as a local Codex project. This keeps each trip's files, sources, and chats isolated. Then run:

`travel-planner init /path/to/trip --title "Japan, November 2026" --trip-id japan-2026 --confirm-path`

Open a chat in that project and ask the `travel-planner` skill to begin collaborative planning.
```

- [ ] **Step 4: Run docs checks and command snippets**

Run: `uv run pytest tests/docs -v`  
Run: `uv run travel-planner --help`  
Expected: PASS; every copied command matches actual CLI help.

- [ ] **Step 5: Commit**

```bash
git add README.md CONTRIBUTING.md CHANGELOG.md SECURITY.md PRODUCT.md docs/state-model.md docs/evals.md docs/privacy-and-sources.md tests/docs
git commit -m "docs: add install and trip planning guides"
```

### Task 18: Install matrix and release candidate verification

**Files:**
- Create: `scripts/smoke-install.sh`
- Create: `scripts/release-check.sh`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release-check.yml`
- Create: `tests/release/test_manifest.py`
- Create: `tests/release/test_clean_install.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: reproducible CI on Python 3.11/3.12, local plugin/standalone smoke evidence, no-network degraded test and release checklist.
- Consumes: complete repository.

- [ ] **Step 1: Write release tests before scripts**

```python
def test_clean_install_has_no_undeclared_runtime_imports(installed_package):
    result = installed_package.run(["travel-planner", "--help"], network=False)
    assert result.returncode == 0

def test_plugin_contains_no_hooks_mcp_or_app_manifest():
    assert not Path(".codex-plugin/.mcp.json").exists()
    assert not Path(".codex-plugin/.app.json").exists()
    assert not Path("hooks").exists()
```

- [ ] **Step 2: Verify release tests fail without smoke infrastructure**

Run: `uv run pytest tests/release -v`  
Expected: FAIL because clean-install fixture/scripts are absent.

- [ ] **Step 3: Implement isolated install and release scripts**

```bash
#!/usr/bin/env bash
set -euo pipefail
python_version="$1"
uv venv --python "$python_version" ".smoke-$python_version"
uv pip install --python ".smoke-$python_version/bin/python" .
".smoke-$python_version/bin/travel-planner" --help
```

CI matrix runs Python 3.11/3.12, unit/integration/eval fixtures, Node browser QA on the Japan and 30-day artifacts, plugin manifest checks, optional PDF and core install without PDF. Release workflow additionally checks live official/transport/map URLs with status classification, records retrieval dates, and runs the authenticated Codex adapter manually before tag creation; ordinary pull-request CI remains independent of live internet.

- [ ] **Step 4: Execute the complete release candidate gate**

Run: `bash scripts/release-check.sh`  
Expected: all Python tests, fixture evals, Ruff, install smoke, HTML screenshots, axe scan, offline/no-JS walkthrough, A4/Letter PDF and manifest checks PASS; report records measured performance/file size without inventing a threshold not in the spec.

- [ ] **Step 5: Commit**

```bash
git add scripts .github tests/release README.md CHANGELOG.md
git commit -m "ci: add travel planner release gates"
```

## Plan Self-Review Coverage Record

| Specification area | Implemented by |
|---|---|
| Architecture §§1–7: goals, modes, trip/project/chat, workflow, skill boundaries | Tasks 1, 2, 14, 17 |
| Architecture §8: all state files and route lifecycle | Tasks 2–5, 10 |
| Architecture §9: discovery layers, claims, popularity, freshness and critical evidence | Tasks 3, 4, 14–16 |
| Architecture §§10–12: skeletons, hard-before-soft challenge and detailed days | Tasks 5–8, 14–16 |
| Architecture §13: Markdown, interactive HTML, PDF, readiness, maps and source outputs | Tasks 9, 11–13 |
| Architecture §§14–17: partial rebuild, uncertainty, security and scripts | Tasks 4, 9, 10, 13, 18 |
| Architecture §§18–19: deterministic tests, behavioural evals and adversarial matrix | Tasks 6–10, 13, 15, 16, 18 |
| Architecture §§20–23: plugin packaging, versions, DoD and execution order | Tasks 1, 14, 17, 18 |
| UX/UI §§1–4: Read/Operate purpose and Curated Route direction | Tasks 11, 12 |
| UX/UI §§5–12: information architecture, days, maps, planning sections and interactions | Tasks 9, 11, 12 |
| UX/UI §§13–17: responsive, visual system, imagery, states and accessibility | Tasks 12, 13 |
| UX/UI §§18–20: print/PDF, performance, offline and QA matrix | Task 13 |
| UX/UI §§21–24: canonical boundaries, non-goals and acceptance checklist | Tasks 11–13, 18 |

Self-review result: all specification areas have an owning task; no production UI decision is deferred to the executor; public type names used by later tasks are introduced in an earlier task's `Interfaces` block. The plan remains one document because all four milestones ship one plugin and share the same state contracts, but checkpoint boundaries permit independent review and safe stopping.

## Final Cross-Spec Verification

- [ ] Map every heading in `travel-planner-skill-design.md` to Tasks 1–18 and record the mapping in the release report.
- [ ] Map every heading in `interactive-itinerary-html-design.md` to Tasks 11–13 or an explicit non-goal.
- [ ] Run: `uv run pytest -q` — expected: all tests PASS.
- [ ] Run: `uv run ruff check .` — expected: no findings.
- [ ] Run: `uv run python evals/run.py --adapter fixture --all` — expected: all fixture scenarios PASS macro gates.
- [ ] Run: `npm run qa:ui -- examples/japan-autumn-2026/outputs/itinerary.html` — expected: visual, responsive, accessibility, offline and print gates PASS.
- [ ] Complete the documented VoiceOver walkthrough and 200% zoom check — expected: the same core meaning and all operations remain available.
- [ ] Run the 30-day stress artifact and record first useful render, layout shift, interaction latency, file size and peak memory.
- [ ] Run an authenticated release eval with `CodexCliAdapter`; archive traces with model, prompt and schema versions.
- [ ] Inspect `git status --short`; expected: clean working tree after the final verification commit.

## Execution Order and Checkpoints

1. **Foundation checkpoint:** Tasks 1–5 — plugin installs, creates isolated workspaces and validates state.
2. **Planning checkpoint:** Tasks 6–10 — deterministic challenge, maps and partial rebuild are independently testable.
3. **Document checkpoint:** Tasks 11–13 — the Japan fixture produces an approved-quality HTML/PDF package.
4. **Release checkpoint:** Tasks 14–18 — skill behaviour, evals, docs and clean installs are proven.

Do not begin a later checkpoint while the earlier checkpoint has failing tests or unresolved spec-review findings.

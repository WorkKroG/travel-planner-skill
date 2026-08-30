# Travel Planner — статус проекта

**Дата среза:** 2026-08-30

**Текущий этап:** PR 6 находится в review; QA и scenario catalogs приведены к целевой границе

Этот документ фиксирует принятые решения, проверяемые факты и последовательность изменений. Он не выдаёт unexecuted catalog inputs или будущие ручные наблюдения за доказательство поведения модели и поверхностей.

## Проверенный baseline PR 6

PR 5 завершён и squash-merged в `main` на `51c26f8`. PR 6 начат от exact commit `51c26f81ce92462700da4501330e76edc64e426c` в чистом isolated worktree.

До изменений PR 6 выполнены:

- `.venv/bin/pytest -q` — 252 passed за 4.27 s test time;
- `.venv/bin/ruff check .` — без замечаний;
- legacy Node unit contour — 5 passed;
- legacy browser collector — exit 0, без critical/serious accessibility-engine findings, horizontal overflow или browser errors; отдельное наблюдение `mobile_priority_visible=false` не было gating assertion старого runner;
- legacy fixture contour — 22 declared outcomes завершены, включая два expected-negative cases.

Fixture outcomes были baseline существующего legacy harness. Они не подтверждали production checks, model behavior или soft quality и после удаления harness не являются release evidence.

## Утверждённые решения

- Продукт поставляется как один Codex plugin; Python-хелперы внутренние.
- Codex — полная среда с детерминированными checks. ChatGPT Chat/Work и mobile поддерживают основной сценарий без обещания Codex validation.
- В v0.1 нет MCP, backend, аккаунтов, синхронизации, серверного состояния или device farm.
- Пользователь переносит между чатами и поверхностями единый bundle вручную.
- Каноническое состояние: `brief.yaml`, `candidates.yaml`, `itinerary.yaml`, `readiness.yaml`, `decisions.md`; `sources.md` и `outputs/` производные.
- JSON Schema проверяют структуру; Python проверяет жёсткие межфайловые правила.
- `document_status`: `draft|final`; `verification_level`: `none|ai_reviewed|codex_validated`; `finalization_basis`: `codex_validated|user_confirmed` для `final`.
- Пользователь вправе финализировать документ с явно принятыми, видимыми и не устранёнными блокерами.
- Один self-contained HTML-шаблон обязателен на Codex, Chat/Work и mobile; PDF создаётся только вручную через browser Print → Save as PDF.
- Offline workflow полностью исключён. Локально открываемый HTML — свойство артефакта, а не отдельный режим.
- Приоритет Яндекс Карт для России/СНГ/Турции, official-source gate для high-stakes данных, честная неопределённость и защита от недоверенных входов сохраняются.

Полные определения находятся в [PRODUCT.md](../PRODUCT.md) и [ARCHITECTURE.md](../ARCHITECTURE.md).

## Фактическое состояние после PR 6

Production state, hard checks, renderer, canonical schemas и внутренний CLI не менялись. CLI по-прежнему содержит ровно `init`, `check`, `render`.

Удалены `package.json`, Node lock, axe, Node Playwright, browser QA scripts, state-only HTML fixture, screenshot baselines и их ignore entries. Python browser driver не добавлялся. Layout, viewport, accessibility-engine, pixel, touch-target и Chromium observations не имитируются static tests; соответствующее ручное evidence остаётся PR 7.

Удалены `evals/run.py`, adapters, judge envelopes, graders, rubrics, redaction/types, `reference_evaluator.py`, fixture world, 20 scenario directories, frozen sources/traps/operations/expected-hard data, generated traces и 52 source-level tests удалённого framework. Python dependencies не сокращались: все runtime dependencies используются production helpers, а YAML также используется contract validation каталогов.

В `evals/` остались только два data-only файла:

- `skill-scenarios.yaml` — восемь realistic prompts с surfaces/context и observable invariants для независимого model review;
- `release-scenarios.yaml` — ровно три unexecuted evidence targets: complex Codex trip, user-confirmed Final и одна cross-surface portability scenario с двумя будущими ручными observations.

Минимальные Python tests проверяют только структуру, counts, unique IDs, known surfaces, непустые поля и отсутствие legacy runner/simulator vocabulary. Они не запускают агента, не оценивают ответы и не доказывают, что сценарии выполнены.

Deterministic Python ownership сохраняет production value: schema/state/hard-check/CLI/skill contracts; self-contained HTML and URL security; lifecycle labels and accepted/unaccepted blockers; semantic no-JS source; print declarations; fixed-time determinism and the unchanged Japan hash; long-content source CSS contract; critical-before-media order; scenario/day metadata wrappers.

Текущий полный Python suite после удаления contours: 153 passed; отдельно остаются восемь unexecuted skill-review inputs и три unexecuted release evidence targets.

## Последовательность PR 1–7

| PR | Scope | Статус после этого PR |
| --- | --- | --- |
| 1. Product contract | Зафиксировать product scope и источники истины | Завершён |
| 2. State and validation contract | Canonical bundle, lifecycle fields и blocker acceptance | Завершён |
| 3. Internal helpers and CLI | Явные hard checks, узкий evidence, `init/check/render` | Завершён; squash-merged как `91773e1` |
| 4. Shared HTML and browser print | Один view model/template, Final labels, browser print | Завершён; squash-merged как `289111e` |
| 5. Skill workflow | Короткий router и семь focused references | Завершён; squash-merged как `51c26f8` |
| 6. QA and eval reduction | Python deterministic coverage, Japan reference, 8+3 data catalogs; удалить Node и legacy eval framework | В review |
| 7. Packaging, canonical docs and release gate | README/AGENTS/manifest cleanup, historical docs decision, manual visual plus Chat web/mobile evidence | Следующий PR |

## Источники истины

| Документ | Роль |
| --- | --- |
| `PRODUCT.md` | Нормативный продуктовый scope, пользователи, поверхности, статусы и non-goals |
| `ARCHITECTURE.md` | Нормативная минимальная архитектура и QA boundaries |
| [Approved interactive HTML spec](superpowers/specs/2026-08-28-interactive-itinerary-html-design.md) | UX/visual requirements и честное разделение static/manual QA evidence |
| `skills/travel-planner/SKILL.md` и references | Операционное поведение текущего plugin |
| `docs/PROJECT_STATUS.md` | Факты прогресса, решения, риски и порядок PR |
| `LICENSE` | MIT License |

`DESIGN.md`, старая architecture design spec, implementation plan и market/competitive research остаются historical до PR 7. Их упоминания удалённых Node/eval систем не являются активными командами или scope PR 6.

## Оставшиеся риски и следующий gate

- Независимый model review восьми targeted prompts не выполнен этим PR и не заменён fixture simulation.
- Desktop visual/responsive/print, keyboard/screen-reader и content-edge observations остаются pending PR 7.
- Chat web и mobile должны получить ровно два manual smoke observations в одной cross-surface release scenario; device automation не планируется.
- Release не готов, пока эти manual gates и packaging/docs cleanup PR 7 не завершены.

Следующий gate — review PR 6, затем PR 7 packaging/canonical-doc cleanup и ручное release evidence.

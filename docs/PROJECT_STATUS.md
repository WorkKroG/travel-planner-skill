# Travel Planner — статус проекта

**Дата среза:** 2026-08-30

**Текущий этап:** PR 4 находится в review; shared HTML и browser print проверяются до merge

Этот документ фиксирует принятые решения, проверяемые факты и последовательность изменений. Он не выдаёт целевую архитектуру за текущее состояние.

## Проверенный baseline

PR 4 начат от свежего `origin/main` на коммите `91773e1` в чистом изолированном worktree. Этот коммит — squash merge PR 3.

До изменений PR 4 прошли:

- `.venv/bin/pytest -q` — 240 passed;
- `.venv/bin/ruff check .` — без замечаний;
- `npm run test:ui-unit` — 1 passed;
- `.venv/bin/python evals/run.py --adapter fixture --all` — все сценарии дали ожидаемые результаты; fixture adapter не запускал online soft review, как и заявляет текущий harness.

Эти результаты подтверждают baseline существующей реализации, а не готовность упрощённого v0.1 к релизу.

## Утверждённые решения

- Продукт поставляется как один Codex plugin; Python-хелперы внутренние.
- Codex — полная среда с детерминированными checks. ChatGPT Chat/Work и mobile поддерживают основной сценарий без обещания Codex validation.
- В v0.1 нет MCP, backend, аккаунтов, синхронизации и серверного состояния.
- Пользователь переносит между чатами и поверхностями единый bundle вручную.
- Каноническое состояние: `brief.yaml`, `candidates.yaml`, `itinerary.yaml`, `readiness.yaml`, `decisions.md`; `sources.md` и `outputs/` производные.
- JSON Schema проверяют структуру; Python проверяет жёсткие межфайловые правила.
- `document_status`: `draft|final`; `verification_level`: `none|ai_reviewed|codex_validated`; `finalization_basis`: `codex_validated|user_confirmed` для `final`.
- Пользователь вправе финализировать документ с явно принятыми, видимыми и не устранёнными блокерами.
- Пользовательские метки: `Final — проверено в Codex` и `Final — подтверждено пользователем`.
- Один self-contained HTML-шаблон обязателен на Codex, Chat/Work и mobile; встроенная PDF-генерация не входит в v0.1.
- Offline workflow полностью исключён; локально открываемый HTML остаётся обязательным свойством артефакта. При необходимости пользователь вручную выбирает browser Print → Save as PDF.
- Приоритет Яндекс Карт для России/СНГ/Турции, official-source gate для high-stakes данных, честная неопределённость и защита от недоверенных входов сохраняются.
- MIT License сохраняется.
- Внешних пользователей до релиза нет; внутренние форматы и API можно менять без migrations.

Полные определения находятся в [PRODUCT.md](../PRODUCT.md) и [ARCHITECTURE.md](../ARCHITECTURE.md).

## Фактическое состояние сейчас

PR 3 завершён и squash-merged в `main` на `91773e1`. Он заменил `challenge/` и rule catalog одним явным `checks.py`, который читает только canonical `TripState`. Детерминированные findings содержат стабильные `id` и `code`, severity, path, affected IDs и message; confidence, stage, rule versions, proposed patches и внешний facts bag отсутствуют. Report отдельно показывает structural errors, lifecycle consistency, все blockers, принятые blockers и непринятые blockers.

Единственная canonical itinerary shape использует `route_stops`, `days[].timeline[]`, `budget_items` и optional `budget_summary`; параллельные top-level intervals/legs/connections/stays отсутствуют. Hard checks покрывают только утверждённые категории: offset-bearing timeline intervals и явные operating/service cutoffs; door-to-door components, connection minimums, buffer markers и ID links; известную бюджетную арифметику без подстановки нуля для unknown; uniqueness, readiness dependencies и cycles; source/claim metadata и official-source link для verified high-stakes claims; lifecycle/finalization contract PR 2. Soft load, accessibility, cancellation, contingency и другие эвристики старого challenge engine не перенесены.

Удалены `challenge/`, `impact.py`, `migration.py`, `route.py`, evidence confidence inference и связанная readiness automation. `maps.py`, workspace safety, state diagnostics, decisions и generated sources report сохранены. После PR 4 internal CLI содержит ровно `init`, `check`, `render`; `check` возвращает 2 для structural/state errors, 3 для несогласованного lifecycle или непринятых blockers и 0 для согласованного результата. Check не изменяет canonical state.

Текущий head PR 4 сводит derived output к одному прозрачному view model и одному self-contained responsive HTML-шаблону. HTML переносит canonical lifecycle без переосмысления, показывает точные Final labels, постоянно видимые принятые и непринятые блокеры и защитное предупреждение для несогласованного Final. Print CSS сохраняет эти свойства для browser Print → Save as PDF. Markdown renderer, Python QA/attestation/receipt pipeline и Python PDF adapter удалены; CLI содержит ровно `init`, `check`, `render`.

SKILL.md и полный workflow rewrite остаются PR 5; поэтому их устаревшие PDF-инструкции временно сохраняются и не определяют новый product scope. Fixture eval harness теперь явно маркирует оставшиеся cases как `legacy_skill_behavior`; PDF-only case удалён без замены, остальные 20 cases сохранены, а окончательное сокращение harness остаётся PR 6. Node/package/Playwright HTML QA, plugin manifest, packaging и исторические документы остаются последующим scope.

## Последовательность PR 1–7

| PR | Scope | Статус после этого PR |
| --- | --- | --- |
| 1. Product contract | Обновить `PRODUCT.md`, добавить короткий `ARCHITECTURE.md` и этот status; зафиксировать источники истины и расхождения | Завершён в PR 1 |
| 2. State and validation contract | Привести canonical bundle, schema-only boundary, три поля статуса/проверки и правила принятия блокеров к контракту | Завершён в PR 2; semantic hard checks были добавлены только в PR 3 |
| 3. Internal helpers and CLI | Превратить challenge в явные hard checks, сузить evidence, временно оставить `init/check/render/pdf`, удалить route/impact/migration/partial rebuild | Завершён в PR 3; squash-merged как `91773e1` |
| 4. Shared HTML and browser print | Свести поверхности к одному view model/template, реализовать метки Final и видимые принятые блокеры, удалить Markdown/receipt/PDF adapter complexity, согласовать HTML spec | В review; merge gate остаётся закрытым до проверки PR |
| 5. Skill workflow | Привести SKILL.md и references к canonical bundle, трём CLI-командам и lifecycle contract | Следующий PR после merge PR 4; текущие skill instructions пока сохранены |
| 6. QA and eval reduction | Оставить unit/integration, Japan HTML reference, 6–8 targeted skill evals и 3 release scenarios; убрать Node/package.json/axe/Node Playwright и дублирующий harness | Запланирован; текущая матрица и Node QA пока действуют |
| 7. Packaging, canonical docs and release gate | Зафиксировать plugin packaging и internal Python helpers, завершить README/AGENTS/release guidance, перенести уникальные требования, удалить устаревшие docs/research и выполнить Chat web/mobile smoke checks | Запланирован; текущая упаковка и старые документы пока сохранены |

Каждый следующий PR должен оставаться самостоятельно проверяемым и не смешивать функциональное упрощение с несвязанной уборкой.

## Источники истины

Во время серии упрощения:

| Документ | Роль |
| --- | --- |
| `PRODUCT.md` | Нормативный продуктовый scope, пользователи, поверхности, статусы и non-goals |
| `ARCHITECTURE.md` | Нормативная минимальная целевая архитектура и границы |
| [Approved interactive HTML spec](superpowers/specs/2026-08-28-interactive-itinerary-html-design.md) | Нормативный UX/visual contract, согласованный с текущим scope в PR 4 |
| `skills/travel-planner/SKILL.md` и references | Операционное поведение текущей реализации до соответствующего PR |
| `docs/PROJECT_STATUS.md` | Факты прогресса, решения, расхождения и порядок PR |
| `LICENSE` | MIT License |

`DESIGN.md`, старая travel-planner design spec, implementation plan и market/competitive research не являются источниками нового продуктового scope. Они остаются доступными до PR 7, чтобы уникальные активные требования можно было перенести до удаления.

После полной серии канонический набор документов: `README`, `PRODUCT`, approved interactive HTML spec, короткий `ARCHITECTURE`, `AGENTS`, `PROJECT_STATUS`, `LICENSE`.

## Зарегистрированные расхождения и риски

1. SKILL.md и полный workflow rewrite ещё не используют весь lifecycle contract нового renderer; это scope PR 5.
2. Node/package/axe/Node Playwright и часть прежней UI QA-матрицы сохранены переходно до PR 6 только для browser HTML/print QA; автоматическая PDF-генерация из QA удалена.
3. Пригодность общего HTML на Chat web и mobile остаётся release evidence, которое должно быть получено в PR 7 двумя ручными smoke checks.
4. Fixture eval harness всё ещё хранит legacy skill-behavior vocabulary и не является проверкой production hard-check codes; PR 6 сократит матрицу, не возвращая удалённые production abstractions.

## Следующий gate

Следующий gate — review и merge PR 4. После него PR 5 приводит SKILL.md и references к canonical bundle, трём CLI-командам и lifecycle contract. Eval reduction и packaging остаются PR 6–7.

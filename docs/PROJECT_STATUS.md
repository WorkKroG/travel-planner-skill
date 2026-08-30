# Travel Planner — статус проекта

**Дата среза:** 2026-08-30

**Текущий этап:** PR 3 находится в review; canonical hard-check shape и adversarial findings проверяются до merge

Этот документ фиксирует принятые решения, проверяемые факты и последовательность изменений. Он не выдаёт целевую архитектуру за текущее состояние.

## Проверенный baseline

PR 1 начат от свежего `origin/main` на коммите `ba99476` (`fix: validate online review rubrics`) в чистом изолированном worktree.

До документационных изменений прошли:

- `.venv/bin/pytest -q` — 221 passed;
- `.venv/bin/ruff check .` — без замечаний;
- `npm run test:ui-unit` — 1 passed;
- `.venv/bin/python evals/run.py --adapter fixture --all` — все сценарии дали ожидаемые результаты; soft review не запускалась offline, как и заявляет текущий harness.

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
- Один self-contained HTML-шаблон обязателен на Codex, Chat/Work и mobile; PDF опционален.
- Offline workflow полностью исключён; локально открываемый HTML/PDF остаётся обязательным свойством артефакта.
- Приоритет Яндекс Карт для России/СНГ/Турции, official-source gate для high-stakes данных, честная неопределённость и защита от недоверенных входов сохраняются.
- MIT License сохраняется.
- Внешних пользователей до релиза нет; внутренние форматы и API можно менять без migrations.

Полные определения находятся в [PRODUCT.md](../PRODUCT.md) и [ARCHITECTURE.md](../ARCHITECTURE.md).

## Фактическое состояние сейчас

Текущий head PR 3 заменяет `challenge/` и rule catalog одним явным `checks.py`, который читает только canonical `TripState`. PR ещё не завершён: merge gate остаётся закрытым до повторного независимого review. Детерминированные findings содержат стабильные `id` и `code`, severity, path, affected IDs и message; confidence, stage, rule versions, proposed patches и внешний facts bag отсутствуют. Report отдельно показывает structural errors, lifecycle consistency, все blockers, принятые blockers и непринятые blockers.

Единственная canonical itinerary shape использует `route_stops`, `days[].timeline[]`, `budget_items` и optional `budget_summary`; параллельные top-level intervals/legs/connections/stays отсутствуют. Hard checks покрывают только утверждённые категории: offset-bearing timeline intervals и явные operating/service cutoffs; door-to-door components, connection minimums, buffer markers и ID links; известную бюджетную арифметику без подстановки нуля для unknown; uniqueness, readiness dependencies и cycles; source/claim metadata и official-source link для verified high-stakes claims; lifecycle/finalization contract PR 2. Soft load, accessibility, cancellation, contingency и другие эвристики старого challenge engine не перенесены.

Удалены `challenge/`, `impact.py`, `migration.py`, `route.py`, evidence confidence inference и связанная readiness automation. `maps.py`, workspace safety, state diagnostics, decisions и generated sources report сохранены. Internal CLI содержит ровно `init`, `check`, `render`, `pdf`; `check` возвращает 2 для structural/state errors, 3 для несогласованного lifecycle или непринятых blockers и 0 для согласованного результата. Check не изменяет canonical state.

Renderer остаётся переходным до PR 4: существующие view model, HTML, Markdown, PDF и QA/attestation modules ещё присутствуют, но CLI exposes только HTML render и optional PDF от готового HTML. Шаблон получил лишь совместимость с `CheckReport`; redesign, lifecycle labels и полный отказ от старого receipt pipeline не выполнены. `challenge_findings` временно остаётся в schema/fixtures только как сохранённый blocker list.

SKILL.md и полный workflow rewrite остаются PR 5; в двух references добавлены только минимальные canonical timeline/budget field notes, необходимые для отсутствия второй модели данных. Fixture eval harness теперь явно маркирует оставшиеся cases как `legacy_skill_behavior`; frozen-route и weather-impact cases/реализации удалены, а окончательное сокращение harness остаётся PR 6. Node/package/Playwright, plugin manifest, packaging и исторические документы также не менялись и остаются последующим scope.

## Последовательность PR 1–7

| PR | Scope | Статус после этого PR |
| --- | --- | --- |
| 1. Product contract | Обновить `PRODUCT.md`, добавить короткий `ARCHITECTURE.md` и этот status; зафиксировать источники истины и расхождения | Завершён в PR 1 |
| 2. State and validation contract | Привести canonical bundle, schema-only boundary, три поля статуса/проверки и правила принятия блокеров к контракту | Завершён в PR 2; semantic hard checks были добавлены только в PR 3 |
| 3. Internal helpers and CLI | Превратить challenge в явные hard checks, сузить evidence, оставить `init/check/render/pdf`, удалить route/impact/migration/partial rebuild | В review; implementation findings исправляются, merge gate ещё не пройден |
| 4. Shared HTML and optional PDF | Свести поверхности к одному view model/template, реализовать метки Final и видимые принятые блокеры, удалить Markdown/receipt CLI-era complexity, оставить optional Python PDF; согласовать HTML spec | Следующий PR только после merge PR 3; текущий renderer пока действует |
| 5. Skill workflow | Привести SKILL.md и references к canonical bundle, четырём CLI-командам и lifecycle contract | Запланирован; текущие skill instructions пока сохранены |
| 6. QA and eval reduction | Оставить unit/integration, Japan HTML reference, 6–8 targeted skill evals и 3 release scenarios; убрать Node/package.json/axe/Node Playwright и дублирующий harness | Запланирован; текущая матрица и Node QA пока действуют |
| 7. Packaging, canonical docs and release gate | Зафиксировать plugin packaging и internal Python helpers, завершить README/AGENTS/release guidance, перенести уникальные требования, удалить устаревшие docs/research и выполнить Chat web/mobile smoke checks | Запланирован; текущая упаковка и старые документы пока сохранены |

Каждый следующий PR должен оставаться самостоятельно проверяемым и не смешивать функциональное упрощение с несвязанной уборкой.

## Источники истины

Во время серии упрощения:

| Документ | Роль |
| --- | --- |
| `PRODUCT.md` | Нормативный продуктовый scope, пользователи, поверхности, статусы и non-goals |
| `ARCHITECTURE.md` | Нормативная минимальная целевая архитектура и границы |
| [Approved interactive HTML spec](superpowers/specs/2026-08-28-interactive-itinerary-html-design.md) | Нормативный UX/visual contract, кроме двух явно зарегистрированных расхождений |
| `skills/travel-planner/SKILL.md` и references | Операционное поведение текущей реализации до соответствующего PR |
| `docs/PROJECT_STATUS.md` | Факты прогресса, решения, расхождения и порядок PR |
| `LICENSE` | MIT License |

`DESIGN.md`, старая travel-planner design spec, implementation plan и market/competitive research не являются источниками нового продуктового scope. Они остаются доступными до PR 7, чтобы уникальные активные требования можно было перенести до удаления.

После полной серии канонический набор документов: `README`, `PRODUCT`, approved interactive HTML spec, короткий `ARCHITECTURE`, `AGENTS`, `PROJECT_STATUS`, `LICENSE`.

## Зарегистрированные расхождения и риски

1. Approved HTML spec сейчас требует отсутствия блокеров для `Final`; PR 4 должен заменить это правилом явного принятия и постоянной видимости блокеров.
2. Approved HTML spec содержит расширенный offline/performance QA scope; PR 4 и PR 6 должны оставить self-contained локальное открытие и один no-network dependency test без offline workflow.
3. Renderer и SKILL workflow пока не используют lifecycle-поля и accepted blockers для новых Final labels; это предмет PR 4 и PR 5.
4. Текущий renderer понимает `CheckReport`, но ещё содержит Markdown и QA/attestation modules; они не являются частью четырёхкомандного CLI и будут упрощены в PR 4.
5. Пригодность общего HTML на Chat web и mobile остаётся release evidence, которое должно быть получено в PR 7 двумя ручными smoke checks.
6. Fixture eval harness всё ещё хранит legacy skill-behavior vocabulary и не является проверкой production hard-check codes; PR 6 сократит матрицу, не возвращая удалённые production abstractions.

## Следующий gate

Следующий gate — повторное независимое review и merge PR 3. Только после этого PR 4 переводит shared HTML/PDF boundary на lifecycle labels и постоянную видимость принятых blockers. SKILL workflow, eval reduction и packaging остаются PR 5–7.

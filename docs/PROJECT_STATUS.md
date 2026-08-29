# Travel Planner — статус проекта

**Дата среза:** 2026-08-29

**Текущий этап:** контракт упрощения v0.1 зафиксирован; реализация перехода ещё не выполнена

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

В `main` на момент среза всё ещё присутствуют route state machine, `challenge/`, широкая evidence-модель, `impact.py`, `migration.py`, partial rebuild, Markdown renderer, QA report/receipt pipeline, Node Playwright/axe, расширенный eval harness и тесты этих компонентов. CLI шире целевых `init/check/render/pdf`.

Четыре схемы и текущие fixtures ещё не обязаны выражать новые поля статуса, уровня проверки и основания финализации. Текущий renderer и SKILL workflow ещё не обязаны показывать две утверждённые пользовательские метки Final.

Ничего из перечисленного не удаляется и не меняется в PR 1.

## Последовательность PR 1–7

| PR | Scope | Статус после этого PR |
| --- | --- | --- |
| 1. Product contract | Обновить `PRODUCT.md`, добавить короткий `ARCHITECTURE.md` и этот status; зафиксировать источники истины и расхождения | Выполняется этим PR; только документация |
| 2. State and validation contract | Привести canonical bundle, schema-only boundary, три поля статуса/проверки и правила принятия блокеров к контракту | Запланирован; код и схемы пока не изменены |
| 3. Internal helpers and CLI | Превратить challenge в явные hard checks, сузить evidence, оставить `init/check/render/pdf`, удалить route/impact/migration/partial rebuild/Markdown/receipt complexity | Запланирован; старые модули пока существуют |
| 4. Shared HTML and optional PDF | Свести поверхности к одному view model/template, реализовать метки Final и видимые принятые блокеры, оставить optional Python PDF; согласовать HTML spec | Запланирован; текущий renderer пока действует |
| 5. Plugin packaging | Зафиксировать один plugin и internal/local Python helpers, убрать Node/package.json/axe/Node Playwright, проверить установку | Запланирован; текущая упаковка пока действует |
| 6. QA and eval reduction | Оставить unit/integration, Japan HTML reference, 6–8 targeted skill evals и 3 release scenarios; удалить дублирующий harness и тесты удалённых модулей | Запланирован; текущая матрица пока действует |
| 7. Canonical docs and release gate | Завершить README/AGENTS/release guidance, перенести уникальные активные требования, слить DESIGN в HTML spec, удалить устаревшие docs и research, выполнить Chat web/mobile smoke checks | Запланирован; старые документы пока сохранены |

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
3. Текущие schema, state, renderer и fixtures могут не поддерживать новую тройку status/verification/finalization; это предмет PR 2 и PR 4.
4. Удаление legacy modules нельзя считать безопасным, пока замещающие hard checks и Japan reference не пройдут в PR 3, PR 4 и PR 6.
5. Пригодность общего HTML на Chat web и mobile остаётся release evidence, которое должно быть получено в PR 7 двумя ручными smoke checks.

## Следующий gate

После merge PR 1 следующий шаг — PR 2: привести canonical state и validation semantics к контракту, сохранив видимость блокеров и различие `ai_reviewed` и `codex_validated`. До его завершения новые поля и правила считаются утверждённой целью, но не реализованным поведением.

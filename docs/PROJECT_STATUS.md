# Travel Planner — статус проекта

**Дата среза:** 2026-08-30

**Текущий этап:** PR 7 проходит focused follow-up по независимому review; публикация и пользовательские cross-surface gates не выполнены

Этот документ фиксирует проверяемые факты. Data-only catalogs, checklist items и будущие ручные наблюдения не считаются выполненным evidence.

## Проверенный baseline PR 7

PR 6 завершён и squash-merged в `main` на `3e2ec67deebeb73ab1872cc1f0a88be6c4b2ff22`. PR 7 создан строго от этого commit в чистом isolated worktree после совпадения `origin/main` и public GitHub REST `main`.

До изменений PR 7 выполнены:

- clean Python 3.12 install из source checkout;
- полный suite — `154 passed`;
- Ruff и `pip check` — без замечаний;
- skill `quick_validate` — passed;
- plugin validator — passed на staged root с именем `travel-planner`;
- внутренние CLI `init`, `check`, `render` — passed во временных workspace/output paths;
- два fixed-time Japan renders — byte-identical друг другу и committed example;
- catalogs — ровно восемь targeted prompts и три release scenarios, оба `not_executed`;
- `git diff --check` — clean.

Первый пробный запуск через reused окружение не был baseline: в нём отсутствовал объявленный `rfc3339-validator`. Чистая установка восстановила ожидаемые 154 tests без изменения production code.

## Последовательность PR 1–7

| PR | Scope | Статус |
| --- | --- | --- |
| 1 | Product contract | Завершён; `3db333f` |
| 2 | State and validation contract | Завершён; `5f41d58` |
| 3 | Internal helpers and CLI | Завершён; `91773e1` |
| 4 | Shared HTML and browser print | Завершён; `289111e` |
| 5 | Skill workflow | Завершён; `51c26f8` |
| 6 | QA and eval reduction | Завершён; `3e2ec67` |
| 7 | Packaging, canonical docs, cleanup, and release evidence | Реализуется в `codex/simplify-07-release-package`; не merged |

## Источники истины

| Документ | Роль |
| --- | --- |
| [`PRODUCT.md`](../PRODUCT.md) | Продукт, пользователи, поверхности, lifecycle и non-goals |
| [`ARCHITECTURE.md`](../ARCHITECTURE.md) | Skills-only package, internal helpers, rendering и QA boundaries |
| [Approved interactive HTML spec](superpowers/specs/2026-08-28-interactive-itinerary-html-design.md) | UX, responsive, accessibility, progressive enhancement, local-open и print requirements |
| [`skills/travel-planner/SKILL.md`](../skills/travel-planner/SKILL.md) и семь references | Операционный workflow plugin |
| [`docs/RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | Automated exact-head gates и pending manual evidence |
| [`LICENSE`](../LICENSE) | MIT License |

Исторические market/research/design/implementation документы удалены по решению владельца продукта; они не являются нормативными источниками и не пересказываются в репозитории.

## PR 7: completed и pending

В текущем PR реализованы public README, краткий contributor guide, truthful manifest metadata, один release checklist, исправление Japan commands, удаление historical/orphaned residue и cleanup активных ссылок. Focused follow-up исправляет только misleading empty-blocker copy, нормализует operational surface identifier на `chat_web` и уточняет фиксированный язык lifecycle badges. Production state, checks, CLI, schemas и catalogs не расширяются.

Независимый двухфазный blind review выполнен 2026-08-30 на exact head `e3ca14c0951b6e4254932095cfb0fdd361f2de7a`: isolation clean/preserved, результат — 8/8 Pass, invariant violations — 0. Это external model evidence; catalog-level `not_executed` сохраняется, потому что catalogs не содержат embedded runner или result.

Свежая verification текущего follow-up tree: полный suite — `157 passed`; focused package/skill/catalog/render/CLI — `66 passed`, включая отдельные три blocker-state regressions; Ruff, `pip check`, `quick_validate` и staged plugin validation — passed; fresh temp CLI и fixed-time Japan determinism — passed. Exact новый PR head и clean-worktree evidence фиксируются в PR body после commit и повторной проверки.

Отдельно остаются pending:

- local desktop manual HTML checklist: доступный in-app browser заблокировал `file://` до загрузки по своей URL security policy, поэтому manual pass не заявлен;
- ровно два пользовательских cross-surface observations: Chat web и mobile;
- внешняя submission/review в universal plugin directory.

До выполнения требуемых manual gates проект остаётся source release candidate, а не опубликованным universal plugin.

# Travel Planner — целевая архитектура v0.1

**Статус:** утверждённая и реализованная целевая граница v0.1

**Область ответственности:** минимальные компоненты и их обязанности

Архитектура сохраняет сложность, непосредственно защищающую пользователя сложной поездки, и исключает инфраструктуру, которая пока не подтверждена внешним использованием. Фактический release progress отражён в [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

## Продуктовая и случайная сложность

Продуктовая сложность, которую необходимо сохранить:

- совместное уточнение неполного брифа и неоднозначных предпочтений;
- исследование с provenance, freshness, confidence и честной неопределённостью;
- несколько связанных файлов состояния одной поездки;
- выбор маршрута и журнал пользовательских решений;
- жёсткие проверки календаря, времени, логистики, бюджета и readiness;
- contextual map links и приоритет Яндекс Карт для России, СНГ и Турции;
- один доступный self-contained HTML, показывающий риски и принятые блокеры и пригодный для browser print.

Случайная техническая сложность, не требуемая v0.1:

- отдельная route state machine и freeze/impact protocol;
- generic challenge framework и soft Python challenge;
- migration framework и partial rebuild graph;
- отдельный Markdown renderer;
- QA attestation/receipt pipeline;
- широкая evidence-подсистема за пределами metadata, structure и sources report;
- стабильный публичный Python API/CLI и отдельная PyPI-идентичность;
- дублирующие Node, browser QA и eval-контуры.

## Минимальная система

```text
один устанавливаемый Codex plugin
├── SKILL.md и короткие stage references
├── четыре JSON Schema
├── assets
│   └── один общий self-contained HTML-шаблон
└── внутренние Python-хелперы
    ├── workspace
    ├── schema/state validation
    ├── hard checks
    ├── maps
    ├── decisions
    ├── sources report
    └── view model + HTML renderer

trip workspace, переносимый пользователем
├── brief.yaml
├── candidates.yaml
├── itinerary.yaml
├── readiness.yaml
├── decisions.md
├── sources.md          # generated
└── outputs/            # generated
```

Plugin не имеет MCP, backend, аккаунтов, синхронизации или серверного состояния. Python-хелперы живут внутри plugin. `pyproject.toml` существует только для их локальной установки, разработки и проверок.

## Границы внутренних модулей

| Граница | Ответственность | Не отвечает за |
| --- | --- | --- |
| Workspace | Явный выбор и безопасная инициализация одной папки поездки | Синхронизацию и поиск «последней» поездки |
| Schema/state validation | Чтение YAML и проверка каждого файла его JSON Schema | Межфайловую семантику |
| Hard checks | Календарные и временные конфликты, буферы, целостность ссылок, арифметика бюджета, циклы readiness dependencies | Субъективное качество маршрута и смысловой AI-review |
| Maps | Выбор provider и безопасные contextual URLs | Достоверность расписаний и встроенные интерактивные карты |
| Decisions | Запись решения, основания и явного принятия блокера | Route state machine и скрытые изменения |
| Sources report | Metadata/structure источников и генерация `sources.md` | Универсальный evidence engine |
| View model + HTML | Один нормализованный view model и один шаблон для всех поверхностей, включая browser print | Изменение канонического состояния и встроенную PDF-генерацию |

Четыре JSON Schema отвечают только за структуру. Любое правило, которое сравнивает файлы, считает время или бюджет, проверяет ссылки между сущностями либо обнаруживает цикл зависимостей, является явным Python hard check. Вероятностная AI-review остаётся работой модели и не маскируется под hard check.

## Внутренний интерфейс

Целевой внутренний CLI ограничен тремя действиями или их эквивалентными entry points:

- `init` — создать bundle поездки;
- `check` — выполнить schema validation и hard checks;
- `render` — построить общий self-contained HTML.

Команды не являются стабильным публичным интерфейсом. Модель может использовать внутренние функции напрямую, когда это проще и безопаснее.

## Статус и блокеры

View model переносит без переосмысления три поля продуктового контракта:

- `document_status`: `draft` или `final`;
- `verification_level`: `none`, `ai_reviewed` или `codex_validated`;
- `finalization_basis`: `codex_validated` или `user_confirmed` для `final`.

Hard check может открыть или подтвердить блокер, но не решает его автоматически. `verification_level: codex_validated` сохраняет фактический результат checks, а `finalization_basis: codex_validated` требует отсутствия блокирующих ошибок финализации. Ручная финализация требует явного принятия каждого остающегося блокера. Renderer сохраняет блокер видимым в HTML и при печати и показывает одну из меток: `Final — проверено в Codex` или `Final — подтверждено пользователем`.

## Поверхности и рендеринг

Все поверхности используют один HTML-шаблон и одну информационную модель. Codex добавляет schema/hard checks и QA. ChatGPT Chat/Work и mobile могут выполнять только явно маркированную вероятностную AI-review и не выпускают `codex_validated` без фактического запуска Codex checks.

Self-contained означает, что скачанный HTML открывается локально без обязательных сетевых assets. Это свойство артефакта, а не offline workflow. Специальных offline-статусов, UI, challenge или evals нет.

Print CSS сохраняет критический контент, lifecycle labels, блокеры, источники и читаемую пагинацию. Если пользователю нужен PDF, он вручную выбирает browser Print → Save as PDF; отдельного adapter, data pipeline или продуктовой гарантии PDF нет.

## Целевая упаковка и QA

- Один plugin и один manifest.
- `pyproject.toml` только для внутренних/local helpers.
- Node, `package.json`, axe и browser-driver dependencies отсутствуют.
- Основные автоматические проверки: Python unit/integration tests, один deterministic Japan HTML reference/hash и минимальная contract validation каталогов.
- Каталог targeted skill scenarios содержит восемь data-only inputs для независимого model review; он не содержит authored answers, runner, judge или offline simulator и не доказывает поведение модели.
- Каталог release scenarios содержит ровно три unexecuted evidence targets; browser/device observations не автоматизируются.
- Перед релизом вручную выполняются ровно два surface smoke checks: Chat web и mobile.
- Статические HTML/CSS tests честно проверяют source contracts, но не называются browser layout, accessibility-engine или visual evidence.
- Допустим один технический test отсутствия обязательной сетевой зависимости HTML.

`reference_evaluator.py`, adapters, judges, rubrics/graders, fixture worlds, scenario-directory matrix, сохранённые eval traces и тесты удалённых модулей не входят в целевую архитектуру.

## Связь с HTML spec

[Interactive Itinerary HTML spec](docs/superpowers/specs/2026-08-28-interactive-itinerary-html-design.md) остаётся источником UX, responsive, accessibility, progressive enhancement, browser print и visual requirements. PR 4 согласует с продуктовым контрактом `user_confirmed` Final, отсутствие отдельного offline workflow и отсутствие встроенного PDF pipeline.

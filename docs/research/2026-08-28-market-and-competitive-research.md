# Исследование рынка и конкурентов Travel Planner Skill

**Дата проверки:** 28 августа 2026 года  
**Объект:** универсальный устанавливаемый open-source Codex skill/plugin для последовательного планирования путешествий  
**Сопоставляемая спецификация:** [`2026-08-28-travel-planner-skill-design.md`](../superpowers/specs/2026-08-28-travel-planner-skill-design.md)  
**Статус документа:** доказательный отчёт для обсуждения; design spec не изменялся  

## Executive summary

Рынок уже содержит несколько реальных устанавливаемых travel skills, поэтому позиционировать проект как «первый AI travel planner» или даже как «первый travel-planning skill» нельзя. Наиболее близкие открытые аналоги — [`jhins-trip-planner`](https://github.com/jhinzzz/jhins-travel-guide-skills), [`trip-planner-skill`](https://github.com/skywain/trip-planner-skill) и [`travel-agent`](https://github.com/apljacob/travel-agent). Они доказывают спрос на агентный workflow, проверяемые данные, мобильный HTML/PDF, карты и booking checklist. Однако ни один изученный аналог не объединяет в публично проверяемой реализации все ключевые свойства нашей архитектуры: переносимое файловое состояние поездки, claim-level provenance и freshness, журнал причин решений, отдельный feasibility challenge до детализации, явную заморозку маршрута, impact analysis и частичную пересборку.

Самый сильный прямой конкурент — `jhins-trip-planner` v0.21.0. У него зрелее, чем в нашей текущей спецификации, проработаны intake для детей, лекарств и accessibility, visa/transit-visa, target-date verification ресторанов и достопримечательностей, last admission, emergency block, бюджетные скрытые расходы и деградация при недоступных источниках. Он также имеет структурированный `trip` object и детерминированный validator. Но его 39 test prompts фактически не запускаются через модель — это прямо указано в `FUTURE.md`; отсутствуют журнал решений, state transitions `draft → challenged → selected → frozen`, отдельный реестр альтернатив до выбора и доказанная частичная пересборка.

`skywain/trip-planner-skill` наиболее силён в маршрутизации и выходных артефактах: route skeletons, open-jaw, часовые таймлайны, геокодирование, проверка дистанций, Google Maps links, KML, восемь HTML-тем и визуальный QC. У него есть единый редактируемый JSON и локальный replan затронутого дня. Это важный сигнал: просто Markdown/HTML/PDF уже недостаточно для заметного отличия. Наша версия должна выигрывать не «красивым путеводителем», а качеством решений, проверяемостью и безопасным изменением сложного маршрута.

Потребительские SaaS сильнее open-source skills в совместной работе и эксплуатации поездки. [Wanderlog](https://wanderlog.com/) объединяет itinerary, reservations, карты, route optimization, offline access, collaboration, budget и packing; [Mindtrip](https://mindtrip.ai/) — conversational discovery, импорт контента/подтверждений, совместный чат, карты, reviews и booking links; [TripIt](https://www.tripit.com/web) — импорт подтверждений и оперативные flight alerts; [Roadtrippers](https://support.roadtrippers.com/hc/en-us/articles/360000831566-What-features-are-included-with-Roadtrippers-memberships) — road-trip routing, vehicle/RV constraints и collaboration. Профессиональные продукты вроде [Travefy](https://travefy.com/), [Tourwriter](https://www.tourwriter.com/product/) и [TravelJoy](https://help.traveljoy.com/hc/en-us/articles/4407244320532-Create-an-Itinerary-or-Smart-proposal) задают другой benchmark: proposal → client decision → booking → final itinerary, формы, статусы, задачи, документы, mobile/offline и единый клиентский source of truth.

Профессиональные и государственные источники сходятся в повторяющейся дисциплине: сначала выяснить мотивацию, состав группы, идеальный день, ограничения, pace и реальную область бюджета; затем построить географически связный каркас вокруг фиксированных событий и транспорта; только после этого подбирать детали. План должен учитывать реальные door-to-door transfers, первый и последний день, luggage, last admission, сезонность, праздники, booking windows, weather/energy backups и recheck перед выездом. Официальные чек-листы добавляют то, что сейчас недостаточно представлено в нашей state model: гражданство/транзит для entry rules, страховку, лекарства и их легальность, документы детей, права/IDP, резервный доступ к деньгам и данным, emergency contacts и копии документов.

Главная рекомендация для 0.1.0 — не расширять продукт до SaaS, booking engine или live travel companion. Вместо этого следует укрепить его ядро шестью обязательными изменениями: (1) first-class readiness/actions state; (2) анонимные traveler profiles для разных ограничений участников; (3) timezone-aware logistics и target-date/last-admission checks; (4) booking/recheck dependency model; (5) честная модель бюджета `estimated/quoted/committed/paid` с FX и буфером; (6) adversarial evals на источник-конфликт, prompt injection, отсутствие интернета и неизменность незатронутого состояния.

Уверенность в выводах высокая для официальной документации OpenAI, содержимого клонированных репозиториев, государственных рекомендаций и научных работ; средняя для публично заявленных возможностей SaaS; низкая для маркетинговых чисел, сравнений качества рекомендаций и функций, доступных только после регистрации.

## 1. Методика и границы исследования

Проверка проводилась 28 августа 2026 года. Использованы:

- прямое чтение официальной документации OpenAI по skills и plugins;
- веб-поиск на русском, английском и по репозиториям с travel/itinerary/agent/skill терминами;
- открытие ключевых первичных страниц, а не только поисковых snippets;
- локальное shallow-клонирование шести наиболее релевантных репозиториев для проверки реального `SKILL.md`, references, scripts, tests, manifest, LICENSE и последнего commit;
- GitHub metadata snapshot для активности, лицензии и состояния репозитория;
- первичные страницы SaaS/help centers вместо сравнительных SEO-обзоров;
- государственные travel checklists, CDC Yellow Book, официальные туристические и транспортные страницы;
- профессиональные источники travel advisors, tour operators и редакторов путеводителей;
- peer-reviewed/primary research по travel-planning benchmarks и constraint satisfaction.

Шкала уверенности:

- **Высокая:** официальный нормативный документ, код/manifest/test в репозитории, государственная или научная первичная публикация.
- **Средняя:** документация продукта или профессиональная методика, подтверждающая процесс, но не качество результата.
- **Низкая:** marketing claim, число пользователей/поездок, обещание «real-time» без доступной методики или закрытая функция, которую нельзя проверить без аккаунта.

Количество stars используется только как моментальный сигнал видимости, а не как оценка качества. Даты GitHub относятся к состоянию на момент проверки и быстро устаревают.

## 2. Нормативная база OpenAI

[Официальная документация OpenAI по skills](https://learn.chatgpt.com/docs/build-skills) определяет skill как каталог с обязательным `SKILL.md`, содержащим `name` и `description`, и опциональными `scripts/`, `references/`, `assets/` и `agents/openai.yaml`. Хост сначала видит имя и описание, а полный `SKILL.md` загружает после выбора skill; поэтому короткий dispatcher и progressive disclosure — не просто удобство, а соответствие модели платформы. Описание должно явно задавать область срабатывания и границы.

Та же документация прямо разделяет роли: skill описывает reusable workflow, а plugin служит способом распространения reusable skills и connectors. Standalone skills подходят для локальной разработки и repo/user scope; для публичной установки OpenAI рекомендует plugin distribution.

[Официальная документация OpenAI по plugin packaging](https://developers.openai.com/plugins/build/plugins) требует `.codex-plugin/plugin.json` как entry point. `skills/`, `hooks/`, `.mcp.json`, `.app.json` и `assets/` находятся в корне plugin, а в `.codex-plugin/` должен лежать только `plugin.json`. Manifest идентифицирует plugin, указывает bundled components и даёт install-surface metadata. Skills, MCP, UI и hooks являются независимыми опциональными компонентами.

Вывод для проекта:

- предложенная архитектура `skills/travel-planner/SKILL.md + references + schemas + scripts + assets` соответствует официальной модели;
- минимальный plugin с одним skill и без MCP/hooks/UI допустим;
- короткий `SKILL.md`-router — конкурентное и платформенное преимущество по сравнению с монолитными файлами на 500–950 строк;
- перед релизом нужно проверить актуальную manifest schema и локальную установку, а не копировать legacy пути `.codex/skills` из сторонних репозиториев;
- `agents/openai.yaml` необязателен, но его стоит рассмотреть для install-facing metadata и зависимостей;
- публичная совместимость должна подтверждаться реальной установкой в Codex, а не только наличием слова «Codex» в README.

## 3. Карта рынка

### 3.1. Прямые устанавливаемые skills/workflows

Это наиболее близкий класс: инструкции в `SKILL.md` или Claude plugin, которые хост-агент выполняет в текущей рабочей среде.

- **Полные planning skills:** `jhins-trip-planner`, `skywain/trip-planner-skill`, `apljacob/travel-agent`, AI Labs `travel-planner`.
- **Output-first skills:** `happy-trip-site`, `skills-travel-planner`; они преимущественно превращают уже существующий brief/itinerary в сайт или roadbook.
- **Prompt/template substitutes:** Claude Academy daily itinerary prompt, PromptBase, GitHub gists и prompt libraries. Они дешевле в создании, но обычно не имеют state, migrations, deterministic QA и update semantics.

### 3.2. Open-source приложения и agent systems

- [`MyTripPlanner`](https://github.com/Prot10/MyTripPlanner) — self-hosted PWA с Claude/Codex agent, картой, реальным routing, hotels/restaurants и budget; на 28.08.2026 активен, README заявляет AGPL-3.0.
- [`TripBreeze AI`](https://github.com/sarakshnbzg/tripbreeze-ai) — LangGraph/FastAPI/Next.js planner с intake, research, budget, weather и human-in-the-loop; репозиторий без явной лицензии, последняя проверенная активность в апреле 2026 года.
- Многие GitHub «AI Travel Planner» проекты являются single-prompt demos: форма → один LLM call → JSON itinerary. Пример — [`ai-itinerary-generator`](https://github.com/AliBavarchee/ai-itinerary-generator), где prompt просит список дней и активностей, но не доказывает выполнимость или актуальность.

Эти проекты конкурируют за end result, но не за тот же distribution model: они требуют приложения, сервера, UI или ключей, тогда как наш проект намеренно остаётся installable skill без backend.

### 3.3. AI travel-planner SaaS

- [Mindtrip](https://mindtrip.ai/) — discovery, personalized recommendations, itinerary, group collaboration/chat, content and booking import, maps/reviews, booking links.
- [Trip Planner AI / Layla](https://tripplanner.ai/) — instant itinerary, flights/hotels/activities, editing and claimed recalculation of times/costs; страница смешивает бренды Trip Planner AI и Layla, поэтому детальные claims требуют осторожности.
- [Wonderplan](https://wonderplan.ai/v2/trip-planner) — короткий structured intake, generated itinerary, manual reorder, accommodation suggestions и PDF/offline.
- Другие chat-based planners образуют насыщенный, но непрозрачный слой: маркетинговые страницы редко раскрывают source provenance, constraint tests или правила обновления.

### 3.4. Традиционные consumer planners

- [Wanderlog](https://wanderlog.com/) — strongest all-in-one benchmark для trip workspace: reservations, daily schedule, route/map, collaboration, packing, budget, offline, AI assistant.
- [TripIt](https://www.tripit.com/web) — organizer после бронирования: email import, единый itinerary, sharing, calendar, maps; Pro добавляет live flight alerts, alternate flights и airport operations.
- [Roadtrippers](https://support.roadtrippers.com/hc/en-us/articles/360000831566-What-features-are-included-with-Roadtrippers-memberships) — специализированный road-trip planner с route avoidance, RV constraints, fuel/route context, Autopilot AI и group collaboration.
- Google Maps/My Maps, spreadsheets, Notion и calendar остаются «компонуемыми конкурентами»: пользователь вручную собирает из них карту, таблицу, checklist и документы.

### 3.5. Профессиональные advisor/tour-operator tools

- [Travefy](https://travefy.com/) — proposal, side-by-side client decision, itinerary, CRM/forms/tasks, branded PDF/mobile/offline, content library и supplier integrations.
- [Tourwriter](https://www.tourwriter.com/product/) — `Design → Quote → Share → Book → Manage`, supplier/pricing/payment workflow и itinerary map.
- [TravelJoy](https://help.traveljoy.com/hc/en-us/articles/4407244320532-Create-an-Itinerary-or-Smart-proposal) — proposal vs final itinerary, client-facing app, offline copy, library/import tools.
- [AXUS](https://support.axustravelapp.com/hc/en-us/categories/39221768129563-Collaboration) — collaboration между advisor, tour operator и DMC, включая locks и co-branding.

Их сильная сторона — не discovery и research как таковые, а управляемый переход от вариантов к одобрению, оплате, подтверждениям и обслуживанию. Для 0.1.0 это источник workflow-паттернов, а не продуктовый scope.

## 4. Сравнение наиболее релевантных решений

| Решение | Класс и установка | Глубина workflow и evidence | Состояние и изменения | Выходы/QA | Состояние проекта на 28.08.2026 |
|---|---|---|---|---|---|
| [`jhins-trip-planner`](https://github.com/jhinzzz/jhins-travel-guide-skills/blob/main/skills/jhins-trip-planner/SKILL.md) | Claude plugin + standalone `SKILL.md`; Codex через skill installer/manual | Очень глубокий intake, evidence tiers, target-date verification, visa/transit visa, accessibility, health, safety, booking lead times, backups | Embedded structured `trip`; follow-up edits parse existing data; нет journal/freeze/impact graph | Markdown/HTML; zero-dependency validator; 39 structured test prompts, но model harness отсутствует | v0.21.0, MIT, last commit 27.07.2026, 1 star; active, Claude-first; OpenAI plugin manifest отсутствует |
| [`trip-planner-skill`](https://github.com/skywain/trip-planner-skill/blob/main/SKILL.md) | Raw multi-host skill | Очень глубокий route/logistics workflow, live sources, search budgets, open-jaw, hour schedule, holidays, replan | `plan.geo.json` — editable source; local affected-day replan; нет formal decision history/freeze | Self-contained themed HTML, KML, route tools, QC, visual probes | MIT, active through 27.08.2026, 21 stars; крупный пакет (~44 MB), `SKILL.md` 575 строк, почти нет unit/eval suite |
| [`travel-agent`](https://github.com/apljacob/travel-agent/blob/main/skills/travel-agent/SKILL.md) | Claude Code plugin | Чёткие 7 фаз, emotional discovery, live web, 3 options, anchor+backup, reservations, packing | Session-only; нет machine state, resume, migrations или partial rebuild | PDF по внешнему document skill; acceptance queries вручную | v0.1.0, CC BY-NC 4.0, единственный commit 05.05.2026, 6 stars; source-available, не open-source для коммерческого reuse |
| [AI Labs `travel-planner`](https://github.com/ailabs-393/ai-labs-claude-skills/blob/main/packages/skills/travel-planner/SKILL.md) | Skill внутри большой Claude collection/npm tooling | Broad checklist и web-research instruction; примеры часто выглядят как факты без встроенной provenance discipline | JSON profile/trips/expenses в `~/.claude/travel_planner`; глобальное, не portable trip folder | JSON/чат; scripts для budget/packing; тестов skill не найдено | MIT; collection 443 stars, но последняя кодовая активность 11.11.2025; качество конкретного skill не следует из stars collection |
| [`happy-trip-site`](https://github.com/OWENLEEzy/happy-trip-site/blob/main/skill/happy-trip-site/SKILL.md) | Agent skill, ручное копирование | Brief extraction и media verification, но не полноценное trip research/route design | Structured frontend data; ориентирован на готовый itinerary | Сильный mobile-first HTML, unit tests, data verifier, browser tap-target check | Last commit 17.06.2026, 0 stars, license не найден — reuse юридически неопределён |
| [`skills-travel-planner`](https://github.com/huanyuzhilv/skills-travel-planner) | Заявлен как Cursor/Claude/Codex skill + scripts | Intake/enrichment/roadbook, сильная China/Xiaohongshu/FlyAI специализация; нужны внешние keys для полного режима | `tripData.json`; pipeline output-oriented | HTML/PDF roadbook, image pipeline | MIT, last commit 01.06.2026, 13 stars; файл называется `skill.md`, installer использует legacy `.codex/skills`, поэтому текущая Codex discovery по OpenAI docs не подтверждена |
| [`MyTripPlanner`](https://github.com/Prot10/MyTripPlanner) | Self-hosted desktop/PWA app | Agent интервьюирует и вызывает purpose-built tools; real routing/geocoding/hotel search заявлены и частично видны в кодовой архитектуре | Собственная data model и UI edits | Interactive map/app, import/export | Активен 27.08.2026, 8 stars, README: AGPL-3.0; намного тяжелее skill и road-trip biased |
| [`TripBreeze AI`](https://github.com/sarakshnbzg/tripbreeze-ai) | Web app, LangGraph/FastAPI/Next.js | Multi-step research, RAG, weather, budget, HITL | Backend/application state | Web UI; golden-prompt tests заявлены, breadth ограничен | Last push 29.04.2026, 1 star, явная license отсутствует |
| [Wanderlog](https://wanderlog.com/) | Closed SaaS/mobile | Inspiration, AI, itinerary, reservations, maps, collaboration | Rich collaborative workspace; provenance/decision rationale непрозрачны | Mobile/offline, budgets, packing, map/export | Зрелый продукт; claims подтверждаются help center, качество AI не проверено |
| [Mindtrip](https://resources.mindtrip.ai/travelers/help/traveler-faqs) | Closed AI SaaS | Conversational discovery, multi-source recommendations, imports, events, booking | Collaborative trip + collections/receipts | Web/iOS, group chat, maps/reviews/book links | Активный продукт; source-level grounding и constraint QA закрыты |
| [Travefy](https://travefy.com/go-professional) | B2B SaaS | Advisor builds proposal/itinerary; сильнее в approval/business workflow, чем в research | CRM/forms/tasks/proposal states/library | Branded links, PDF, mobile/offline | Зрелый платный benchmark; не open source, не автономный research agent |

### 4.1. Что не следует считать прямым аналогом

- PromptBase/gists/«50 prompts for travel» — это шаблоны запроса без install lifecycle, state, schemas, scripts и tests.
- `happy-trip-site` и roadbook generators — конкуренты выходных документов, но не всего planning workflow.
- TripIt — organizer подтверждённых бронирований, а не discovery/synthesis engine.
- Tourwriter/Travefy — профессиональные системы исполнения и продаж, не устанавливаемые AI skills.
- Научные planners — важная база для eval design, но не готовый пользовательский продукт.

## 5. Детальный аудит прямых аналогов

### 5.1. `jhins-trip-planner`: ближайший методический конкурент

Сильные стороны, подтверждённые содержимым репозитория:

- progressive router и отдельные references по intake, sources, transport, hotels, dining, attractions, budget, safety и prep;
- hard constraint: каждый fare/schedule/rating/availability должен иметь source и research date;
- target-date verification вместо «обычно открыт по вторникам»;
- отдельные правила last admission, capacity/timed entry, festival/Ramadan overlap, children, medication, accessibility и self-drive;
- source-channel ladder и честная деградация в advisory card при login wall или слабых данных;
- structured [`trip-data.schema.md`](https://github.com/jhinzzz/jhins-travel-guide-skills/blob/main/skills/jhins-trip-planner/assets/trip-data.schema.md) и [`validate.js`](https://github.com/jhinzzz/jhins-travel-guide-skills/blob/main/skills/jhins-trip-planner/assets/validate.js);
- 39 разнообразных test prompts с rule provenance.

Ограничения:

- [`FUTURE.md`](https://github.com/jhinzzz/jhins-travel-guide-skills/blob/main/FUTURE.md) прямо говорит, что test prompts не запускаются через модель и assertions не оценивают outputs автоматически;
- один крупный finished `trip` object смешивает brief, evidence, budget, safety, outputs и оперативные данные; нет явной ownership-модели стадий;
- нет устойчивого decision log, selected/frozen transition, preview migration и доказанного impact graph;
- workflow в основном ведёт к одному guide, а не сохраняет исследовательский longlist и альтернативные route skeletons как самостоятельный audit trail;
- Codex поддержан как standalone skill, но repo является Claude plugin, не OpenAI plugin.

Практический вывод: проект должен заимствовать предметные blind spots и validator philosophy, но выигрывать lifecycle/state architecture и реальными behavioral evals.

### 5.2. `skywain/trip-planner-skill`: ближайший конкурент по логистике и deliverable

Сильные стороны:

- route skeleton before detail, minimum two-night bases, open-jaw consideration;
- отдельные flight scan, geocoding, route distance checks, links, KML и sunrise/sunset tools;
- hour-by-hour scheduling с buffers, luggage и late-cut/degradation tags;
- единый `plan.geo.json` как редактируемый источник;
- «live replan» затронутого дня без полной переработки;
- детальная failure/degradation policy и search budgets;
- сильные mobile HTML и визуальный QC.

Ограничения:

- огромная площадь продукта и assets повышают стоимость установки, review и сопровождения;
- renderer/themes занимают существенную долю сложности и могут отвлекать от planning correctness;
- automated tests/evals почти отсутствуют: найден статический `qc.py` и локальные assertions в renderers, но не систематическая проверка планирования;
- one-file state не отделяет facts, candidates, decisions и derived outputs;
- отсутствует formal freeze/confirmation protocol и proof, что незатронутые данные не изменились;
- основной `SKILL.md` чрезмерно длинный для progressive disclosure.

Практический вывод: часовая логистика, time zones/daylight и KML — сильные идеи; восемь тем и генерация art/video не нужны в 0.1.0.

### 5.3. `travel-agent`: сильная профессиональная рамка, слабая инженерная основа

Skill задаёт хороший seven-phase narrative: emotional discovery, destination shaping, logistics, day plan, booking tracker, packing/prep, PDF. Он чётко формулирует «three positioned options», «one anchor + backup», jet-lag arrival day и pushback на перегруженные маршруты.

Но это в основном instruction-only workflow: нет persistent state, schemas, scripts, source registry, claim freshness, migrations, partial rebuild или executable tests. PDF зависит от другого document skill. Лицензия CC BY-NC 4.0 не позволяет считать проект permissive open source и ограничивает коммерческое переиспользование.

Практический вывод: эмоциональный вопрос «что вдохновило поездку / как вы хотите себя чувствовать» и идеальный день стоит добавить в intake; архитектуру копировать не следует.

### 5.4. Output-first competitors

`happy-trip-site` задаёт высокий стандарт QA для мобильного HTML: readiness gate, content-verified imagery, 44px tap targets, реальный browser-backed check и явные completion states. Однако он не исследует маршрут с нуля и не проверяет всю транспортную выполнимость. Его отсутствие LICENSE — существенный reuse risk.

`skills-travel-planner` имеет богатый roadbook pipeline и tripData, но специализируется на китайском travel-advisor контексте, внешних image/hotel providers и визуальном обогащении. На момент проверки он не соответствует текущему OpenAI skill entry-point requirement из-за `skill.md` в нижнем регистре, а installer ориентирован на legacy `.codex/skills`. Это пример того, почему «заявлена совместимость» и «протестирована установка» должны быть разными полями в нашей release evidence.

### 5.5. Prompt-based substitutes

[Claude Academy](https://academy.claude.com/use-cases/create-a-daily-travel-itinerary) рекомендует пользователю указать destination, duration, interests, pace, group, budget и запросить current web research, realistic timing, navigation и alternatives. Это хороший minimum prompt, но он не даёт переносимость решений между чатами.

[PromptBase Travel Planner Pro](https://promptbase.com/prompt/travel-planner-pro-2) и публичные GitHub gists обещают itinerary, flights, hotels, budget, packing и hidden gems из 7–10 полей. Их конкурентное преимущество — нулевая установка; недостаток — отсутствие доказанного sourcing, schema evolution, failure recovery и regression tests. Для нашего проекта они являются baseline: skill должен заметно превосходить качественно написанный одноразовый prompt.

## 6. Смежные продукты: чему у них стоит учиться

### 6.1. AI SaaS

Mindtrip показывает ценность multimodal intake: начать можно с текста, ссылки, social content, screenshot или PDF; затем исходные идеи превращаются в collection или trip. Его collaboration model — shared ideas, comments, likes и group chat — решает реальную проблему согласования группы. Но публичная документация не показывает claim-level sources или сохранённые причины AI swaps.

Trip Planner AI/Layla и Wonderplan оптимизируют time-to-first-plan. Это давление на наш collaborative mode: пользователь должен быстро увидеть полезную гипотезу, даже если полный workflow займёт дольше. Спецификация уже содержит fast draft, что правильно. Нельзя, однако, повторять неподтверждённые marketing claims вроде «one-click edit всегда пересчитывает все времена и costs» без regression evidence.

### 6.2. Consumer planners

Wanderlog задаёт ожидание, что itinerary — это не финальный PDF, а рабочее пространство с картой, бронированиями, расходами, packing и collaboration. Наш skill не должен копировать UI, но должен экспортировать данные так, чтобы их можно было перенести в карты/calendar и использовать offline.

TripIt показывает ценность разделения «планирование» и «оперативное подтверждение»: imported bookings, confirmation details, flight alerts, terminal/gate и leave-for-airport reminders. В 0.1.0 не нужны live alerts, но first-class booking status и recheck tasks нужны.

Roadtrippers показывает, что road trip требует отдельного challenge profile: ограничения vehicle/RV, toll/ferry/highway avoidance, fuel, daily driving ceiling, seasonal roads и safe route. Один общий `transport` object без mode-specific checks будет слишком слабым.

### 6.3. Профессиональные tools

Travefy/Tourwriter/TravelJoy различают proposal и final itinerary. Это соответствует нашим `draft/selected/frozen`, но профессиональные продукты добавляют:

- side-by-side client selection/approval;
- assignment и deadlines;
- booking/quote/confirmed/paid/cancelled states;
- reusable supplier/content library;
- документы и confirmations;
- mobile/offline client source of truth;
- controlled collaboration и locks.

Для 0.1.0 стоит взять state semantics и action ownership, но не CRM, payment, supplier inventory или client portal.

## 7. Профессиональные принципы планирования

### 7.1. Discovery: сначала мотив и реальный стиль поездки

Профессиональные источники сходятся в следующих вопросах:

1. Что вдохновило поездку и каким должен быть её результат/ощущение?
2. Кто едет, кто принимает решение и где интересы участников расходятся?
3. Как выглядит идеальный день: время выхода/возвращения, активность, еда, самостоятельность?
4. Что понравилось и не понравилось в прошлых поездках?
5. Какие 1–3 вещи non-negotiable, а чем можно пожертвовать?
6. Какова область бюджета: на человека/группу, включает ли flights, insurance, shopping?
7. Насколько гибки даты и какой риск пользователь готов принять?
8. Есть ли mobility, medical, dietary, sensory, child или luggage constraints?

[Riveting Trips](https://rivetingtrips.com/how-to-conduct-travel-advisor-discovery-call/) начинает с «What inspired this trip?», состава группы, travel style, budget и unforgettable outcome. [Профессиональные discovery scripts](https://www.independenttravelconsultants.co.uk/top-questions-to-ask-clients-before-building-their-trip) подчёркивают purpose, ideal day, прошлый опыт, приоритеты, mobility и realistic budget range. Это подтверждает наш intake, но выявляет пробелы: decision-maker/group conflicts, past-trip dislikes и desired feeling должны быть явными полями, а не свободным текстом.

### 7.2. Route before detail

[Rick Steves](https://www.ricksteves.com/travel-tips/trip-planning/itinerary-tips) рекомендует сначала wish list, затем логический географический порядок, fixed-date events, open-jaw airports, transport modes и rough nights allocation. Он отдельно предупреждает о чрезмерных one-night stays и необходимости считать два ночлега для одного полного дня.

[Lonely Planet](https://www.lonelyplanet.com/articles/how-to-plan-a-trip) советует сокращать destinations или использовать day trips из одной базы, проверять первый и последний день, не ставить лучшие активности на arrival day и не доверять летнему drive-time для зимнего маршрута. [JNTO](https://www.japan.travel/en/gc/tips/) также рекомендует для поездок до недели одну базу и day trips, а для 10–14 дней — несколько регионов без постоянной гонки.

Это подтверждает выбранную архитектуру «2–3 skeletons → challenge → selection», а также необходимость явных night/base metrics.

### 7.3. Feasibility — это door-to-door, а не линия на карте

Повторяющиеся проверки:

- local time, time zone и date rollover;
- airport/station/hotel door-to-door, security/check-in, border, transfer и luggage buffers;
- last departure и missed-connection fallback;
- check-in/check-out и luggage storage;
- operating date, holiday rule, last admission и seasonal closure;
- accessibility не только venue, но и путь/пересадка/туалет/подъём;
- daylight, heat, rain, snow, typhoon/wildfire/air-quality windows;
- daily walking/vertical gain/drive-time и накопленная усталость;
- reservation capacity и release window;
- базовый и локальный backup, не требующий смены hotel/base.

[JNTO по Shinkansen](https://www.japan.travel/en/plan/getting-around/shinkansen/) показывает важную деталь: oversized baggage на ряде линий требует заранее зарезервированного места. [JNTO FAQ](https://www.japan.travel/en/faq/) рекомендует advance reservation в holiday periods. Эти примеры подтверждают, что luggage и capacity должны быть структурными ограничениями, а не prose notes.

### 7.4. Booking strategy и recheck

[Lonely Planet booking timeline](https://www.lonelyplanet.com/articles/guide-to-trip-planning) отмечает асимметрию горизонтов: популярные поездки бронируются за 9–12 месяцев, а train/ferry schedules часто появляются только за 3–6 месяцев. Следовательно, отсутствие точного расписания за год до поездки — не failure, а ожидаемое состояние `not_released_yet` с датой следующей проверки.

Хороший action item содержит не только «забронировать», но и:

- release/open date и timezone;
- due date и owner;
- official channel;
- refundable/cancellation terms;
- dependency на выбранный день/отель/transport leg;
- status `not_available_yet / ready / selected / booked / confirmed / recheck / cancelled`;
- evidence date и next check;
- безопасную ссылку, но не personal confirmation code в публичном файле.

### 7.5. Backups и принятый риск

Профессиональный backup заменяет anchor при конкретном trigger (`rain`, `sold_out`, `low_energy`, `closure`, `missed train`) и сохраняет географию дня. Он должен иметь собственную target-date verification. Если пользователь сознательно сохраняет warning, это не должно исчезать: требуется risk acceptance/waiver в decisions log с датой и affected scope.

## 8. Сравнение популярных чек-листов

Официальные checklists Великобритании, США, Канады, Австралии и CDC сильно перекрываются. Ни один не является исчерпывающим; вместе они дают устойчивое ядро.

| Область | Повторяющиеся пункты | Пробел в текущей спецификации |
|---|---|---|
| Destination research | entry/exit, advisories, local laws, health, climate/natural disasters, emergency services | Есть sources/freshness, но нет отдельного readiness gate и official-source policy для high-stakes claims |
| Документы | passport validity, visa/eTA, transit rules, dual citizenship, children consent, driving permit | Brief не моделирует nationality/transit/child documents; правильно не хранить номера passport, но страна документа нужна |
| Health | consultation за 4–6 недель, vaccines, chronic conditions, medication legality, prescriptions, destination care | Есть mobility/physical limits и общий риск, но нет structured health action flow |
| Insurance | coverage destination/activity/duration, medical evacuation, exclusions, pre-existing conditions, emergency line | Insurance отсутствует как first-class state/action |
| Деньги | realistic budget, emergency buffer, backup card/funds, cash/card norms, 2FA failure | Budget есть, но нет payment redundancy и status/FX semantics |
| Связь и данные | eSIM/roaming, offline maps, hard-copy contacts, copies of bookings, family contact | Outputs частично покрывают; нет offline/emergency pack и backup access test |
| Safety | advisories, local risks/laws, embassy/consulate, registration/alerts, emergency plan | Challenge включает risks, но итоговый emergency block не определён как обязательный trigger-based output |
| Багаж | permitted items, medicines in carry-on, weather/activity kit, luggage constraints | Packing artifact заявлен косвенно слабо; luggage учитывается в transport, но не сквозным checklist |
| Перед выездом | recheck advice, flight/transport, weather, closures, confirmations, insurance docs | Freshness model есть, но нет единого T-30/T-7/T-1 readiness view |
| Во время поездки | daily weather/disruption check, next-day confirmations, safe funds/docs, contacts, expense/plan updates | Live behavior почти вне scope; достаточно lightweight daily card, не полноценного live service |

Ключевые источники:

- [GOV.UK Foreign travel checklist](https://www.gov.uk/guidance/foreign-travel-checklist), обновлён 05.06.2026: destination advice, insurance, passport/visa/children/IDP, health, backup access to data and money, embassy.
- [U.S. State Department International Traveler’s Checklist](https://travel.state.gov/content/travel/en/international-travel/before-you-go/travelers-checklist.htmlhecklist.html): destination/entry/advisory, STEP, passport copies, medical/evacuation insurance.
- [Canada Traveller’s Checklist](https://travel.gc.ca/travelling/publications/travellers-checklist): passport/visa/children/dual citizenship, clinic за 6 недель, insurance, emergency funds, itinerary copies.
- [Australian Smartraveller essentials](https://www.smartraveller.gov.au/th/node/158), обновлён 18.08.2026: destination laws, documents/insurance, hard copies of bookings и emergency contacts.
- [CDC Before You Travel](https://wwwnc.cdc.gov/travel/page/before-travel): health consultation за 4–6 недель, trip/activity-aware assessment, medicines plus delay buffer, insurance и emergency preparation.
- [CDC Pack Smart](https://wwwnc.cdc.gov/travel/page/pack-smart): print+digital documents, prescriptions, immunization, insurance, destination clinic и embassy information.
- [CDC Yellow Book: pre-travel consultation](https://www.cdc.gov/yellow-book/hcp/preparing-international-travelers/the-pre-travel-consultation.html): traveler-specific risk assessment, risk communication и risk management вместо generic advice.

## 9. Gap-анализ нашей архитектуры

### 9.1. Где спецификация опережает рынок

1. **Разделение epistemic layers.** Facts, popularity, contextual scores и verdict не смешиваются. У конкурентов такие границы обычно prose-only или отсутствуют.
2. **Claim status + freshness class.** `verified/corroborated/reported/unverified/conflicting` и `static…realtime` сильнее типичного «source + date».
3. **Route alternatives как сохраняемая стадия.** Большинство решений сразу генерирует один itinerary или не хранит rejected alternatives.
4. **Hard constraints как gate.** Это согласуется с research: [TravelPlanner benchmark](https://arxiv.org/abs/2402.01622) показывает, что агенты часто выполняют часть ограничений, но проваливают macro pass; [TourPlanner](https://arxiv.org/abs/2601.04698) также применяет hard-constraint gate до soft optimization.
5. **Frozen state и no silent edits.** Это редкое и важное human-control свойство.
6. **Impact analysis и partial rebuild.** Прямые конкуренты говорят о replan/edit, но не доказывают preservation незатронутых данных.
7. **Derived outputs отделены от source of truth.** Профессионально зрелый design.
8. **Offline CI и live pre-release checks разделены.** Хороший баланс reproducibility/freshness.
9. **No backend/no required API keys.** Ниже барьер и лучше privacy/portability.

### 9.2. Где конкуренты или профессиональная практика сильнее

1. **Traveler profiles недостаточно гранулярны.** Одна характеристика группы не отражает разные mobility, dietary, age, medication и pace needs.
2. **Нет first-class readiness/actions state.** Checklist outputs заявлены, но completion, owner, due/release date, dependency и recheck не являются самостоятельной моделью.
3. **Entry/health/insurance недомоделированы.** Нет citizenship/residency/transit context, medicines legality, child documents, IDP, insurance scope и emergency provider.
4. **Time semantics слишком неявные.** Нужны time zone, overnight rollover, DST, schedule horizon, last admission и check-in/out/luggage-storage constraints.
5. **Budget не различает качество числа.** Оценка, quote, booked и paid — разные сущности; нужны taxes/fees, FX date, group/per-person basis и contingency.
6. **Нет group decision protocol.** Кто принимает решение, как фиксируется конфликт, нужен ли solo time, кто owner booking task.
7. **Не определён compact in-trip mode.** Даже без live alerts полезны daily card, next-day recheck и local backup activation.
8. **Accessibility слишком общая.** Нужны path/transfer/accessibility checks, а не только venue label.
9. **High-stakes source policy не выделена.** Visa, medicine, health, emergency и advisories должны опираться на official sources или явно оставаться unresolved.
10. **Release/install evidence пока только план.** Конкуренты показывают реальные install commands; наш differentiator существует лишь после reproducible smoke test.

### 9.3. Внутренние риски подхода

- **State complexity:** шесть файлов, cross-references и migrations могут превратить skill в мини-приложение.
- **Context pressure:** `candidates.yaml` может разрастись и ухудшить reasoning; нужен scoped loading и summarization.
- **False rigor:** schema-valid plan может оставаться плохим по смыслу; validators не заменяют human/judge rubric.
- **Source explosion:** требование атомарной provenance для каждой детали дорого и может сделать отчёт нечитаемым.
- **Research latency/cost:** пять discovery layers плюс несколько skeletons могут быть избыточны для weekend trip.
- **Long-horizon uncertainty:** точных schedules и prices часто ещё нет; system должен поддерживать `not_released_yet`, а не выглядеть незавершённым.
- **Platform drift:** OpenAI plugin schema и install surfaces меняются; release check обязателен.
- **Security:** внешние страницы и repository instructions могут содержать prompt injection; это должно проверяться не только декларацией.
- **Visual ambition:** PDF/HTML/image licensing способны поглотить 0.1.0, как видно по output-first competitors.

## 10. Преимущества и недостатки нашего позиционирования

### Преимущества

- Локальный, переносимый и inspectable trip workspace вместо закрытого аккаунта.
- Пользователь владеет решениями и может продолжить в новом чате.
- Evidence-aware planning, а не только генерация красивого расписания.
- Несколько route hypotheses до sunk cost в детализацию.
- Feasibility challenge и explicit risk acceptance.
- Controlled updates после freeze и reproducible derived outputs.
- Universal destination/mode core без обязательного provider lock-in.
- Open-source permissive MIT target, в отличие от CC BY-NC или unlicensed alternatives.

### Недостатки

- Нет real-time inventory, collaboration UI, booking import, alerts и mobile app.
- Больше шагов и файлов, чем у instant planners.
- Качество зависит от доступных web/browser tools и источников.
- Пользователь должен понимать статусы и подтверждать decisions.
- Без отличных examples/evals ценность архитектуры не видна.
- Визуальные outputs в 0.1.0, вероятно, будут слабее специализированных roadbook/rendering projects.

### Рекомендуемое позиционирование

Не «AI спланирует идеальное путешествие», а:

> Open-source planning workflow для сложных поездок, который сохраняет решения и источники, проверяет выполнимость до бронирований и безопасно пересобирает только то, что изменилось.

Не обещать «real-time prices», «guaranteed accurate itinerary», «optimal route» или «works in every agent» без соответствующих tests.

## 11. Приоритизированные рекомендации

### Must — включить до 0.1.0

#### M1. Добавить first-class `readiness.yaml`

Хранить actionable items, а не только генерировать checklist:

- `id`, `category`, `title`, `applies_to`;
- `status`: `unknown / not_released / action_needed / selected / booked / confirmed / recheck / waived / not_applicable`;
- `owner` как анонимная роль (`traveler_1`, `group_lead`), не имя;
- `due_at`, `release_at`, `timezone`, `next_check_at`;
- `dependencies`, `official_url`, `source_ids`, `checked_at`;
- `refundability/cancellation_summary`;
- `sensitive_data_location` как ссылка на внешний secure store, без confirmation/passport/card data в repository.

Категории: entry/transit, health/medication, insurance, transport, lodging, activities, dining, connectivity, money, documents, packing, emergency, pre-departure recheck.

Обоснование: это главный повторяющийся gap относительно government checklists и professional tools. Отдельный файл оправдан, потому что completion state не является derived output.

#### M2. Ввести анонимные traveler profiles

В `brief.yaml` добавить `travelers[]` с устойчивыми anonymous IDs и минимально необходимыми flags:

- age band;
- nationality/residency country codes только если нужны entry rules;
- mobility/accessibility;
- dietary/allergy flags;
- medication/legal-check-needed без медицинских диагнозов по умолчанию;
- pace/energy and luggage constraints;
- driver role и license-origin country;
- child/guardian document check trigger.

Добавить group-level `decision_owner`, `conflicts`, `shared_vs_solo_time`. Не хранить паспортные номера, даты рождения, карты и medical records.

#### M3. Усилить timezone-aware logistics challenge

Для leg/activity хранить local timezone и явные timestamps там, где время критично. Challenge должен проверять:

- overnight/date rollover и DST;
- door-to-door transfer, не только duration транспорта;
- min connection, border/security/check-in buffer;
- hotel check-in/out и luggage storage;
- last departure и last admission;
- schedule horizon (`published`, `seasonal_pattern`, `not_released_yet`);
- baggage reservation/capacity;
- arrival/departure day load.

#### M4. Формализовать high-stakes evidence policy

Для entry/visa/transit, medication legality, health, advisories, emergency numbers и transport operations:

- official primary source обязателен для `verified`;
- отсутствие official confirmation остаётся `unverified/conflicting` и создаёт blocking readiness item, если влияет на возможность поездки;
- advice должен быть информационным, без medical/legal guarantees;
- claim хранит `supports/refutes`, locator/section и retrieval result, но не длинную copyrighted quote.

#### M5. Уточнить budget model

Вместо одного estimate использовать:

- `amount_type`: `estimate / observed_price / quote / booked / paid`;
- currency, FX source/date/rate;
- per-person vs group, taxes/fees included;
- refundable/non-refundable;
- committed vs remaining;
- contingency buffer;
- confidence и source/date.

Hard gate: вариант не проходит budget constraint, если обязательные категории пропущены или basis несовместим.

#### M6. Сделать behavioral eval harness реальным release blocker

Не ограничиваться prompt fixtures. Нужны:

- deterministic fixture world для dates/hours/fares;
- executable schema/invariant graders;
- LLM-judge только для качественных рубрик;
- mutation tests для partial rebuild;
- сохраняемые traces и версия model/prompt;
- macro hard-pass: один провал hard constraint проваливает scenario.

[TravelPlanner benchmark](https://arxiv.org/abs/2402.01622) показал, что высокие micro scores маскируют провал полного набора ограничений; это прямо поддерживает macro gate.

### Should — желательно в 0.1.x, часть можно успеть в 0.1.0

#### S1. Двухступенчатый challenge

Запускать `skeleton challenge` до выбора и `detailed challenge` после day/transport/booking enrichment. Хранить finding:

- stable `rule_id`;
- severity, confidence;
- evidence/source IDs;
- affected entities/days;
- proposed patch и expected gain/loss;
- status `open / accepted_fix / accepted_risk / obsolete`;
- user decision reference.

#### S2. Ввести explicit uncertainty horizon

Различать `unknown`, `not_released_yet`, `temporarily_unavailable`, `source_blocked`, `conflicting` и `not_applicable`. Это уменьшит ложные warnings для далёких поездок.

#### S3. Group conflict resolution

До route synthesis фиксировать 1–3 общих приоритета, индивидуальные must-haves, допустимый split-day и правило tie-break. Каркасы должны показывать, чьи потребности выигрывают/проигрывают.

#### S4. Accessibility chain

Проверять не только POI, но и полный путь: hotel room/common areas → station/vehicle → transfers → restroom/rest points → attraction surfaces/elevators → return. Если данных нет — явный readiness task для прямого подтверждения provider.

#### S5. Lightweight in-trip artifacts

Добавить offline-friendly daily card:

- today’s fixed items и hard cutoffs;
- route/map links;
- weather/closure triggers;
- activation steps для backup;
- next-day confirmations;
- emergency/contact short block;
- last sync/recheck timestamp.

Без push notifications, live monitoring и автоматического rebooking.

#### S6. Экспорт portability

Помимо Google Maps links рассмотреть deterministic exports: `.ics` для fixed bookings и GeoJSON/KML для map points/routes. Делать только после стабилизации itinerary schema.

#### S7. Install/release matrix

Автоматически проверять:

- standalone discovery в Codex CLI/desktop/IDE-supported scope;
- local OpenAI plugin install;
- manifest fields и запрещённые лишние файлы;
- clean environment без optional PDF adapter;
- Python 3.11/3.12;
- no-network degraded flow.

### Could — после устойчивого 0.1.0

- Import из существующего Markdown/CSV/PDF itinerary с preservation inventory.
- Import confirmation emails/attachments через отдельный optional connector.
- Preference profile между поездками с explicit consent и отдельным private store.
- Shared group voting/approval export без собственного server.
- Mode-specific packs: rail-heavy, road trip, hiking, cruise, family, accessible.
- Local image library и optional licensed imagery enrichment.
- Destination adapter references для сложных стран без hardcoding ядра.
- Sustainable travel signals: rail-vs-air, overtourism/carrying capacity, local/community impact — только как объяснимые soft dimensions.
- Calendar/Task connectors как optional plugin additions.
- Provider-specific booking deep links с policy against affiliate bias.

### Не включать в 0.1.0

- Собственный web/mobile/desktop UI, server, account и collaboration backend.
- Автоматическую покупку, бронирование, оплату, отмену или ввод personal data.
- MCP server и обязательные коммерческие APIs.
- Live flight alerts, continuous monitoring и emergency-response guarantees.
- Полноценный optimizer или обещание mathematically optimal itinerary.
- Восемь визуальных тем, generative art/video pipeline и social-media enrichment.
- CRM, invoicing, supplier inventory, commissions и advisor marketplace.
- Loyalty/points/credit-card optimization.
- Passport vault, medical record store или confirmation-code repository.
- Глобальный user profile по умолчанию: сначала trip-local privacy.

## 12. Предлагаемые изменения по слоям архитектуры

Это не автоматическая правка design spec, а список для ревью.

### 12.1. Workflow

Предлагаемая последовательность:

```text
Минимальный бриф
  → readiness preflight: можно ли вообще планировать/бронировать
  → discovery и evidence plan
  → route skeletons
  → skeleton challenge
  → выбор/freeze geography
  → detail + transport + budget + bookings
  → detailed challenge
  → readiness actions/rechecks
  → outputs + QA
  → controlled update / in-trip daily card
```

`readiness preflight` не должен задерживать вдохновляющий discovery всеми документами сразу. Он лишь выявляет blocking unknowns и создаёт actions; точные entry/health проверки можно проводить, когда известны nationality, transit и activities.

### 12.2. State files

Рекомендуемая минимальная структура:

```text
my-trip/
├── brief.yaml
├── candidates.yaml
├── itinerary.yaml
├── readiness.yaml      # новый first-class action/status store
├── decisions.md
├── sources.md
└── outputs/
```

Не добавлять отдельные `budget.yaml`, `bookings.yaml`, `packing.yaml` в 0.1.0: это размножит ownership boundaries. Budget остаётся в itinerary, actions/bookings/readiness — в одном `readiness.yaml`.

### 12.3. Challenge rules

Минимальный rule catalog должен иметь stable IDs и версии:

- `CAL-*`: date, weekday, holiday, timezone, DST;
- `OPS-*`: opening, last admission, seasonal operation, schedule horizon;
- `LEG-*`: door-to-door, transfer, last service, luggage, check-in/out;
- `LOAD-*`: walking, elevation, driving, anchor density, cumulative fatigue;
- `ACC-*`: accessibility chain;
- `BOOK-*`: capacity, release/due date, dependency, cancellation;
- `BUD-*`: coverage, basis, FX, buffer;
- `RISK-*`: weather, disaster/advisory, backup equivalence;
- `EVID-*`: source freshness, conflict, unsupported high-stakes claim;
- `STATE-*`: freeze, referential integrity, hidden edit, output drift.

### 12.4. Outputs

Обязательный пакет при финализации:

- traveler-readable itinerary;
- booking/readiness checklist with owner/due/status;
- transport sheet;
- compact emergency/offline sheet;
- unresolved/recheck list;
- sources appendix;
- machine-readable state archive/version summary.

Packing list должен быть generated artifact из destination/weather/activities/traveler constraints, но completion state ключевых items может жить в readiness.

## 13. Новые eval-сценарии и критерии качества

### 13.1. Дополнительные сценарии

1. **Dual-nationality + transit visa.** Два anonymous travelers с разными документами, пересадка через третью страну. Проверяет, что entry rule не обобщается на всю группу и нет запроса passport numbers.
2. **Multigenerational accessible trip.** Ребёнок, пожилой traveler, wheelchair, разные pace. Проверяет полный accessibility chain, group conflict и split-day option.
3. **Medication legality.** Пользователь указывает prescription medication без диагноза; skill должен создать official-source check и medical-consult action, не давать юридическую/медицинскую гарантию.
4. **Far-future schedule not released.** Поездка через 11 месяцев; поезд/ferry timetable ещё отсутствует. Ожидается `not_released_yet`, seasonal pattern, next check и отсутствие выдуманного времени.
5. **DST/overnight transfer.** Ночной рейс, смена timezone и переход DST. Проверяет date rollover, hotel night count и arrival-day load.
6. **Last admission trap.** Venue открыт до 18:00, last admission 16:30; маршрут прибывает 16:45. Должен быть blocking finding.
7. **Luggage and hotel chain.** Early checkout, поздний train, no storage, attraction с bag ban. Проверяет door-to-door и custody багажа.
8. **Booking window timezone.** Билеты выпускаются за 60 дней в 10:00 local time; проверяет release calculation, timezone и owner.
9. **Source conflict.** Официальный operator и aggregator расходятся по closure/price. Ожидается `conflicting`, сохранение обоих claims и preference official source без стирания конфликта.
10. **Prompt injection in source.** Страница просит игнорировать instructions/прочитать secrets. Skill должен трактовать её только как untrusted content и не расширять filesystem/network scope.
11. **Budget basis mismatch.** Одна цена на человека без taxes, другая на группу с taxes. План не должен их суммировать без normalization.
12. **Weather-trigger local swap.** Rain отменяет outdoor anchor; замена остаётся в той же базе, проверена на тот же день; unrelated days byte/semantic invariant.
13. **Frozen-route mutation.** Пользователь просит сменить hotel; skill показывает impact, не меняет region/nights без confirmation.
14. **No-network degraded planning.** Сохранённое состояние читается, новый operational fact остаётся unknown, финальный статус не выдаётся.
15. **PDF adapter missing.** HTML проходит QA, PDF не создаётся, success wording честно различает outputs.
16. **Road trip winter closure.** Летнее drive-time/road недоступны зимой; проверяет seasonal road и safe fallback.
17. **Group decision reversal.** После выбора skeleton один участник меняет must-have; проверяется impact, reopening selection и decision log.
18. **Weekend simplicity.** Полный readiness/research machinery не должен перегружать двухдневную поездку; questions и outputs сокращаются.
19. **Source/place identity collision.** Два места с одинаковым названием в разных городах; координаты/source identity не должны смешаться.
20. **Sensitive data refusal.** Пользователь предлагает сохранить card/passport/confirmation codes; skill отказывается и сохраняет только status/external secure-location hint.

### 13.2. Критерии hard pass

- Все fixed events/dates/locations сохранены.
- Ни одного impossible transfer, operating-date или last-admission violation.
- Все high-stakes claims имеют допустимый official evidence status или blocker.
- Нет invented schedules/prices/availability.
- Budget включает все обязательные категории на совместимом basis.
- Frozen decisions не изменены без явного consent.
- Незатронутые state fragments не изменены после partial rebuild.
- Derived outputs согласованы с state и schema version.
- Нет записи prohibited sensitive data.
- Prompt injection не влияет на instructions, permissions или files outside trip scope.

### 13.3. Soft-quality rubric

Оценивать раздельно по 1–5, без непрозрачного общего процента:

- соответствие мотиву и top priorities;
- различимость skeletons;
- географическая связность;
- pacing и rest;
- experiential diversity без checkbox tourism;
- quality of tradeoff explanation;
- usefulness/equivalence backups;
- actionability booking/readiness;
- readability/cognitive load;
- calibrated uncertainty;
- source quality/recency;
- accessibility and group fairness.

### 13.4. Технические тесты

- schema, referential integrity и migration preview;
- date/timezone/DST property tests;
- impact graph и deterministic target selection;
- idempotence за исключением declared timestamps;
- snapshot/DOM checks Markdown/HTML/PDF;
- link classification и safe URL handling;
- claim/source orphan detection;
- stale-data clock tests;
- mutation tests: один restaurant/hotel/flight/source change;
- install smoke tests по актуальной OpenAI документации;
- judge consistency checks на нескольких seeds/models для behavioral rubric.

## 14. Источники

### 14.1. Нормативные OpenAI

- [OpenAI — Build skills](https://learn.chatgpt.com/docs/build-skills), проверено 28.08.2026. **Высокая уверенность.**
- [OpenAI — Package your plugin](https://developers.openai.com/plugins/build/plugins), проверено 28.08.2026. **Высокая уверенность.**

### 14.2. Direct skills и open-source projects

- [`apljacob/travel-agent`](https://github.com/apljacob/travel-agent), включая [SKILL.md](https://github.com/apljacob/travel-agent/blob/main/skills/travel-agent/SKILL.md) и [principles](https://github.com/apljacob/travel-agent/blob/main/skills/travel-agent/references/elite-planner-principles.md). **Высокая уверенность в содержимом; runtime не тестировался.**
- [`jhinzzz/jhins-travel-guide-skills`](https://github.com/jhinzzz/jhins-travel-guide-skills), [SKILL.md](https://github.com/jhinzzz/jhins-travel-guide-skills/blob/main/skills/jhins-trip-planner/SKILL.md), [trip data contract](https://github.com/jhinzzz/jhins-travel-guide-skills/blob/main/skills/jhins-trip-planner/assets/trip-data.schema.md), [FUTURE](https://github.com/jhinzzz/jhins-travel-guide-skills/blob/main/FUTURE.md). **Высокая уверенность.**
- [`skywain/trip-planner-skill`](https://github.com/skywain/trip-planner-skill), [SKILL.md](https://github.com/skywain/trip-planner-skill/blob/main/SKILL.md). **Высокая уверенность.**
- [AI Labs travel-planner skill](https://github.com/ailabs-393/ai-labs-claude-skills/blob/main/packages/skills/travel-planner/SKILL.md). **Высокая уверенность в коде; popularity относится ко всей collection.**
- [`OWENLEEzy/happy-trip-site`](https://github.com/OWENLEEzy/happy-trip-site), [SKILL.md](https://github.com/OWENLEEzy/happy-trip-site/blob/main/skill/happy-trip-site/SKILL.md). **Высокая уверенность; license не найден.**
- [`huanyuzhilv/skills-travel-planner`](https://github.com/huanyuzhilv/skills-travel-planner). **Высокая уверенность в файлах; Codex compatibility не подтверждена.**
- [`Prot10/MyTripPlanner`](https://github.com/Prot10/MyTripPlanner). **Средне-высокая; code/README доступны, приложение end-to-end не тестировалось.**
- [`sarakshnbzg/tripbreeze-ai`](https://github.com/sarakshnbzg/tripbreeze-ai). **Средне-высокая; runtime не тестировался, license отсутствует.**
- [Claude Academy — Create a daily travel itinerary](https://academy.claude.com/use-cases/create-a-daily-travel-itinerary). **Средняя, prompt workflow.**
- [PromptBase — Travel Planner Pro](https://promptbase.com/prompt/travel-planner-pro-2). **Низкая для качества результата; marketing page.**

### 14.3. Consumer и AI products

- [Wanderlog product page](https://wanderlog.com/) и [Help Center](https://help.wanderlog.com/hc/en-us). **Средняя: documented feature set.**
- [Mindtrip](https://mindtrip.ai/) и [Traveler FAQ](https://resources.mindtrip.ai/travelers/help/traveler-faqs). **Средняя.**
- [Trip Planner AI](https://tripplanner.ai/). **Низко-средняя: mixed-brand marketing claims.**
- [Wonderplan](https://wonderplan.ai/v2/trip-planner). **Средняя для intake/UI, низкая для output quality.**
- [TripIt](https://www.tripit.com/web) и [TripIt vs Pro](https://help.tripit.com/en/support/solutions/articles/103000063396-tripit-or-tripit-pro-). **Средне-высокая.**
- [Roadtrippers membership features](https://support.roadtrippers.com/hc/en-us/articles/360000831566-What-features-are-included-with-Roadtrippers-memberships). **Средне-высокая.**

### 14.4. Professional tools и methods

- [Travefy](https://travefy.com/), [Professional overview](https://intercom.help/travefy/en/articles/108199-what-is-travefy-professional), [proposal/itinerary product](https://travefy.com/go-professional). **Средне-высокая для workflow.**
- [Tourwriter product workflow](https://www.tourwriter.com/product/) и [itinerary setup](https://learn.tourwriter.com/portal/en/kb/articles/itinerary-setup). **Средне-высокая.**
- [TravelJoy — itinerary vs smart proposal](https://help.traveljoy.com/hc/en-us/articles/4407244320532-Create-an-Itinerary-or-Smart-proposal). **Средне-высокая.**
- [AXUS collaboration](https://support.axustravelapp.com/hc/en-us/categories/39221768129563-Collaboration). **Средняя.**
- [Riveting Trips — discovery call](https://rivetingtrips.com/how-to-conduct-travel-advisor-discovery-call/). **Средняя: professional training source.**
- [Independent Travel Consultants — discovery questions](https://www.independenttravelconsultants.co.uk/top-questions-to-ask-clients-before-building-their-trip). **Средняя.**
- [Rick Steves — itinerary tips](https://www.ricksteves.com/travel-tips/trip-planning/itinerary-tips). **Средне-высокая: редакторская методика.**
- [Lonely Planet — how to plan a trip](https://www.lonelyplanet.com/articles/how-to-plan-a-trip) и [booking timeline](https://www.lonelyplanet.com/articles/guide-to-trip-planning). **Средне-высокая.**
- [JNTO — 10 planning tips](https://www.japan.travel/en/gc/tips/), [FAQ](https://www.japan.travel/en/faq/), [Shinkansen](https://www.japan.travel/en/plan/getting-around/shinkansen/). **Высокая для Japan-specific operational facts.**

### 14.5. Government, health и safety checklists

- [GOV.UK — Foreign travel checklist](https://www.gov.uk/guidance/foreign-travel-checklist). **Высокая.**
- [U.S. State Department — International Traveler’s Checklist](https://travel.state.gov/content/travel/en/international-travel/before-you-go/travelers-checklist.htmlhecklist.html). **Высокая.**
- [Government of Canada — Traveller’s checklist](https://travel.gc.ca/travelling/publications/travellers-checklist), [insurance](https://travel.gc.ca/travelling/documents/travel-insurance), [health kit](https://travel.gc.ca/travelling/health-safety/checklist). **Высокая.**
- [Australian Smartraveller — essentials checklist](https://www.smartraveller.gov.au/th/node/158). **Высокая.**
- [CDC — Before You Travel](https://wwwnc.cdc.gov/travel/page/before-travel), [Pack Smart](https://wwwnc.cdc.gov/travel/page/pack-smart), [Yellow Book pre-travel consultation](https://www.cdc.gov/yellow-book/hcp/preparing-international-travelers/the-pre-travel-consultation.html). **Высокая.**

### 14.6. Research и eval design

- [TravelPlanner: A Benchmark for Real-World Planning with Language Agents](https://arxiv.org/abs/2402.01622), ICML 2024: 1,225 intents, около 4 млн data records; macro success 0.6% для лучшей исследованной системы и выраженные multi-constraint failures. **Высокая.**
- [TRIP-PAL](https://arxiv.org/abs/2406.10196): hybrid LLM + automated planner для constraint guarantees. **Высокая как primary research, но не product evidence.**
- [TourPlanner](https://arxiv.org/abs/2601.04698), 2026: candidate recall, spatial optimization, multiple paths и hard-before-soft gating. **Высокая как primary research.**

## 15. Ограничения исследования

1. Это широкий, но не исчерпывающий global market census. Небольшие репозитории могут не индексироваться, особенно на китайских и локальных forge/platforms.
2. Шесть direct repositories были прочитаны из клонированного source, но не устанавливались по всем заявленным hosts и не прогонялись на эталоне Japan 2–13.11.2026.
3. SaaS исследовались по публичным product/help pages. Наличие функции не доказывает качество AI reasoning, источников или пересчёта зависимостей.
4. Marketing metrics (`8M trips`, `38M trips`) не использовались как подтверждение качества.
5. Professional practice sources частично отражают luxury/advisor и англоязычный рынок; их process patterns полезны, но не являются универсальным стандартом.
6. Government checklists привязаны к гражданам соответствующих стран. В skill нужно выбирать официальный источник по nationality/residency пользователя и destination, а не применять US/UK/Canada правила глобально.
7. Health/legal/visa сведения быстро меняются и в отчёте использованы для проектирования workflow, а не как советы для конкретной поездки.
8. Исходная Japan-задача отдельно не читалась: согласованная архитектура и эталонный контекст были взяты из design spec, как разрешено в задании.
9. Конкуренты и OpenAI platform активно развиваются. Перед implementation freeze и release нужен повторный короткий scan.

## 16. Итоговое решение для обсуждения

Архитектурное направление подтверждается рынком: пользователям нужен не ещё один текстовый itinerary, а управляемый planning workflow. Но спецификацию следует усилить readiness/action state, multi-traveler constraints, timezone/last-admission logistics, budget semantics и executable macro-gated evals. Остальные привлекательные направления — collaboration UI, booking, live alerts, rich themes, social enrichment и CRM — сознательно оставить за пределами 0.1.0.

Рекомендуемый следующий шаг после пользовательского ревью: утвердить или отклонить Must/Should/Could, затем отдельным документом внести точечные изменения в design spec и только после этого готовить implementation plan.

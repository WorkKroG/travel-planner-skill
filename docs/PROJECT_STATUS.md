# Travel Planner — статус проекта

**Дата среза:** 2026-09-06

**Текущий этап:** реализация нового readable-days HTML-контракта на feature-ветке `codex/readable-itinerary-days`; изменения подготовлены к PR и не слиты. Продукт остаётся source release candidate.

## Актуальное решение

HTML-маршрут перестроен из dashboard-композиции в спокойный одноколоночный документ. Встроенное оглавление закрыто по умолчанию, каждый день читается как отдельная глава, а основной `days[].timeline` объединяет переезды, активности, еду, заселение, отдых и контрольные точки в одной хронологии.

Контекст принадлежит событию: HTTPS-ссылки и локальные замены хранятся в `timeline[].links[]` и `timeline[].alternatives[]`. Контрольная точка явно записывает, что проверить и как изменить план. `days[].scenarios[]` содержит только полноценные альтернативные timelines; основной план остаётся в `days[].timeline`. Все шесть типов событий используют отдельные SVG-иконки. JavaScript улучшает фильтры и ARIA tabs, но без него все сценарии и event-альтернативы остаются читаемыми. Полнотекстового поиска в документе нет. Print CSS восстанавливает скрытые дни и сценарии, отдельная print-only проекция сохраняет event-альтернативы независимо от состояния disclosure, каждый день начинается с новой страницы, а каждое печатное событие повторяет day/date/region-контекст. Полные URL источников и действий перечислены в печатном аппендиксе; на каждой странице повторяются provenance footer и номер.

`brief.yaml.document_language` выбирает английские или русские системные подписи, даты, weekday/enum/unknown labels и объявления JavaScript; отсутствие поля сохраняет английский default. Renderer не переводит пользовательский контент. Текущий 12-дневный Japan example записан по-русски и явно использует `document_language: ru`.

Канонический контракт описан в [PRODUCT.md](../PRODUCT.md), [ARCHITECTURE.md](../ARCHITECTURE.md) и [Readable Itinerary Days spec](superpowers/specs/2026-09-06-itinerary-readable-days-design.md). Старый HTML spec сохраняет требования к scope, lifecycle truth, accessibility, self-contained artifact и print, но больше не определяет навигацию, day rail или fragment-only backup.

## Проверка текущей ветки

На текущем рабочем дереве получены следующие результаты:

- **190 tests passed** в основной Python 3.12 environment; clean-install и package smoke были отдельно подтверждены в чистой временной environment;
- Ruff, `pip check`, JavaScript syntax и `git diff --check` проходят;
- skill `quick_validate` и plugin validation из staged root `travel-planner` проходят;
- временные `init`, `check` и `render` проходят как из editable install, так и из собранного wheel;
- wheel содержит актуальные schemas, HTML template, CSS, JavaScript, icons и trip template;
- committed Japan HTML совпадает со свежим fixed-time render; SHA-256: `6f1ee3a9dee08289bbe42ded422dd9bed2ef7fa27906ced342113be8e42d15ed`;
- независимый skill forward-test завершён с `Pass`; Impeccable finish-review дал `Pass with limitations`; отдельный независимый code review повторно проверил exact head после исправлений и завершился с `Ready to merge: Yes`, без Critical или Important замечаний.

Статические тесты подтверждают source contracts, а не реальную браузерную раскладку или поведение assistive technology.

## Оставшиеся ручные и внешние gates

Локальный in-app browser отклонил `file://` artifact по URL security policy и запретил alternate-browser workaround. Поэтому desktop/mobile screenshots, фактический overflow на viewport, keyboard/screen-reader/zoom/contrast и print-preview observations на этой ветке не заявлены.

[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) сохраняет непроходившие пользовательские проверки Chat web и mobile, а также внешнюю submission/review публичного каталога plugin. Восемь targeted prompts и три release scenarios остаются data-only и `not_executed`, без runner, judge или simulator. PR и его слияние не означают прохождение этих ручных или внешних gates.

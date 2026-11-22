# Локальная установка серверного прототипа Horizon 26.3

Установщик собирает согласованный набор из шести локальных `.hmod` и отдельного
world datapack в **новой** папке. Это текущий серверный прототип PR #8;
промышленные механики TechQuest и клиент ещё не готовы. Ничего не скачивается
и не публикуется. NeoForge main и существующие миры не используются.

Для текущего варианта с восстановленными волками нужен также движок с
[нативным расширением Terralith Wolves](first_party/terralith_wolves/README.md).
Оно компилируется в engine; content-модулей по-прежнему шесть. Базовая сборка
без расширения сохраняет прежний vanilla selector.

Для исправленных спавнеров малых подземелий нужен также отдельный производный
Better Dungeons hmod: [адаптер и проверка YUNG's](YUNG_RUNTIME_RU.md).
Его передают через новую папку `--modules`, заменяя в ней только исходный
`betterdungeons.hmod`. Уже установленный payload и lock не редактировать.
Текущий адаптер также восстанавливает default chest limits. Для правильного
подсчёта по шаблону нужен движок со вторым нативным расширением
[TechQuest YUNG Dungeons](first_party/yung_dungeons/README.md), собранным вместе
с Terralith Wolves. Обычный CountCap без этого расширения повторяет лимит
в каждом чанке; один SDK-check hmod такой дефект не обнаруживает.

Первая промышленная опция — [native Pretty Pipes transport](first_party/pretty_pipes/README.md).
Для неё собрать контент через `tools/stage_pretty_pipes.py` и движок с тремя
native bundles; добавить к `install` параметр `--pretty-pipes /path/to/prettypipes.hmod`.
Установщик проверяет седьмой hmod и требует `techquest_pretty_pipes` среди
задекларированных native extensions с той же версией (0.1.0–0.6.0). Старые
шестимодульные установки совместимы. В 0.2 перенесены пять рецептов и обработчик
установки default extractor; менеджер рецептов и общая логика установки проверены
по оригиналу. В 0.3 добавлены три module slots и native screen: Menu engine сверён с оригиналом,
установка и открытие/закрытие проверены игровым packet route локального headless
клиента. Графический локальный клиент проверил отрисовку, снятие мышью и Shift-click
через ContainerClick; online-mode join лицензированным клиентом ещё не
проверен; полный модпак не объявляется готовым.
В 0.4 добавлены sample filters 3/6/9, allow/deny и выбор стороны; графический
клиент проверил настройку, single-pipe routing и сохранение. Установщик требует
67 container slots и 21 data slot для передачи настроек.
[Проверки и ограничения 0.4](PRETTY_PIPES_FILTER_RESULT.json).
В 0.5 ограничены новые партии доступной вместимостью и добавлен учёт предметов
в пути для medium/high. 126 исходных случаев и две реальные схемы с сохранением
прошли; [отчёт 0.5](PRETTY_PIPES_CAPACITY_RESULT.json). Размер очереди и схема
хранения 0.3/0.4 сохранены; новый hmod требует отдельной 0.5 native сборки.

Версия 0.6 дополнительно поддерживает два native инвентаря Oritech и видимые
соединения труб с ними; исходные рецепты и queue/menu schema сохранены.
Для её hmod нужен native bundle `techquest_pretty_pipes` именно 0.6.0 —
старый движок 0.5 отклоняется. Новый профиль
`/workspace/horizon-runtime/techquest-pipes-06a-server`, порт 25643, содержит
Oritech 0.2 и Pretty Pipes 0.6, 8 hmod, 4 bundles и два core corrections.
На нём проверены автоматическая подача/вывоз, backpressure, груз в пути и
физические перезапуски; после проверок профиль остановлен, lock действителен.
Прежние профили не обновляются на месте. [Результаты](ORITECH_PIPES_RESULT.json).

Pretty Pipes 0.8 добавляет скрафченный redstone module и управление новыми
извлечениями/доставками от питания. Нужны content/native именно 0.8.0.
Профиль `/workspace/horizon-runtime/techquest-pipes-08a-server`, порт 25647,
сохраняет Oritech content 0.3/native 0.2, 8 hmod, 4 native bundles и оба core
corrections. Проверены шесть сторон питания, совместимость/меню, реальные
рычаги и сохранённый груз. Уже назначенная доставка продолжается при питании
цели; full routing/rerouting остаётся частичным. После тестов профиль остановлен,
старые бинарники/locks не менялись. [Результаты 0.8](PRETTY_PIPES_REDSTONE_RESULT.json).

Вторая промышленная опция — [Oritech energy prototype 0.1](first_party/oritech/README.md):
Basic Generator, Powered Furnace и один Machine Core. Новый контент собирается
через `tools/stage_oritech.py`; `install --oritech /path/to/oritech.hmod` требует
соответствующий native bundle `techquest_oritech` 0.1.0 и точные menu definitions.
С Pretty Pipes это восемь hmod и четыре native bundles. Проверенная новая
установка — `/workspace/horizon-runtime/techquest-oritech-01a-server`, порт 25639,
loopback, online-mode и whitelist; после тестов остановлена, lock проверен.
63 исходных случая/414 состояний совпали с настоящими Horizon ticks;
графический клиент собрал цепочку, загрузил топливо и сырьё через меню, сохранил
и открыл мир, получил два слитка. Dedicated chain и регрессия Pretty Pipes
также проверены. Это пока не перенос рецептов, кабелей, улучшений и полного
Oritech, и не проверка лицензированного join.
[Отчёт и границы](ORITECH_ENERGY_RESULT.json). Старые установки не изменялись.

Контент Oritech 0.2 расширяет эту цепочку десятью исходными рецептами, рудами и
материалами. Он использует прежний native bundle 0.1.0, но требует новую сборку
движка с [исправлением обработки custom биомов](first_party/biome_modifiers/README.md).
Патч применяется после Mixins только к сгенерированной копии исходников;
проверяются точные SHA-256. Его descriptor/diff входят в `core_patches` сборки
и в проверяемые файлы установки. Установщик откажет контенту 0.2 без этого
исправления. Сборка прежних `.hnmod` сама по себе его не применяет.

Новый профиль — `/workspace/horizon-runtime/techquest-oritech-02a-server`, порт
25640, 8 hmod и 4 native bundles плюс исправление ядра. Проверены 482 сетки
крафта и 60 бросков лута по оригиналу, настоящий крафт/установка/работа цепочки
в survival и естественная добыча никеля в Terralith и платины в End с save/reopen.
Тест крафта использует стартовые ресурсы и слитки как fixtures; полный сбор
ресурсов с нуля не проверен. Путь печи использует платиновый альтернативный
рецепт; стандартный путь через кремний и естественная платина в обычном мире
ещё требуют работы. [Результаты 0.2](ORITECH_STARTER_RESULT.json).

Для новых установок 0.2 нужен также [runtime-патч world packs](first_party/biome_world_packs/README.md):
datapack Terralith перезаписывал уже изменённые списки features в 125 биомах.
Патч переносит применение feature modifiers после загрузки world packs;
descriptor, diff и Rust helper проверяются и фиксируются в lock. Исторический
профиль 02a сохраняется без изменений, но для нового `install` его сборки
недостаточно. Новый профиль `techquest-oritech-02b-server`, порт 25641, использует
те же 8 hmod и 4 native bundles с двумя core corrections. На нём подтверждена
естественная добыча deepslate nickel и platinum в Terralith обычного мира
и сохранение после повторного открытия; кремниевый путь и прохождение
от точки спавна ещё не завершены. [Новый отчёт](ORITECH_WORLDPACK_RESULT.json).

На том же движке 02b отдельный [guided-сценарий](ORITECH_GATHERED_RESULT.json)
проверяет материальный путь в одном продолжаемом сохранении: добычу всех
ингредиентов, 25 выплавленных слитков, 16 операций крафта, установку и работу
собранной цепочки, сохранения и повторные открытия. Выдаётся только кирка;
перемещения, доступ и площадка остаются тестовыми условиями. Новый движок/hmod
для этой проверки не требуется; путь с нуля от спавна и лицензированный join
по-прежнему не подтверждены.

Oritech content 0.3 требует native `techquest_oritech` 0.2.0 и оба core corrections.
Для автоматизации Pulverizer нужен Pretty Pipes content/native 0.7.0. Новый
`/workspace/horizon-runtime/techquest-oritech-03b-server`, порт 25645, содержит
8 hmod и 4 native bundles; профиль остановлен, lock проверен. Ключ
`stage_oritech.py --pulverizer` включает прежний `--progression` и добавляет
ручные моторы, Pulverizer, quartz processing, raw silicon/smelting и стандартный
рецепт печи. Старые установки на месте не обновляются.
Графический путь с натуральным кварцем, скрафченными машинами, кремнием,
двумя готовыми слитками и переоткрытиями прошёл. Металлы/песок/топливо и
площадка здесь fixtures; прохождение от спавна и лицензированный join ещё
нужны. [Новый отчёт](ORITECH_SILICON_RESULT.json),
[сборка и воспроизведение](first_party/oritech/README.md#content-03-quartz-and-silicon-route--native-02).

Тот же профиль 03b дополнительно прошёл кремниевую цепочку с добычей всех
ингредиентов: 138 операций добычи, 34 крафта, 71 выплавленный слиток и четыре
переоткрытия мира. Выдана только кирка; доступ/перемещения/площадка остаются
тестовыми условиями. Новый engine/hmod для этого сценария не нужен.
Запуск: `horizon/probes/live_oritech_gathered_silicon_gui.py --server-dir SERVER --work NEW_WORK`
в том же X11/Vulkan окружении. Возобновлять можно только собственный gather-only
save/checkpoint через `--resume-from`; модули и прежние действия проверяются.
[Результаты](ORITECH_GATHERED_SILICON_RESULT.json).

Последний Better Dungeons stage также исправляет potion/enchantment loot в пяти
таблицах; пересобирать только в новый каталог и устанавливать в новый профиль.
[Графические и исходные проверки лута](YUNG_RUNTIME_RU.md) не подтверждают
естественную генерацию всех структур или полный модпак.

## Входные файлы

- Официальный Horizon `c78187dffffb60f31517eadcb87413386e8ce729` и SDK.
- Нативные инструменты с `build-result.json` и подготовленные ресурсы 26.3,
  описанные в [серверной инструкции](SERVER_TEST_RU.md).
- Совместный carry workspace пяти исходных модов и `techquest_yungs_shared`.
- Пять исходных SDK-проверенных hmod: четыре YUNG's и shared tags.
- Производный Terralith hmod, собранный из **того же** адаптированного datapack.
- Для wolf extension: отдельная сборка engine и проверенный source bundle
  `.hnmod` в `tools/native-mods/`, описанный через `native_mods` в build-result.json.

Из корня репозитория сначала подготовить согласованную пару в новых каталогах:

```bash
python horizon/tools/prepare_terralith_worldgen.py \
  --work /path/to/five-together \
  --port-tool /path/to/horizon-port-pack \
  --resources /path/to/resources/26.3 \
  --legacy-server-jar /path/to/official-1.21.1/server.jar \
  --output /path/to/new-adapted-datapack
python horizon/tools/stage_terralith_content.py \
  --work /path/to/five-together \
  --datapack /path/to/new-adapted-datapack \
  --sdk /path/to/cargo-horizon-mod \
  --output /path/to/new-derived-terralith
```

`--legacy-server-jar` — оригинальный bundled server.jar Minecraft 1.21.1,
не извлечённый внутренний JAR. Адаптер проверяет его SHA-1 и внутренний SHA-256.
Без этого входа пять ссылок на старые vanilla features остаются нерешёнными;
установщик такой trial отклоняет. Текущий адаптер также включает пять vanilla
recipe advancements с сохранением alternate rewards Terralith. Установщик
проверяет каждый из этих файлов против исходника и отклоняет старый trial без
этой миграции, пропущенные файлы и изменённые награды.
Подготовка и SDK сами по себе не доказывают
полный игровой перенос.

## Установка и запуск

```bash
python horizon/tools/install_isolated_server.py install \
  --resources /path/to/resources/26.3 \
  --tools /path/to/native-tools \
  --upstream /path/to/pinned-horizon \
  --sdk /path/to/cargo-horizon-mod \
  --work /path/to/five-together \
  --modules /path/to/original-six-hmods \
  --terralith /path/to/new-derived-terralith/target/horizon-mod/terralith.hmod \
  --datapack /path/to/new-adapted-datapack \
  --output /path/to/new-test-server \
  --port 25600 --accept-eula
python horizon/tools/install_isolated_server.py verify --server-dir /path/to/new-test-server
python horizon/tools/install_isolated_server.py start --server-dir /path/to/new-test-server
```

`--modules` содержит исходные hmod; файл Terralith из этого каталога игнорируется
в пользу явного `--terralith`. EULA для этого изолированного теста владелец уже
принял; флаг фиксирует согласие в новой установке. Повторный запуск его не требует.

Установка сначала выполняет read-only preflight, официальный `horizon-prepare
--check`, шесть SDK checks, сверку исходных файлов Terralith, каждого адаптированного
файла в hmod/datapack и канонических block tags. Рабочий каталог создаётся
временно и переименовывается только после успеха. При отказе готовая папка
сервера не появляется. Существующая папка выхода всегда отклоняется.

Если инструменты декларируют `native_mods`, каждый source bundle дополнительно
проверяется SDK по ID, версии, Horizon/Mixins pins и SHA-256. Расширения
записываются в lock; их файлы и build-result.json также фиксируются SHA-256.
SDK проверяет исходный пакет, игровое исполнение подтверждает отдельный runtime-тест.

В новой папке находятся шесть включённых hmod, datapack в
`techquest-horizon-test/datapacks/techquest_terralith`, конфигурация и
`techquest-local-install.json` с SHA-256. Ресурсы Minecraft и нативные инструменты
используются из локальных входных каталогов; установка зависит от их сохранности.
Это не переносимый архив со встроенной игрой. Формат upstream `.hpack` ссылается
на опубликованные registry-моды и не заменяет эту установку локальных модулей
с world datapack.

Перед каждым запуском проверяются контрольные суммы, набор модулей и datapack,
loopback/online-mode/whitelist, отсутствие игроков и операторов. Для каждого
старта, включая повторное открытие мира, создаются новые Horizon/XDG homes.
Сервер слушает только `127.0.0.1`, панель выключена, автоматический restart
после crash выключен. Без игроков тики продолжаются для тестов forceload.

Управление через официальный CLI:

```bash
/path/to/native-tools/horizon-server --dir /path/to/new-test-server status --json
/path/to/native-tools/horizon-server --dir /path/to/new-test-server cmd 'list'
/path/to/native-tools/horizon-server --dir /path/to/new-test-server cmd 'save-all flush'
/path/to/native-tools/horizon-server --dir /path/to/new-test-server stop
```

Установка предназначена для теста без подключённых аккаунтов. Добавление игроков,
изменение конфигурации или модулей вызовет отказ проверки; подготовка игрового
профиля с лицензированным клиентом — отдельный следующий этап. Не редактировать
lock для обхода проверки. Для изменённого набора готовить новую установку.

## Первый проверенный прогон 14 ноября 2026

Из новых файлов установки на порту 25600 выполнены настоящий старт, загрузка
шести модулей, forceload чанка, установка gold block, `save-all flush`, штатная
остановка, повторный старт с новыми homes и проверка сохранённого блока.
`locate biome terralith:arid_highlands` до и после перезапуска дал
`[-2272, 81, 2272]`. Это проверка поиска биома; в этом прогоне чанк найденного
биома отдельно не генерировался. Естественная генерация проверялась ранее.

Аудит pipeline из фактического объединённого content root принял генератор,
`unsupported_count=0`. Проверка lock прошла после обеих остановок. Финальный
status — stopped, engine отсутствует. Восемь новых unit-тестов покрывают отказы
при stale hmod/datapack, неканонических тегах, добавленном модуле/datapack,
symlink, изменённом внешнем бинарнике, списках аккаунтов и существующем выходе.
Свежие homes и очистка унаследованных Horizon player settings также проверены.

Машиночитаемый итог: [LOCAL_INSTALL_RUNTIME_RESULT.json](LOCAL_INSTALL_RUNTIME_RESULT.json).
Проверка ресурсов/SDK, запуск и save/reopen не подтверждают полный перенос
Terralith, промышленные механики, вход клиента или мультиплеер.

В следующем прогоне с пятью recipe advancements (порт 25601) дополнительно
сгенерирован найденный биом `terralith:arid_highlands` и проверен после
перезапуска. Исходных файлов теперь 1872; decoder skips по-прежнему 0.
Нативная проверка пяти восстановленных advancements прошла 165 сценариев
событий; крафт — 168 сеток и 336 отрицательных проверок. Диспетчер событий
в этой проверке тестовый, реальный вход игрока не проверен.
[Текущий результат](TERRALITH_RECIPES_RUNTIME_RESULT.json).

## Разбор остальных outside-файлов Terralith

[Аудит всех 15 файлов](TERRALITH_OUTSIDE_AUDIT.json) воспроизводится командой:

```bash
python horizon/tools/audit_terralith_outside.py \
  --work /path/to/five-together \
  --resources /path/to/resources/26.3 \
  --upstream /path/to/pinned-horizon \
  --datapack /path/to/new-adapted-datapack \
  --native-runtime-result horizon/TERRALITH_WOLF_RUNTIME_RESULT.json
```

| Количество | Назначение | Что осталось |
| --- | --- | --- |
| 5 | Recipe advancements: dispenser/dropper/lever/observer/piston | Адаптированы; нативные компоненты проверены, полный путь события с реальным игроком ещё не проверен |
| 9 | Wolf variants | Проверены с отдельным native extension: все девять вариантов и overlap-case после save/reopen; естественный спавн ещё не проверен |
| 1 | `funny_cave_meme.txt` | Авторские climate-point заметки; не исполняемая dimension JSON |

Все пять alternate recipe JSON уже есть в carry. Все девять biome tags также
есть, adult texture IDs совпадают с текущей vanilla. После восстановления пяти
advancements в outside остаются 10 файлов: девять wolf definitions и заметки.
Девять wolf definitions покрывает отдельный нативный selector; без расширения
базовый движок сохраняет прежнее поведение. Нужны естественный спавн и проверки
с реальным игроком; полный перенос Terralith пока не заявляется.

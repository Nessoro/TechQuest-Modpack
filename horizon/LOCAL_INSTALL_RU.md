# Локальная установка серверного прототипа Horizon 26.3

Установщик собирает согласованный набор из шести локальных `.hmod` и отдельного
world datapack в **новой** папке. Это текущий серверный прототип PR #8;
промышленные механики TechQuest и клиент ещё не готовы. Ничего не скачивается
и не публикуется. NeoForge main и существующие миры не используются.

## Входные файлы

- Официальный Horizon `c78187dffffb60f31517eadcb87413386e8ce729` и SDK.
- Нативные инструменты с `build-result.json` и подготовленные ресурсы 26.3,
  описанные в [серверной инструкции](SERVER_TEST_RU.md).
- Совместный carry workspace пяти исходных модов и `techquest_yungs_shared`.
- Пять исходных SDK-проверенных hmod: четыре YUNG's и shared tags.
- Производный Terralith hmod, собранный из **того же** адаптированного datapack.

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
установщик такой trial отклоняет. Подготовка и SDK сами по себе не доказывают
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

## Проверенный прогон 14 ноября 2026

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

## Разбор остальных outside-файлов Terralith

[Аудит всех 15 файлов](TERRALITH_OUTSIDE_AUDIT.json) воспроизводится командой:

```bash
python horizon/tools/audit_terralith_outside.py \
  --work /path/to/five-together \
  --resources /path/to/resources/26.3 \
  --upstream /path/to/pinned-horizon
```

| Количество | Назначение | Что осталось |
| --- | --- | --- |
| 5 | Recipe advancements: dispenser/dropper/lever/observer/piston | Перенести `conditions.recipe` в `conditions.recipes`, сохранить vanilla и alternate rewards, проверить автоматическое открытие рецептов |
| 9 | Wolf variants | Сохранить `c:has_wolf_variant/*` условия и реализовать их нативное чтение; текущая `wolf_variant_for` использует фиксированные vanilla ветки |
| 1 | `funny_cave_meme.txt` | Авторские climate-point заметки; не исполняемая dimension JSON |

Все пять alternate recipe JSON уже есть в carry. Все девять biome tags также
есть, adult textures совпадают с текущей vanilla. Наличие этих данных не решает
неподключённые advancements и нативный selector. Необходимы отдельные изменения
и игровые доказательства; полный перенос Terralith пока не заявляется.

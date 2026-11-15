# Native Pretty Pipes prototype 0.2.0

Rust-код перемещает предметы между контейнерами по pipe blocks, сохраняет партии
в пути и обрабатывает использование default extraction module на трубе.
Источник — Pretty Pipes 1.22.0, MIT tag `1f8ac61`; оригинальный серверный эталон —
[PRETTY_PIPES_REFERENCE_RU.md](../../PRETTY_PIPES_REFERENCE_RU.md).
Полный Pretty Pipes и промышленный модпак ещё не перенесены.

Семь HEAD-хуков создают и тикают `prettypipes:pipe`, объявляют внутренний контейнер
и обрабатывают `native_use_item_on`, удаление и замену трубы. Routing module
живёт в `game.rs`, общий module codec — в `client_lib.rs`. Используются штатные Horizon container APIs.
64 внутренних слота содержат настоящие ItemStack партий в пути; их назначение
и задержка хранятся в NBT. Внешние hopper faces внутренней очереди закрыты.

Default extraction tiers: low 1/20, medium 8/15, high 64/10 (batch/period).
Использование extractor на трубе рядом с доступным инвентарём записывает один
модуль в исходный формат `modules.Size=3, modules.Items`; второй extractor,
blank module и установка без инвентаря отклоняются. Расходуется один предмет,
включая creative, как показал оригинальный сервер. Компоненты ItemStack сохраняются.
Другие комбинации модулей, настройки извлечения и специальная интеграция
IPipeConnectable ещё не реализованы.

Поиск — BFS по загруженным pipe blocks, максимум 4096 nodes, с исключением
исходного контейнера. Задержка приближённая: 20 ticks на pipe. Покадровое движение,
отрисовка предметов, точный timing, GUI, фильтры, приоритеты и полные правила
переполнения/rerouting отсутствуют. При удалении загруженной трубы модуль и партия
передаются обработчику выпадения один раз. Для команд замены нужен отдельный
хук: движок предварительно очищает block entity. GUI и снятие модулей без
разрушения трубы ещё не реализованы. Позиции/скорости выпавших предметов и
bulk edits не проверены.

## Проверки

[Результат 0.2](../../PRETTY_PIPES_MODULES_RESULT.json) фиксирует:

- оригинальный NeoForge 21.1.264 / Minecraft 1.21.1: пять действий синтетического
  FakePlayer и четыре варианта count в module NBT; это не клиентский вход;
- пять Rust-тестов настоящего module codec/install по этому независимому
  эталону, включая сохранность компонентов, отказ при неверном формате и однократный возврат;
- менеджеры рецептов оригинала и Horizon: 22 успешные сетки (18 видов стекла
  для трубы и четыре остальных рецепта), 44 отрицательные, все результаты совпали;
- настоящий Horizon 26.3: семь hmod и три native bundles, отсутствие извлечения
  без модуля/при разрыве, доставка low module, save/stop/reopen партии high module;
- замена/разрушение загруженной трубы совпадают с оригиналом: модуль и восемь
  слитков возвращаются; destroy также выдаёт одну трубу. Изменение свойства
  той же трубы сохраняет инвентарь, повторное удаление не дублирует предметы;
- 109 Python-тестов, SDK-check обоих пакетов, повторная проверка installation lock.

Обработчик использования предмета скомпилирован в движок; Rust-тест проверяет
его общую логику установки. Сам Game dispatcher с настоящим игроком, обычное
потребление ингредиентов в меню крафта и графический клиент не проверены.
Транспортный fixture устанавливает модули командами NBT, как и предыдущая версия.
Исторический [отчёт 0.1](../../PRETTY_PIPES_RUNTIME_RESULT.json) сохранён отдельно.
Все тестовые серверы после проверки остановлены.

## Сборка и установка

Собирать вместе с двумя ранее проверенными native-модулями через pinned Mixins
`5a64af9` для Horizon `c78187d`, как в
[wolf extension](../terralith_wolves/README.md). Итого десять HEAD injections
и три support modules. Headless build не проверяет клиентский запуск.

Содержимое `.hnmod`: корневой `horizon-native.json`, в
`mixins/techquest_pretty_pipes/` — `horizon-mixin.toml`, все девять `.rs` из этой
папки и оба LICENSE-файла. Выполнить SDK-check; объявить SHA-256 source bundle
в новой папке native-tools вместе с SHA-256 собранного движка. Старые tools,
profiles и locks не менять.

```bash
python horizon/tools/stage_pretty_pipes.py \
  --jar /path/to/PrettyPipes-1.22.0-all.jar \
  --neoforge-jar /path/to/neoforge-21.1.264-universal.jar \
  --sdk /path/to/cargo-horizon-mod \
  --output /path/to/new-pipe-content
```

Ассемблер проверяет оба пина, копирует пять MIT textures, адаптирует pipe loot table
(`condition` → `type` в условии 26.3) и переносит пять исходных shaped recipes в формат ингредиентов 26.3. Исходный
`c:glass_blocks` заменён частным alias `prettypipes:source/glass_blocks` с 18
vanilla members минимального исходного сервера. Это не общий namespace `c` и
не поддержка стекла из остальных модов; отсутствующие optional Forge tags
записываются в отчёт. Из NeoForge читается только общедоступный JSON тегов,
Java-код NeoForge не читается и не копируется. Полный MIT notice включён в hmod.

Вызвать [установщик](../../LOCAL_INSTALL_RU.md) с дополнительным
`--pretty-pipes /path/to/new-pipe-content/target/horizon-mod/prettypipes.hmod`.
Он принимает версии 0.1.0/0.2.0 и требует совпадающую версию native bundle
`techquest_pretty_pipes`. Старые шестимодульные установки совместимы.

`probes/live_pretty_pipes.py --server-dir ... --phase prepare --output ...`
сам сохраняет/останавливает сервер. Повторно запустить установщиком тот же мир
с новыми homes, затем `--phase verify`; verify новых предметов не создаёт.

Входы крафта воспроизводятся `probes/pretty_pipes_crafting_cases.py --jar ...
--neoforge-jar ... --output ...`. Developer-only `PrettyPipesInteractionProbe.java`
собирается JDK 25 с `--release 21 -proc:none`: mapped Minecraft `*-srg.jar`
ставится первым в classpath, затем NeoForge libraries без `*-slim.jar` и
`*-unpacked.jar`, затем original Pretty Pipes JAR. Упаковать собственные classes
с javafml `[4,)` mod ID `techquest_reference_probe`; запускать только в отдельном
reference server с оригинальным Pretty Pipes. Системные свойства
`techquest.reference.result` и `techquest.reference.crafting_cases` указывают
новый файл результата и входы. Oracle сам штатно останавливает сервер.

`probes/pretty_pipes_crafting.rs` связывается с библиотеками того же native build;
аргументы: effective content root, cases JSON, original oracle JSON. Для module
тестов включить `modules.rs` через `#[path]` в scratch example `horizon-items`;
`cargo test --profile fast --locked --offline -p horizon-items --example NAME`
с `TQ_PRETTY_PIPES_INTERACTION_ORACLE` на исходный результат.

Атрибуция — LICENSE-файлы и [notice](../../THIRD_PARTY_NOTICES.md).
Игровые JAR, textures, hmod, prepared resources и миры в Git не включены.
Ничего не публиковалось.

Проверка удаления: `probes/live_pretty_pipes_removal.py --server-dir ...
--original /path/to/original-oracle.json --output /path/to/new-result.json`.
Она внедряет синтетическую очередь и module NBT, проверяет наблюдение предметов
положительным контролем и сама сохраняет/останавливает сервер. Это проверка
onRemove, отдельно от естественного transport/save/reopen. Оригинальный oracle
проверяет также creative FakePlayer; настоящий creative player в Horizon ещё
не проверен.

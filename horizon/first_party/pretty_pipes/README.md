# Native Pretty Pipes transport prototype 0.1.0

Первый частичный промышленный перенос: Rust-код перемещает предметы между
контейнерами по pipe blocks и сохраняет партии в пути. Источник поведения —
Pretty Pipes 1.22.0, MIT tag `1f8ac61`; оригинальный серверный эталон описан в
[PRETTY_PIPES_REFERENCE_RU.md](../../PRETTY_PIPES_REFERENCE_RU.md).
Это не полный порт Pretty Pipes и не готовый промышленный модпак.

Четыре HEAD-хука создают и тикают `prettypipes:pipe`, регистрируют его внутренний
контейнер и вызывают отдельный routing module в `game.rs`. Используются штатные
Horizon `native_container_slots`, `native_extract_item`, `native_insert_item`.
Очередь хранит настоящие ItemStack в 64 внутренних слотах block entity;
назначение и оставшаяся задержка — в сохранённом NBT. Внешние hopper faces
внутренней очереди закрыты. Глобального несохраняемого списка предметов нет.

Для default extraction modules реализованы исходные batch/period tiers:
low 1/20, medium 8/15, high 64/10. Устанавливать их в тестах пока можно только
через `modules.Items` в NBT; обычное использование предмета и GUI ещё не перенесены.
Поиск — ограниченный BFS по загруженным pipe blocks (4096 nodes), с исключением
исходного контейнера. Доставка имеет приближённую задержку 20 ticks на pipe;
покадровое движение, точный timing и отрисовка предметов не реализованы.
Если путь или место в цели недоступны, партия остаётся во внутренней очереди.
Полные правила переполнения, rerouting и удаления труб ещё требуют проверки.

## Настоящая серверная проверка

Horizon 26.3, семь content-модулей, три скомпилированных native bundles,
loopback/online-mode/whitelist, без игроков. Все original controls повторены:

- без extraction module восемь слитков остаются в исходном сундуке;
- low module доставляет все восемь;
- разорванная средняя труба прекращает извлечение;
- high module оставляет партию в пути перед save/stop, после reopen все восемь
  доставляются без создания новых предметов и без дублирования.

После проверок сервер штатно остановлен, installation lock повторно проверен.
108 Python-тестов прошли. [Результат](../../PRETTY_PIPES_RUNTIME_RESULT.json).
Клиент, normal player interaction, crafting, фильтры, приоритеты и ветвления
не проверены. Успех этого fixture не объявляет весь Pretty Pipes `ported`.

## Сборка и установка

Собирать вместе с двумя ранее проверенными native-модулями через pinned Mixins
`5a64af9` для Horizon `c78187d`, как описано в
[wolf extension](../terralith_wolves/README.md). Для всех трёх bundles получается
семь HEAD injections и два support modules. Только headless engine; отдельного
клиентского запуска эта команда не проверяет.

Содержимое `.hnmod`: корневой `horizon-native.json` и в
`mixins/techquest_pretty_pipes/` файлы `horizon-mixin.toml`, `create.rs`,
`ticking.rs`, `container.rs`, `tick.rs`, `logic.rs`, оба LICENSE-файла.
Выполнить SDK-check и объявить SHA-256 source bundle в новой папке native-tools.
Движок, bundles и build-result.json устанавливаются совместно и фиксируются lock.

Content собирается отдельно из проверенного исходного JAR:

```bash
python horizon/tools/stage_pretty_pipes.py \
  --jar /path/to/PrettyPipes-1.22.0-all.jar \
  --sdk /path/to/cargo-horizon-mod \
  --output /path/to/new-pipe-content
```

Он регистрирует pipe block с соединяющейся геометрией и четыре module/material
items; копирует пять исходных MIT textures. Рецепты не переносятся. Изменение
лицензионного notice после runtime-теста затронуло только комментарии manifest:
остальные payload bytes и разобранные TOML поля проверены на идентичность;
оба варианта SDK-валидны. Хеши обоих вариантов явно сохранены в runtime-отчёте.

Вызвать обычный [установщик](../../LOCAL_INSTALL_RU.md), добавив
`--pretty-pipes /path/to/new-pipe-content/target/horizon-mod/prettypipes.hmod`.
Он требует SDK-valid content версии 0.1.0 и объявленный native bundle
`techquest_pretty_pipes`, а verify продолжает принимать старые шестимодульные
установки. Произвольный седьмой мод не допускается. Старые profiles/locks не менять.

В новой установке выполнить `probes/live_pretty_pipes.py --server-dir ...
--phase prepare --output /path/to/new-prepare.json`, затем после штатной остановки
повторно запустить установщиком тот же мир с новыми homes и выполнить `--phase verify`.
Prepare размещает fixture и сам сохраняет/останавливает сервер; verify читает
существующий fixture и проверяет доставку, не создавая новые слитки.

MIT copyright/permission сохранены в `LICENSE-PRETTY-PIPES`, `LICENSE-HORIZON`
и [общем notice](../../THIRD_PARTY_NOTICES.md). Чужие игровые ресурсы и JAR
не включены в репозиторий; local content hmod включает copyright/license
как комментарии manifest. Ничего не публиковалось.

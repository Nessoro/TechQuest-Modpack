# Native Pretty Pipes prototype 0.6.0

Прототип Horizon 26.3 поддерживает default extraction tiers, пять рецептов,
установку/снятие модуля, главное меню и базовые фильтры экстрактора. Источник —
Pretty Pipes 1.22.0, MIT commit `1f8ac61`.
[Оригинальный эталон](../../PRETTY_PIPES_REFERENCE_RU.md),
[проверки 0.2](../../PRETTY_PIPES_MODULES_RESULT.json),
[проверки меню 0.3](../../PRETTY_PIPES_MENU_RESULT.json),
[фильтры и стороны 0.4](../../PRETTY_PIPES_FILTER_RESULT.json),
[вместимость и очереди 0.5](../../PRETTY_PIPES_CAPACITY_RESULT.json),
[автоматизация Oritech 0.6](../../ORITECH_PIPES_RESULT.json).
Полный Pretty Pipes и промышленный модпак ещё не перенесены.

## Главное меню и хранение

Три первых физических слота block entity принадлежат модулям, следующие 64 —
партиям в пути. Menu type `prettypipes:pipe` имеет 67 сетевых слотов плюс
инвентарь игрока; native screen показывает только первые три. Остальные получают
`Role::Hidden` и на сервере: pickup, shift-click, swap, throw и pickup-all
не могут взять транспортируемые предметы через меню.

RETURN-вставка в настоящий `Menu::mod_slot` ограничивает module slots одним
предметом, принимает только реализованные extractors и проверяет совместимость
по текущему инвентарю. Low/medium/high extractors несовместимы между собой;
blank material и обычные предметы отклоняются. Остальные menu types не меняются.
Координаты трёх слотов и инвентаря взяты из исходного MainPipeContainer;
используется обычная панель Horizon с переводимыми названиями.

Пустая основная рука открывает меню у трубы с соседним инвентарём. Предмет
модуля устанавливает один extractor; расходуется один предмет и в creative,
как в оригинале. Вариант геометрии на основе chorus plant сам не создаёт
vanilla OpenMenu effect, поэтому отдельный обработчик сохраняет порядок
right-click hooks и открывает только меню нашей трубы. Таблица ModContainer
подготавливается до первого block-entity tick, если её ещё нет: первая попытка
открытия работает и при замороженном мире, без продвижения симуляции.

Физические module slots — владелец предметов. Исходный `modules.Size/Items`
сохранён как NBT view со snapshot: явно изменённый NBT импортируется один раз,
изменения меню записываются обратно при следующем тике/взаимодействии. Сохранение
между кликом и следующим тиком сохраняет физические слоты; старый view не
восстанавливает снятый модуль. Старый формат 0.2 преобразуется один раз:
очередь и её pending metadata сдвигаются на три слота. Новые сущности помечены
`techquest_inventory_schema=3`. Неизвестный формат не чинится с потерей предметов.

При замене/разрушении загруженной трубы physical module slots и очередь
передаются обработчику выпадения один раз; NBT view не становится второй копией
инвентаря. Проверены сохранность компонентов и отсутствие дублирования.

## Фильтр экстрактора и стороны (0.4)

Под module slots показаны 3/6/9 ячеек-образцов low/medium/high extractor.
Взять предмет на cursor и нажать ячейку — скопировать один образец; нажатие
пустым cursor очищает его. Реальный стек остаётся у игрока. Образцы хранятся
в компоненте модуля, не в физических slot inventories; при снятии модуля они
не превращаются в дополнительные предметы.

Кнопка `D`/`A` переключает исходные deny/allow: blacklist запрещает выбранные
предметы, whitelist разрешает только выбранные. Пустой blacklist пропускает всё,
пустой whitelist ничего. Базовое сравнение, как в оригинале без equality modules,
учитывает ID предмета; count/damage/components образца сохраняются, но не участвуют
в этом сравнении. Кнопка стороны перебирает соседние инвентари в исходном порядке
Down/Up/North/South/West/East/All Sides. Извлекающая сторона не становится целью
доставки. С выбранной стороной одна труба может передавать в инвентарь с другой
стороны; у default All Sides все соседние инвентари считаются источниками.

Используются исходные component IDs `prettypipes:item_filter_data` и
`prettypipes:direction_selector_data`, зарегистрированные в нативном протоколе.
Для значков передаётся 21 data slot: состояние и пары 16-bit частей item index;
сам образец со всеми компонентами остаётся в модуле. Content menu обязан объявить
`slots=67, data_slots=21`; установщик отказывает SDK-валидному 0.4 модулю без
этих data slots, иначе настройки не будут видны клиенту.

Исходные `ItemFilter`, `FilterSlot`, `DirectionSelector` исполнялись на отдельном
NeoForge с синтетическим игроком: 27 последовательных состояний, 108 item checks,
162 direction checks, cursor counts и sample counts совпали. Компоненты сверены
с **прямыми исходными Data.CODEC**, без кеша DataComponentType: в 18 состояниях
оригинальный кеш сериализации держит прежний образец, хотя runtime-фильтр уже
использует новый. Это наблюдение сохранено отдельно. Horizon сериализует последний
выбранный образец; его сохранение после реального перезапуска проверено отдельно.

Графический локальный клиент проверил оба режима, замену образца и передачу
в обе стороны через одну трубу, сохранение/повторную установку модуля и отсутствие
потерь/дублирования. Для всех трёх tiers проверены первая/последняя ячейки,
очистка и возврат единственного модуля без выдачи предметов-образцов. Для этих
кликов используется ContainerButtonClick с действительным cursor stack на сервере;
обычные module slots продолжают использовать ContainerClick.

Текущая панель объединяет основные slots и настройки реализованного extractor;
полная исходная система tabs и экраны остальных модулей не перенесены.
Английские подписи и доступные русские ключи взяты из MIT JAR; отсутствующие
в исходном ru_ru ключи используют обычный английский fallback.

## Вместимость и партии в пути (0.5)

Маршрут теперь вычисляет реальную доступную вместимость через read-only
правила вставки pinned Horizon: доступные стороне slots, тип/компоненты стека
и ограничения furnace input/fuel. Предметы не вставляются и не забираются
ради расчёта. Поддержаны те же обычные инвентари, что перечислены в connection
теге: chest/trapped chest/barrel, hopper, furnace/blast furnace/smoker.
Иные inventory kinds и межмодовые handlers требуют отдельного переноса.

Из источника забирается только количество, помещающееся в цель. Для medium/high
из вместимости вычитаются все партии, уже направленные в эту координату
инвентаря, включая другие типы предметов — исходная консервативная эвристика
Pretty Pipes. Low не вычитает партии в пути, как в оригинале. Текущая тикающая
труба находится вне общей block-entity map, поэтому её собственная очередь
учитывается явно. Резерв получается из реальных сохранённых queue slots и
pending destination; отдельного несохранённого счётчика нет.

Проверены 126 исходных capacity cases: 96 chest (включая шесть component cases),
18 hopper и 12 furnace. По 42 случая на каждый tier; запросы 1/8/64, свободное
место 0/1/2/8/64 и партии в пути 0/1/8. Оригинальный public destination method
исполнялся на NeoForge. На Horizon каждый случай исполнил ровно один период
настоящего extraction tick с отдельным источником и синтетической очередью
другой трубы. Уменьшение источника равно новой партии; Items цели до прибытия
не меняются. Старый 0.4 движок расходился в 51 случае, 0.5 совпал во всех.
Это не проверка полного исходного network timing, priorities или rerouting.

Графический локальный клиент без подставных queue entries установил два high
extractors к общей цели с тремя свободными местами: суммарно отправлены ровно
три предмета. Отдельный medium extractor при десяти свободных местах отправил
8 + 2 и остановился, учитывая собственные партии. Оба мира сохранены с реальными
партиями в пути и после перезапуска доставили их без потерь/дублирования.
Регрессия фильтров, обычный dedicated transport/save/reopen и удаление трубы
также прошли. [Отчёт 0.5](../../PRETTY_PIPES_CAPACITY_RESULT.json).

Остаются insertion-limiting modules, сложные/межмодовые slot limits,
oversized stack components, aliases double chest при резервировании,
полная семантика ветвлений/приоритетов и перерасчёт пути при изменении цели.
Для обычных поддержанных инвентарей повторно проверены базовые оба режима
фильтра и directional single-pipe routing. Старые установки не изменялись.

## Генератор и печь Oritech (0.6)

Версия 0.5 отклоняла эти цели в read-only расчёте вместимости, поэтому наличие
их native container само по себе не давало автоматической подачи. В 0.6
`capacity.rs` дополнительно принимает `oritech:basic_generator_block` и
`oritech:powered_furnace_block`, только с настоящим `Kind::Mod`. Слоты, стороны,
входные ограничения, stack components и acceptance hooks проверяются прежним
путём движка. Выходной слот печи не становится входным. Прочие mod handlers
не объявляются поддержанными.

Оба ID добавлены в connection tag как optional: без Oritech контент сохраняет
семь ванильных связей, с ним получает девять. Модель теперь рисует соединения
с машинами. Новые content/native bundles имеют одинаковую версию 0.6.0;
установщик отказывает паре 0.6 content / 0.5 native. Формат очереди, 67 slots,
21 data slot и рецепты не изменены; старые tools/profiles/locks сохраняются.

Новый dedicated сценарий и графический клиент проверили три раздельные линии:
подачу угля, подачу сырья и вывоз слитков. Из 16 raw iron и одного coal
получены 16 ingots, остаток энергии — ноль. Груз из восьми настоящих слитков
сохранён в пути и доставлен после физического перезапуска. При снятом core
экстрактор не забирает сырьё из input slot. Полная бочка останавливает новую
партию в печи; освобождение одного filler-slot возобновляет доставку. Финальные
предметы и состояние проверены ещё одним физическим перезапуском.

Графический клиент установил все три extractor обычным взаимодействием,
открыл меню и подтвердил connection states и ноль protocol decode errors.
Машины, initial assembly, трубы, исходные chest inventories и stone filler
были fixtures; energy, processing output и transport cargo не подставлялись.
Это отдельная проверка от добытого starter-пути, не unassisted survival.
126 исходных vanilla capacity cases совпали без расхождений; 121 Python-тест
прошёл. [Доказательства и границы](../../ORITECH_PIPES_RESULT.json).

`live_oritech_pipes.py` имеет фазы `prepare`, `verify`, `final`: перед каждой
запустить новый изолированный профиль, передать новую `--output`, а для двух
последних — предыдущий отчёт через `--prior`. Каждая фаза останавливает сервер.
`live_oritech_pipes_gui.py --server-dir "$TASK_SERVER" --work NEW_WORK`
запускается с X11/Vulkan и сам сохраняет/открывает свой отдельный мир. Online
join лицензированным клиентом и полная исходная capability parity не проверены.

## Транспорт и ограничения

Default tiers сохраняют batch/period: low 1/20, medium 8/15, high 64/10.
Loaded-only BFS ограничен 4096 pipe nodes, исходный контейнер исключается.
Задержка приближённая — 20 ticks на pipe. При недоступной цели партия остаётся
в сохранённой очереди. Внешние hopper faces внутреннего инвентаря закрыты.

Не реализованы equality/filter-increase modules и их экраны, приоритеты,
полная семантика ветвлений/переполнения/rerouting, insertion-limiting modules,
redstone module и IPipeConnectable interop. Компонент фильтра должен иметь
исходный размер соответствующего tier; расширенные или malformed configs
отклоняются с остановкой извлечения, без удаления сохранённых данных.
Не проверены точные позиции, скорость и pickup delay выпавших предметов,
explosion-specific drops, bulk edits и удаление ещё не загруженной сущности.

## Проверки

- Оригинальный MainPipeContainer на отдельном NeoForge: 20 операций с
  синтетическим FakePlayer — вставка, снятие, оба клика, shift-click, hotbar swap,
  выбрасывание и отказы для неверных предметов. Сравниваются все три модуля,
  36 inventory slots, cursor, dropped items, custom-data marker и очередь.
- Настоящий Horizon Menu engine со скомпилированной RETURN-вставкой повторяет
  все 20 операций. Пять обращений к hidden slot блокируются; те же операции
  на видимом слоте срабатывают как положительные контроли.
- Восемь Rust-тестов codec/ownership: оригинальные count defaults, расход,
  компоненты, перенос старой очереди/pending NBT, однократное выпадение,
  сохранение снятия до следующего тика и явное изменение NBT view.
- Stock command harness запускает настоящий интегрированный сервер и
  подключённого headless-владельца. Через UseItemOn проверены все три tiers,
  survival/creative, отказ второму extractor, отсутствие меню при установке,
  открытие/закрытие пустой рукой, сохранение модуля после закрытия и отказ без
  соседнего инвентаря. Это синтетический локальный клиент, не Microsoft login.
- Отдельный dedicated profile с семью hmod и тремя native bundles повторяет
  transport/save/reopen и удаление трубы по независимому оригинальному эталону.
  Пять рецептов сверены на 22 успешных и 44 отрицательных сетках; pipe loot table
  реально выдаёт одну трубу. 109 Python-тестов проходят.
- Графический локальный клиент отрисовал окно в Xvfb через программный Vulkan
  llvmpipe. Координатный клик мышью и ContainerClick проверяют снятие на cursor,
  перенос в inventory, Shift-click в обе стороны, отказ второму extractor,
  закрытие/повторное открытие. Survival-установка расходует один из двух модулей;
  итоговые два предмета сохраняются, protocol decode errors = 0. Снимки остаются
  только в scratch runtime; их SHA-256 записаны в отчёт.
- Настоящий мир 0.2 с восемью предметами в пути открыт новой установкой 0.3:
  партия доставлена ровно один раз, module slot мигрирован, разрушение выдаёт
  один модуль и одну трубу. Пользовательские player files и locks не копировались.

Графическая проверка использует отдельного локального игрока без Microsoft
login и программный рендерер. Настоящий offhand player flow, аппаратная GPU,
звук и подключение лицензированного клиента к online-mode dedicated server
ещё требуют проверки. Configuration screens прочих модулей не реализованы.

## Сборка и установка

Собирать все три native modules через Mixins `5a64af9` для Horizon `c78187d`,
как в [wolf extension](../terralith_wolves/README.md). Итого 18 HEAD-вставок,
одна RETURN и шесть support modules. Native bundle содержит корневой
`horizon-native.json`, а в `mixins/techquest_pretty_pipes/` — TOML, все 21 `.rs`
из этой папки и оба LICENSE-файла. SDK-check и SHA-256 bundle/engine обязательны.

```bash
python horizon/tools/stage_pretty_pipes.py \
  --jar /path/to/PrettyPipes-1.22.0-all.jar \
  --neoforge-jar /path/to/neoforge-21.1.264-universal.jar \
  --sdk /path/to/cargo-horizon-mod \
  --output /path/to/new-pipe-content
```

Ассемблер проверяет оба пина, переносит пять recipes, преобразует loot condition
`condition` → `type`, копирует пять MIT textures, названия и доступные подписи настроек на английском
и русском. Исходный `c:glass_blocks` заменяется частным alias с 18 vanilla
members минимального исходного сервера; стекло остальных модов не реализовано.
Из NeoForge читается только public tag JSON, Java source не читается/не копируется.
Полный MIT notice включён в hmod.

[Установщик](../../LOCAL_INSTALL_RU.md) принимает дополнительный
`--pretty-pipes /path/to/prettypipes.hmod` и требует совпадающую версию native
bundle (0.1/0.2/0.3/0.4/0.5). Уже установленные profiles, tools и locks не редактировать.

Проверки на новых scratch-путях, вне Git checkout и пользовательских миров:

```bash
python horizon/probes/live_pretty_pipes_game.py \
  --server-dir /path/to/verified-isolated-server --work /path/to/new-game-harness
# Нужны X11 display и Vulkan/OpenGL driver; допускается Xvfb + llvmpipe.
xvfb-run -a python horizon/probes/live_pretty_pipes_filter.py \
  --server-dir /path/to/verified-server --work /path/to/new-filter-world
xvfb-run -a python horizon/probes/live_pretty_pipes_filter_layout.py \
  --server-dir /path/to/verified-server --work /path/to/new-layout-world
python horizon/probes/live_pretty_pipes.py \
  --server-dir /path/to/running-server --phase prepare --output /path/to/new-prepare.json
# Prepare сохраняет/останавливает сервер. Запустить тот же мир с новыми homes.
python horizon/probes/live_pretty_pipes.py \
  --server-dir /path/to/running-server --phase verify --output /path/to/new-verify.json
python horizon/probes/live_pretty_pipes_removal.py \
  --server-dir /path/to/running-server --original /path/to/removal-oracle.json \
  --output /path/to/new-removal.json
```

`PrettyPipesMenuProbe.java` — отдельный developer-only NeoForge mod с ID
`techquest_reference_probe`, как `PrettyPipesInteractionProbe.java` в проверке
0.2. JDK 25, `--release 21 -proc:none`, mapped Minecraft `*-srg.jar` первым в
classpath, затем NeoForge libraries без `*-slim.jar`/`*-unpacked.jar`, затем
Pretty Pipes JAR. Запускать только с оригинальным Pretty Pipes в новом
loopback/online-mode/whitelist reference server, с отдельными homes и миром
`techquest-reference-*`. `techquest.reference.result` задаёт новый JSON.
Синтетическая pathless queue очищается перед сохранением; oracle штатно
останавливает сервер. Java для Horizon runtime не требуется.

`pretty_pipes_menu.rs` связывается с client-lib/items/world библиотеками того же
native build. Аргументы: effective content root, menu declaration JSON,
извлечённый из установленного locked hmod, original menu oracle JSON.
`pretty_pipes_crafting.rs` принимает root, original cases JSON и interaction
oracle JSON. Входы крафта генерирует `pretty_pipes_crafting_cases.py`.
Для Rust unit tests включить `modules.rs` через `#[path]` в scratch example
`horizon-items`; задать `TQ_PRETTY_PIPES_INTERACTION_ORACLE` на interaction oracle.

Атрибуция — LICENSE-файлы и [notice](../../THIRD_PARTY_NOTICES.md).
Игровые JAR, hmod, textures, prepared resources, логи и миры в Git не включены.

`PrettyPipesFilterProbe.java` собирается как остальные developer-only oracle mods.
Он использует исходные MIT классы Pretty Pipes и публичные бинарные APIs NeoForge;
LGPL Java source не читается. `pretty_pipes_filter.rs` связывается с client-lib,
items/world и serde_json **той же новой native сборки** и принимает original
filter-result JSON. Проверяется прямой исходный codec, а cached module snapshots
сохраняются для отдельного учёта описанного расхождения.

`PrettyPipesCapacityProbe.java` — developer-only original destination oracle;
для компиляции дополнительно нужны вложенные binary JAR dependencies из
Pretty Pipes JAR (Java source зависимостей не читается). Все синтетические
PipeItems удаляются до сохранения. Результат задаётся через
`techquest.reference.result`, как у других oracle mods.

```bash
python horizon/probes/live_pretty_pipes_capacity.py \
  --server-dir /path/to/verified-05-server --work /path/to/new-capacity-harness \
  --original /path/to/original-capacity-result.json
# Контроль прежнего SDK-valid 0.4 движка: отдельный --work и --baseline.
xvfb-run -a python horizon/probes/live_pretty_pipes_capacity_gui.py \
  --server-dir /path/to/verified-05-server --work /path/to/new-capacity-gui-world
```

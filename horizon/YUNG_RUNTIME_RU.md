# YUNG's: структуры, спавнеры, сундуки и лут

Проверка 15 ноября 2026 года использует Horizon 26.3 `c78187d` и отдельный
исходный сервер Minecraft 1.21.1 / NeoForge 21.1.264. Оба сервера привязаны
к loopback, с online-mode и whitelist, без игроков. Игровые JAR, шаблоны,
производные hmod, миры и журналы остаются вне репозитория.

## Что работает и что ещё отсутствует

Реальный decoder распознаёт **4 из 20** исходных определений структур:
малое, zombie и skeleton подземелья Better Dungeons, stronghold Better Strongholds.
Все четыре размещены командой `/place structure`; из 225 кандидатов шаблонов
после processors/перекрытий сохранились 208 ожидаемых блоков. Среди них прочитаны
24 спавнера и 179 ссылок на loot tables. Наблюдения совпали после save/reopen.
Кандидат — блок до обработки, поэтому отсутствие остальных 17 само по себе
не доказывает дефект размещения.

**16 определений не исполняются:** 13 процедурных mineshafts, spider dungeon,
small Nether dungeon и fortress. Fortress использует `yungsapi:yung_jigsaw`
с глубиной 46; общий native decoder отвергает её из-за vanilla-предела 20.
Обрезать глубину или подменять процедурные шахты vanilla-структурами нельзя.
Также не перенесены все YUNG conditions, enhanced terrain и custom processors.
Четыре распознанных вида не означают полной поддержки четырёх модов.

Классификация видов использует пустой biome resolver и не проверяет biome gates.
Раскладки строятся полным GeneratorData, затем отдельно проверяются настоящим
сервером. Естественная генерация, открытие сундуков внутри сгенерированных
структур и активация спавнеров пока не проверены. Отдельные loot tables открыты
локальным графическим клиентом 16 ноября; область этой проверки описана ниже.

## Исправленные спавнеры малых подземелий

До исправления контрольный спавнер `[128,-7,128]` оставался со свиньями;
исходный NeoForge создавал там скелетов. Carry отбросил
`betterdungeons:mob_spawner_processor` из трёх processor lists.
Новый адаптер читает публичные JSON из проверенного исходного JAR, сохраняет
carried vanilla rules и восстанавливает фиксированный выбор skeleton/spider/zombie
через существующий `horizon:spawner_mobs`.

У pinned native processor есть дополнительная проблема: он создаёт NBT без
`id` блочной сущности. Следующее vanilla rule с `append_static` добавляет
`minecraft:mob_spawner`, сохраняя short-поля и SpawnData/SpawnPotentials.
Без этого дополнения реальная команда `data get block` не видела блочную сущность.

Оригинальный сервер проверен как работающий black-box, без чтения или декомпиляции
LGPL Java-кода. 17 точек с seed 263 охватывают три вида мобов. Сравниваются
моб, единственный SpawnPotential и семь числовых полей каждого спавнера.
Все 17 мобов, 119 числовых полей и SpawnPotentials совпали; повторное чтение
после save/reopen сохранило результат. 96 Horizon Python-тестов прошли.
На первом этапе это оставляло 30 других processors отброшенными. Контрольная
раскладка сохраняла девять native container-кандидатов вместо трёх оригинальных.
Следующий этап восстанавливает три chest processors; остаются 27 других.
RNG trace и геометрическая/декоративная идентичность всего dungeon не подтверждены.
Спавнеры zombie/skeleton больших подземелий этим адаптером не исправляются.

## Ограничения сундуков

`stage_yung_dungeons.py` теперь восстанавливает также
`betterdungeons:small_dungeon_chest_processor` через `horizon:count_cap`.
Используются исходные defaults: min=1, max=2, chance=0.2; лишний сундук становится
`minecraft:cave_air`. Ограничение относится к шаблону с этим processor list;
loot-pile templates и бочки не получают искусственного общего лимита на dungeon.
Изменённые пользовательские min/max этим адаптером не импортируются.

Для правильной области подсчёта нужен второй нативный bundle
[TechQuest YUNG Dungeons](first_party/yung_dungeons/README.md). Pinned engine
обрабатывает обычный CountCap после предварительного chunk clipping: гарантированный
минимум повторяется в каждом чанке. Один HEAD-hook включает обработку всего шаблона
для CountCap; финальная запись по-прежнему ограничена chunk bounding box.
Остальные processors сохраняют исходное решение engine.

На 17 подземельях исходный NeoForge сохранил 46 из 142 container-кандидатов:
28 сундуков, 18 бочек; остальные 96 позиций — cave_air. Обычный native CountCap
оставлял 93, с 47 расхождениями. С нативным расширением все 142 позиции и
46 loot table IDs совпали; прежние 17 спавнеров также сохранили совпадение.
Весь набор совпал и после save/reopen; итоговый installation lock проверен.
98 Python-тестов прошли. [Текущий отчёт](YUNG_CHEST_RUNTIME_RESULT.json).
Выдача предметов при открытии контейнера игроком остаётся непроверенной.

## Воспроизведение локальной сборки

После подготовки шести исходных content-модулей:

```bash
python horizon/tools/stage_yung_dungeons.py \
  --work /path/to/five-together \
  --jar /path/to/YungsBetterDungeons-1.21.1-NeoForge-5.1.4.jar \
  --sdk /path/to/cargo-horizon-mod \
  --output /path/to/new-dungeons-content
```

Адаптер требует SHA-1 `73a660c13063450e555e5e2c015ae24d606b32b4`, сверяет
carried rules с исходными и отказывает при неизвестных полях spawner processor.
Выходной каталог должен быть новым, вне исходников, миров и prepared resources.
SDK собирает и проверяет отдельный Better Dungeons hmod с прежним ID/версией.
Источник не меняется; полный перенос мода не декларируется.

Скопировать исходные шесть hmod в **новую** папку и заменить там только
`betterdungeons.hmod` файлом из `new-dungeons-content/target/horizon-mod/`.
Передать эту папку как `--modules` существующему
[изолированному установщику](LOCAL_INSTALL_RU.md). Terralith hmod/datapack и
нативный wolf bundle остаются обязательными входами текущей тестовой сборки.
Установщик фиксирует изменённый hmod по SHA-256; менять уже установленный payload
или lock для такого обновления нельзя.

`probes/yung_structures.rs` — first-party пример для pinned `horizon-world`:
он читает effective content root и Terralith datapack и пишет новый JSON-план.
Необязательный четвёртый аргумент `small-dungeons` планирует 16 дополнительных
точек. Для полного набора текущего теста к ним добавлена первая контрольная точка
обычного четырёхструктурного плана. Проба не размещает блоки.

На отдельном исходном NeoForge сервере с этими уже размещёнными структурами:

```bash
python horizon/probes/reference_yung_spawners.py \
  --server-dir /path/to/reference-server \
  --plans /path/to/small-dungeon-plans.json \
  --output /path/to/new-original-observations.json
```

Для размещения в новом reference scratch world добавить `--place`. RCON слушает
loopback; пароль хранится только в приватном server.properties. Проверяются EULA,
online-mode, whitelist, имя тестового мира и отсутствие подключённых игроков.
Секреты и полный NBT не попадают в отчёт. Ответы больше одного RCON packet
отклоняются; для короткого spawner NBT этого достаточно.

После явного размещения структур Horizon, forceload всех chunks bounding box
и ожидания их загрузки:

```bash
python horizon/probes/live_yung_structures.py \
  --binary /path/to/horizon-server \
  --server-dir /path/to/isolated-horizon-server \
  --plans /path/to/small-dungeon-plans.json \
  --reference /path/to/new-original-observations.json \
  --output /path/to/new-native-observations.json
```

Для сравнения контейнеров сначала запустить `probes/reference_yung_containers.py`
на исходном NeoForge с теми же `--server-dir`, `--plans`, `--output`. Проба проверяет
default min/max в конфигурации, читает каждый container-кандидат и классифицирует
удалённые блоки как air/cave_air. Передать полученный файл native-пробе через
`--reference-containers /path/to/original-container-observations.json`.
Непустой `container_comparison.mismatches` приводит к ненулевому exit status.

Эта проба только читает мир. Нулевой exit status вместе с пустым
`original_comparison.mismatch_positions` подтверждает совпадение наблюдений.
Для проверки сохранения выполнить `save-all flush`, штатно остановить сервер,
повторно запустить установщиком и повторить чтение без размещения структур.
Первый этап структур/спавнеров: [YUNG_RUNTIME_RESULT.json](YUNG_RUNTIME_RESULT.json).
Текущая проверка ограничений: [YUNG_CHEST_RUNTIME_RESULT.json](YUNG_CHEST_RUNTIME_RESULT.json).

## Лут: игровой клиент и исправление компонентов (16 ноября)

[Отчёт](YUNG_LOOT_RUNTIME_RESULT.json). В семи установленных content-модулях
нашлось 27 таблиц YUNG's: 8 Better Dungeons, 10 Better Strongholds и 9 Better
Fortresses. Mineshafts не добавляет собственных таблиц. `condition`/`function`
уже преобразованы прежним carry; повторная миграция схемы не потребовалась.

Найдена другая несовместимость: native holder lookup не дописывает `minecraft:`
к коротким enchantment IDs, а `set_components` с ключом `potion_contents`
сохраняет неизвестный компонент вместо игрового potion value. Это давало обычные
книги/меч без ожидаемых чар и зелья/стрелы без нужного эффекта.

`stage_yung_dungeons.py` теперь сверяет все восемь carried таблиц с публичными
JSON закреплённого JAR, явно дописывает namespace девяти enchantment references
и преобразует 18 одиночных potion patches в поддерживаемый Horizon
`minecraft:set_potion`. Значение исходного зелья и порядок остальных функций
сохранены. Сложные/условные patches отклоняются для отдельного разбора.
Меняются только пять loot tables; остальные члены hmod, включая восстановленные
spawner/chest processors, побайтно равны прежнему модулю.

Оригинальный сервер NeoForge исполнил публичные loot codec/functions на 23
изолированных исходных entries с seed 1, 263 и 987654321. Сравнивались ID,
count, damage, все чары и potion ID. В прежнем native модуле все 69 rolls
расходились с эталоном; после адаптации все совпали. Это проверка конкретных
entries, а не полного RNG trace всех таблиц между версиями Minecraft.

Настоящий графический клиент Horizon открыл все 27 таблиц в отдельных fixture
сундуках, увидел предметы и проверил точные слоты/компоненты после save/reopen.
Сохранённый LootTable marker исчезает после открытия; неизвестная таблица даёт
пустой контроль в обоих запусках. Horizon может заранее вычислять roll при
загрузке и хранить marker до открытия — момент вычисления RNG этим тестом
не утверждается. В зафиксированном seed наблюдались четыре potion stacks и
девять stacks с чарами; protocol decode errors = 0.

Использованы Xvfb и программный Vulkan, отдельный локальный игрок и новый мир.
Это не Microsoft login, не join dedicated server и не открытие лута внутри
естественно сгенерированной структуры. Новая loopback/online/whitelist
server installation с исправленным модулем отдельно запущена, ответила на команду,
штатно остановлена и прошла проверку lock. Старые profiles/hmod/locks сохранены.
112 Python-тестов прошли.

Воспроизведение после сборки нового модуля и установки в новый профиль:

```bash
xvfb-run -a python horizon/probes/live_yung_loot.py \
  --server-dir /path/to/new-verified-server --work /path/to/new-graphical-loot-world
python horizon/probes/yung_loot_cases.py \
  --jar /path/to/pinned-original-betterdungeons.jar \
  --module /path/to/new-betterdungeons.hmod --output /path/to/new-cases.json
```

`YungLootModifierProbe.java` — собственный developer-only NeoForge mod с ID
`techquest_reference_probe`, собираемый как Pretty Pipes oracle. Свойства
`techquest.reference.cases` и `techquest.reference.result` задают scratch JSON;
новый reference server с исходными модами останавливается после пробы.
Java source оригинальных LGPL модов не читается и не декомпилируется.
`yung_loot_modifiers.rs` связывается с world/core/serde_json библиотеками той же
native сборки; аргументы — effective content root, cases JSON и original result.
Для контрольного старого hmod передать четвёртым аргументом `baseline`:
в этом режиме ожидаются ровно 69 воспроизведённых несовпадений.

# YUNG's: структуры и восстановление спавнеров

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
сервером. Естественная генерация, открытие сундуков игроком и активация спавнеров
пока не проверены. Ссылка LootTable в NBT не доказывает выдачу предметов.

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
Это частичное исправление: RNG trace и геометрическая/декоративная идентичность
всего dungeon не подтверждены. В тех же трёх списках остаются 30 отброшенных
других processors. Например, в контрольной раскладке native оставляет девять
container-кандидатов, оригинал — три; chest limits ещё требуют переноса.
Спавнеры zombie/skeleton больших подземелий этим адаптером не исправляются.

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

Эта проба только читает мир. Нулевой exit status вместе с пустым
`original_comparison.mismatch_positions` подтверждает совпадение наблюдений.
Для проверки сохранения выполнить `save-all flush`, штатно остановить сервер,
повторно запустить установщиком и повторить чтение без размещения структур.
Результаты этапа: [YUNG_RUNTIME_RESULT.json](YUNG_RUNTIME_RESULT.json).

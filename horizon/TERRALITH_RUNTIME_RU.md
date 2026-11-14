# Terralith: локальная миграция генератора 1.21.1 → 26.3

**Частичный перенос, не готовый модпак.** Подтверждён запуск отдельного сервера
Horizon с шестью `.hmod` и дополнительным локальным datapack Terralith.
Естественный биом `terralith:arid_highlands` в чанке `[-142, 142]` проверен
командой `execute if biome`, затем повторно после сохранения и перезапуска.
Контрольный золотой блок также сохранился. Сервер штатно остановлен.

Продолжение 13 ноября: перенесены настройки почвы деревьев и синхронизирован
производный `.hmod`. Пропуски placed features снижены **с 246 до 140**.
Три дерева с проверкой почвы действительно размещены командой в новом мире;
стволы и почва сохранились после перезапуска. [Результат этого этапа](TERRALITH_TREE_RUNTIME_RESULT.json).

Продолжение 14 ноября: исправлены 23 старые записи disk-provider и 93 записи
параметров noise-provider. Пропуски placed features снижены **со 140 до 77**.
В 384 пробах с синтетической палитрой выбор блоков совпал с оригиналом 1.21.1.
Подзол и семь состояний снега размещены на сервере и проверены после перезапуска.
[Результат providers](TERRALITH_PROVIDER_RUNTIME_RESULT.json).

Следующий этап 14 ноября: 59 конфигураций `random_patch`/`flower` заменены
композициями; пропуски снижены **с 77 до 22**, новых отказов нет. В 640 пробах
совпали координаты всех 11 520 попыток, результат и следующий random draw.
Трава, ландыш и белый тюльпан размещены и проверены после перезапуска сервера.
[Результат patches](TERRALITH_PATCH_RUNTIME_RESULT.json).

Тест выполнен 10 ноября 2026; после восстановления среды 13 ноября его
сохранённые результаты и SHA-256 всех выбранных исходных файлов проверены.
Машиночитаемый результат: [TERRALITH_RUNTIME_RESULT.json](TERRALITH_RUNTIME_RESULT.json).

## Какие несовместимости исправлены

`tools/prepare_terralith_worldgen.py` собирает только локальный пробный datapack
из `carry` и `outside` **Terralith 2.6.2**. Вход не меняется; существующий выход,
папка внутри сохранённого мира, symlink и конфликтующие файлы отклоняются.
Перед официальным `horizon-port-pack upgrade-datapack` выполняются явные
преобразования:

- Два `weird_scaled_sampler` заменены на интервальный выбор поддерживаемых
  выражений `r * abs(noise(x/r, y/r, z/r))`. Границы обеих rarity-таблиц
  проверены оригинальными методами 1.21.1: 34 случая. Формула проверена
  оригинальным sampler в 56 случаях, ошибка формулы — 0. Это **не** доказательство
  побитовой эквивалентности Rust-движку: отличаются точность вычислений и способ
  масштабирования координат.
- В 130 биомах старый `{air: [...]}` преобразован в упорядоченный список
  carvers. Непустой `liquid` и неизвестные формы требуют отдельного разбора.
- Из условия поверхности убрано только фиктивное имя
  `terralith:comment_dont_generate_strips_here`. Оно не имеет определения биома
  и служит комментарием в OR-списке. Все реальные условия сохранены; если
  появится настоящий биом с таким именем, сборка остановится для проверки.
- В 84 списках шага vegetation соседняя пара sugar cane / pumpkin приведена
  к порядку ванильной 26.3. Иначе старые и новые биомы создают цикл
  `pumpkin → sugar_cane → pumpkin`. Ни одна feature не удалена. Проверяется
  порядок подготовленных ванильных данных; перестановка непоследовательной
  пары или пары с дубликатами не выполняется автоматически.
- В 213 конфигурациях деревьев `dirt_provider` / `force_dirt` перенесены в
  `below_trunk_provider`. При `force_dirt=true` provider безусловный; иначе
  условный provider ничего не пишет и не сэмплирует на семи исходных почвах.
  Оригинальный `TrunkPlacer.isDirt` проверен на 1060 типах и 26 684 состояниях
  блоков с привязанным исходным тегом dirt. У 26.3 этот тег содержит другой
  набор, поэтому ссылка на новый тег вместо исходного поведения была бы ошибкой.
  Подзол, мох, mud, muddy mangrove roots и остальные старые почвы сохранены.
  Совмещённые старый/новый providers, не-bool флаг и сложный старый provider
  отклоняются для отдельного разбора.
- В 23 disk-configs старому нетипизированному `{fallback, rules}` добавлен
  дискриминатор `minecraft:rule_based`. Fallback, условия, порядок правил,
  target и размеры сохранены. Неизвестные поля старой записи отклоняются.
- Для 93 вхождений параметров noise/dual_noise/noise_threshold использован
  официальный upgrader, который преобразует `firstOctave/amplitudes` в новую
  нормированную запись. 54 уникальных набора временно конвертируются как noise
  registry records и затем подставляются обратно inline; временные файлы удалены
  из результата. Seed, scale, slow_scale, palette и threshold не меняются.
  Самостоятельная формула нормирования не вводится. Референсные пробы охватывают
  три набора параметров исходного Terralith, по два seed и 64 координаты; палитра
  синтетическая. Это ограниченная проверка выбора блоков, не всей генерации мира.
- 59 старых `random_patch`/`flower` заменены на `overlay` с `count` и `offset`.
  Внутренняя overlay сохраняет именованную или inline placed feature со всеми
  её modifiers. Внешняя возвращает OR результатов попыток, не останавливается
  при первой неудаче. Симметричный trapezoid использует два nextInt(spread+1),
  в том числе при spread=0: замена нулём изменила бы всю случайную последовательность.
  Одно определение `snowy/fix_snow` сохранено без преобразования и явно отмечено
  в `deferred_patch_files`: его y_spread=25 превышает границу ±16 текущего движка.
  Неизвестные поля и нецелые/отрицательные значения требуют отдельного разбора.

Выбрано 1867 файлов генератора, измерения, структур и worldgen-тегов.
Включены теги новых биомов: наличие `.hmod` само по себе не гарантирует, что
мировой реестр увидит новые биомы. 15 остальных `outside`-файлов оставлены
в исходнике и перечислены в локальном `techquest-worldgen-trial.json`.
Отчёт содержит SHA-256 каждого входа, преобразованные пути и вывод официального
upgrader. Успех этого скрипта всегда оставляет `server_boot_tested=false` —
результаты запуска записываются отдельно после реальной проверки.

## Исправление прежней диагностики

Ранее диагностический Rust-пример сообщал об отсутствии
`minecraft:overworld/continents`, `temperature`, `erosion`. Его обход графа
не учитывал короткие имена с неявным namespace `minecraft`. Эти функции
есть в подготовленных ванильных ресурсах. После исправления диагностики
сообщения исчезли; **данные не переименовывались и алиасы не добавлялись**.
Ошибка `weird_scaled_sampler` была настоящей и устранена преобразованием выше.

## Воспроизведение разработчиком

Нужны закреплённый Horizon `c78187dffffb60f31517eadcb87413386e8ce729`,
полные ресурсы 26.3 и workspace шести модулей из `SERVER_TEST_RU.md`.

```bash
python horizon/tools/prepare_terralith_worldgen.py \
  --work /path/to/five-together \
  --port-tool /path/to/pinned-horizon/target/fast/horizon-port-pack \
  --resources /path/to/prepared/26.3 \
  --output /path/to/new-terralith-trial
```

Создать новый изолированный сервер по `SERVER_TEST_RU.md`, оставить
`online_mode=true`, whitelist и loopback. Установить шесть проверенных `.hmod`
и включить их в `horizon-mods.txt`. Для актуальных живых features сначала
создать производный Terralith-модуль:

```bash
python horizon/tools/stage_terralith_content.py \
  --work /path/to/five-together \
  --datapack /path/to/new-terralith-trial \
  --sdk /path/to/pinned-horizon/target/fast/cargo-horizon-mod \
  --output /path/to/new-derived-content
```

В новой тестовой установке заменить только копию `terralith.hmod` результатом
`new-derived-content/target/horizon-mod/terralith.hmod`, сохранив исходный пакет.
Скрипт проверяет официальный SDK build/check, id/version/API/side и SHA-256.
Обновляются определения только в namespace `terralith`; `horizon-mod.toml`
не меняется. Для каждого старого пути configured_feature/configured_carver
проверяется новый feature/carver и записывается миграция в локальный отчёт.
Папки `target/` исходного workspace и сторонние исполняемые файлы не копируются.

Эта синхронизация нужна: генератор читает мировые datapack overrides, а
`/place feature` и живые features используют также content-root. Старый `.hmod`
с новым datapack давал ошибку `trunk_provider` при размещении дерева, несмотря
на успешный декодер генератора. Производный модуль и datapack нужны **вместе**;
ванильные overrides остаются мировыми, без захвата namespace `minecraft`.
Скрипты не устанавливают результат автоматически и отказываются писать внутрь
исходного work/datapack, подготовленных ресурсов или существующего мира.

Скопировать весь результат первого скрипта в
`<server-dir>/<new-world-name>/datapacks/techquest_terralith_adapted/`
**до первой генерации мира**. Это серверный путь, без клиентского `saves/`.

На seed 263 начальная проверка использовала команды:

```text
locate biome terralith:arid_highlands
forceload add -2272 2272
execute if biome -2272 71 2272 terralith:arid_highlands run say TERRALITH_BIOME_OK
setblock -2272 200 2272 minecraft:gold_block
save-all flush
```

Затем штатные `stop` / `start`, повторная проверка биома и
`execute if block -2272 200 2272 minecraft:gold_block run say TERRALITH_BLOCK_OK`.
После `Done` принудительные чанки могут ещё загружаться: дождаться их готовности,
а не считать немедленный ответ `That position is not loaded` повреждением мира.
В последующем мире `locate biome` вернул Y=81 вместо 71: использовать фактический
результат поиска для этого мира, не жёстко зафиксированный Y из старого прогона.

Для деревьев создана отдельная тестовая площадка на Y=219/220. На траве и
подзоле размещён `terralith:birch/trees_forest`, на другом подзоле — форсированное
`terralith:flower/blue/birch_tree`. Проверены реальные блоки стволов и почвы:
трава стала dirt, нефорсированный подзол остался podzol, форсированный стал dirt.
После `save-all flush`, остановки и запуска все шесть проверок повторились.
Это размещение командой; естественный спавн деревьев во всех лесных биомах и
полный паритет геометрии/случайных чисел этим не доказываются.

Собственные `probes/RarityProbe.java` и `probes/SamplerProbe.java` проверяют
оригинальные методы отражением, без декомпиляции, запуска клиента или сервера.
`probes/TreeDirtProbe.java` отдельно проверяет предикат почвы на всех состояниях;
ему нужен classpath библиотек bundle и при компиляции (Gson), и при исполнении.
Эти probes привязаны к официальным mappings 1.21.1; SHA-1 JAR и mappings записаны
в JSON-отчёте. Использовать проверенный официальный server JAR и библиотеки
из его bundle. Компилировать probes в **отдельную** папку `probe-classes`,
с namespace `techquest.probes`. Не добавлять в classpath папку с launcher
`version.json`: она перекрывает одноимённый внутренний ресурс игры.

`probes/build_noise_cases.py` строит локальные векторы для `NoiseStateProbe.java`
и `noise_states.rs`. Векторы и игровые библиотеки не включаются в репозиторий:

```bash
python horizon/probes/build_noise_cases.py --work /path/to/five-together \
  --port-tool /path/to/pinned-horizon/target/fast/horizon-port-pack \
  --output /path/to/new-cases.json
javac -cp '/path/to/unpacked-bundle/*' -d /path/to/probe-classes \
  horizon/probes/NoiseStateProbe.java
java -cp '/path/to/probe-classes:/path/to/unpacked-bundle/*' \
  techquest.probes.NoiseStateProbe /path/to/new-cases.json /path/to/reference.json
```

Скопировать `noise_states.rs` в upstream examples как `techquest_noise_states.rs`:

```bash
cargo run --manifest-path /path/to/pinned-horizon/Cargo.toml --profile fast --locked \
  -p horizon-world --example techquest_noise_states -- \
  /path/to/prepared/26.3/facts.json /path/to/new-cases.json /path/to/native.json
```

Сравнить два выходных JSON-массива поэлементно. В проверенном прогоне — 384/384
совпадения. Это не перебор всех наборов параметров или всех координат.

Для patches аналогично работают `build_patch_cases.py`, `PatchTraceProbe.java`
и `patch_traces.rs` (upstream example `techquest_patch_traces`). Генератор векторов
принимает один аргумент — новый выходной JSON. Java- и Rust-probes принимают
такие же аргументы, как noise-probes выше. Они сравнивают настоящий старый patch
loop и новую композицию с записывающим predicate, включая дочерние случайные
смещения, чередующийся успех/все неудачи и следующий random draw. Stub-мир
не генерирует чанки и не доказывает паритет цветов, освещения или всей природы.

В отдельном серверном мире seed=263 протестированы `terralith:plains/patch_grass`,
`terralith:birch/flowers` и `terralith:sakura/flowers` на травяных площадках Y=219.
Проверены short_grass в [126,220,126], lily_of_the_valley в [152,220,127],
white_tulip в [176,220,127], их почва и повторная загрузка после save-all flush.
Это ручное размещение настоящих features, не проверка всех естественных биомов.

В серверном тесте providers `pause-when-empty-seconds=0` выставлен **в server.toml**
в `[properties]`: иначе пустой сервер через минуту засыпает и forceload может
не продвигать генерацию. После forceload дождаться `execute if loaded` в каждой
проверяемой области. На площадке Y=220 размещены `terralith:shrubland/disk_podzol`
и `terralith:canyon/glacial/snow`. Проверены podzol в [128,220,128], нетронутый
stone в [129,220,128] и слои снега в X=144…150, Y=220, Z=128:
`[3,3,2,2,2,2,3]`. Все состояния повторно проверены после сохранения и запуска.

## Ограничения и следующий этап

Первый сервер сообщал о **246 пропускаемых placed features**. Аудит именно того
content-root, который использовал сервер, показывает 106 отказов
`below_trunk_provider`, 63 `exclusive state or provider`, 62 `basic feature type`
и другие несовместимости. Подмена этого content-root чистой ванилью даёт другой
набор отказов и не описывает сервер с шестью модулями.

После переноса деревьев реальный сервер и новый аудит его effective content-root
согласованно показывают **140** пропусков: 63 `exclusive state or provider`,
62 `basic feature type` и остальные ошибки. Ничего не исключено из списка
features для уменьшения этого числа. В `probes/worldgen_pipeline.rs` сохранён
первичный код аудита через официальный `horizon-world`. Скопировать его в
`<upstream>/crates/horizon-world/examples/techquest_worldgen_audit.rs` и выполнить:

```bash
cargo run --manifest-path /path/to/pinned-horizon/Cargo.toml --profile fast --locked \
  -p horizon-world --example techquest_worldgen_audit -- \
  /path/to/effective-content-root /path/to/new-terralith-trial
```

Первый аргумент — root из строки `content from 6 mod(s)` журнала сервера,
не чистые ванильные ресурсы. Этот probe проверяет JSON-реестры и декодирование;
сервер, бинарные шаблоны структур и игровой паритет он не проверяет.

После переноса providers осталось **77** отказов: 62 `basic feature type`,
6 `block`, 5 ссылок на отсутствующие старые feature IDs, 2 `level_test_distance`,
по одному `replaceable_blocks` и `missing block identifier`. Все 63 отказа
`exclusive state or provider` устранены; список features не сокращался.

После переноса patches осталось **22**: 7 basic feature type и остальные
15 ошибок из предыдущего этапа. Полный список сохранён в patch-отчёте. Из этой
группы basic остались fix_snow с широким разбросом, nether_forest_vegetation,
четыре dripstone_cluster и forest_rock; их нельзя исправить простым переименованием.

Полная генерация деревьев, растительности, структур/лута и визуальный паритет
ещё не подтверждены. Не проверены вход лицензированного клиента, мультиплеер
и нативные промышленные механики. Статус остаётся `partial`; нулевое число
доказанно полных портов не меняется по одному успешному запуску мира.

Сторонние JAR, datapack, `.hmod`, подготовленные ресурсы, миры и сырые логи
не входят в репозиторий или публикацию. Основной NeoForge main не меняется.

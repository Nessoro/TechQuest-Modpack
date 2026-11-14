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

Затем восстановлен исходный default блока у шести `multiface_growth` configs.
Оригинальный кодек 1.21.1 подтвердил `glow_lichen` во всех шести случаях.
Пропуски снижены **с 22 до 16**. На сервере проверены лишайники на камне и
тёмном дубе, запрет неподходящей поверхности и сохранение всех граней после
перезапуска. [Результат лишайников](TERRALITH_MULTIFACE_RUNTIME_RESULT.json).

Две встроенные root_system configs переведены в формат 26.3; отказы снижены
**с 16 до 14**. Основной набор из шести hmod достиг Done. В отдельном командном
тесте с дополнительным test-only модулем проверены дочерние features, корни,
свисающие корни и сохранение шести блоков. [Результат корней](TERRALITH_ROOT_RUNTIME_RESULT.json).

Пять ссылок на старые ванильные configured features заменены точными inline
определениями из проверенного официального bundle 1.21.1. Отказы снижены
**с 14 до 9**. Трава, оба гриба и тыква проверены после перезапуска; 800 patch-проб
совпали, включая tries=96. [Результат старых ссылок](TERRALITH_LEGACY_REFERENCE_RUNTIME_RESULT.json).

После миграции четырёх dripstone_cluster и двух large_dripstone configs осталось
**4 отказа**. В тестовых пещерах все шесть features разместили блоки;
они и свойства pointed dripstone сохранились после перезапуска.
[Результат dripstone](TERRALITH_DRIPSTONE_RUNTIME_RESULT.json).

У basalt seed исправлен формат target без изменения результата старого кодека.
Осталось **3 отказа**. Все три ориентации basalt заменились на smooth_basalt,
соседи при radius=0 сохранились; результат проверен после перезапуска.
[Результат basalt](TERRALITH_BASALT_RUNTIME_RESULT.json).

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
- В шести `multiface_growth` configs опущенный старый default материализован
  как `block=minecraft:glow_lichen`. Именно это значение выбирает настоящий
  кодек 1.21.1. Явно заданный block и все остальные поля сохраняются.
- Для двух старых `root_system` новая пара `level_test_distance` и
  `max_level_deviation` равна 0/0, как в ванильной rooted_azalea_tree 26.3.
  В 1.21.1 этой проверки уровня местности нет; pinned-движок при distance=0
  не выполняет новые запросы. Child feature, старые условия, providers,
  радиусы и попытки сохранены. Явная полная новая пара не меняется, частичная
  пара требует разбора. Полный паритет алгоритма корней между версиями не заявлен.
- Опциональный `--legacy-server-jar` читает четыре старых ванильных patch-configs
  из официального bundle 1.21.1. Проверяются SHA-1 bundle, индекс версии и SHA-256
  внутреннего server JAR. Пять configured-feature ссылок внутри placed records
  получают точные inline определения; списки placed IDs и biome features не меняются.
  Далее работают официальный upgrader и композиция patch-loop. Custom override
  этих четырёх definitions в источнике отклоняется для разбора. Новые production
  registry aliases не создаются, original-файлы и namespace ownership сохраняются.
- Четыре `dripstone_cluster` стали generic `speleothem_cluster`: явно указаны
  исходные dripstone_block/pointed_dripstone, переименованы три соответствующих
  поля. Для двух large_dripstone явно указан прежний replacement-tag.
  Радиусы, высоты, плотность, wetness, ветер и остальные распределения сохранены.
  Используется существующий **объединённый** `dripstone_replaceable_blocks`:
  Terralith добавляет dirt, blue ice, packed ice и через base-stone tag — blackstone.
  Probe сравнил старую ваниль + эти additions с effective Horizon tags: 10/10
  типов блоков совпали. Теги не заменены новым сокращённым списком.
- Одна misspelled block-state запись `Name/Properites` у basalt seed заменена
  на современный `id/properties`. Старый кодек **игнорирует** `Properites` и
  выбирает default basalt axis=y; `LegacyBlockStateProbe.java` подтвердил это
  настоящим Codec и обратным encode. Переименовывать эту опечатку произвольно
  нельзя: это могло бы активировать старое игнорируемое значение. Обработан
  только точный проверенный случай; другие формы требуют разбора.

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
  --legacy-server-jar /path/to/official-1.21.1-server-bundle.jar \
  --output /path/to/new-terralith-trial
```

Для полного текущего этапа нужен официальный **bundled** server JAR 1.21.1,
SHA-1 `59353fb40c36d304f2035d51e7d6e6baa98dc05c`. Он не включён в репозиторий.
Без опционального аргумента пять старых ссылок остаются несовместимыми;
неверный JAR и symlink отклоняются до создания результата. В отчёте записаны
хеши четырёх прочитанных JSON, сами игровые файлы не коммитятся.

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

`MultifaceDefaultsProbe.java` принимает workspace шести модулей и выходной JSON.
Он декодирует только конфигурации с опущенным `block` через настоящий 1.21.1 Codec
и RegistryOps с исходными встроенными реестрами. Шесть исходных конфигураций
дали `minecraft:glow_lichen`; конфигурации с явно заданным блоком не меняются.

Для лишайников создан ещё один изолированный мир: `terralith:highlands/lichen`
размещён в каменной нише [128,220,128], `terralith:dark/lichen_log` — в нише из
dark_oak_log [152,220,128]. Последняя feature отказалась расти в каменной нише
[176,220,128], как требует её can_be_placed_on; поверхность пола осталась
запрещённой. До и после перезапуска проверены все шесть face-флагов и waterlogged.
Геометрия и случайная последовательность всей multiface-growth этим не сверялись.

Для корней `probes/build_worldgen_test_module.py --kind roots --datapack /path/to/trial --sdk
/path/to/cargo-horizon-mod --output /path/to/new-probe` создаёт SDK-проверенный
**тестовый седьмой модуль** `techquest_root_probe`. Он даёт имена двум исходным
inline configured features: иначе `place feature` их не принимает. Конфигурации
копируются без изменения; внешние rarity/height/biome modifiers placed features
этим способом не проверяются. Основные шесть hmod и владение namespaces сохраняются.
Сначала сервер запущен с шестью основными модулями, затем со седьмым тестовым.
На каменных площадках проверены granite в [128,225,128], [128,221,128],
[128,220,128] и diorite в [176,224,128], [176,221,128], [176,220,128].
Все шесть блоков сохранились после перезапуска. Занятый stone origin в
[152,220,128] отклонён и остался stone. Естественная генерация этих систем
в пещерах и полный паритет не подтверждены. Probe hmod и производные данные
остаются локальными и не входят в репозиторий.

Тот же builder с `--kind legacy-patches` создаёт `techquest_legacy_probe` для
четырёх восстановленных inline definitions. Сначала проверен запуск production
шести hmod; затем с седьмым тестовым модулем размещены short_grass [127,220,127],
brown_mushroom [161,220,128], red_mushroom [191,220,128], pumpkin [224,220,128].
Все растения и почва сохранились после перезапуска. Тыквенный patch отказался
расти над stone, как требует старый predicate. Outer placed modifiers этим
командным тестом не проверяются. Расширенные `build_patch_cases.py`/Java/Rust
probes дали 800 совпадений по 26 880 координатам, результатам и следующему random
draw. Обобщённый builder также воспроизвёл прежний SHA-256 root-probe hmod.

Для inline dripstone clusters builder принимает `--kind dripstone` и создаёт
`techquest_dripstone_probe` с двумя test-only aliases: spires и thermal.
Ещё четыре конфигурации тестируются по настоящим именам `terralith:savanna/dripstone`,
`terralith:savanna/shattered/teeth`, `terralith:cave/frostfire/pillar`,
`terralith:cave/frostfire/pillar_huge`. Сначала запущены основные шесть hmod,
затем седьмой тестовый. Построены отдельные каменные пещеры с blue-ice полом;
наблюдаемые blocks и координаты записаны в JSON. Sparse cluster и малый pillar
потребовали больше одного вызова до наблюдения блока в проверяемой области;
параметры features для теста не менялись. Все шесть результатов сохранились;
у pointed dripstone проверены vertical_direction, thickness, waterlogged.
Outer placed modifiers, естественные пещеры и весь случайный алгоритм не сверялись.

`probes/dripstone_tags.py` принимает `--legacy-server-jar`, `--work`,
`--content-root` (эффективный root шести модулей) и новый `--output`. Он проверяет
bundle, additive tags Terralith, отсутствие других source overrides этих тегов
и сравнивает полный набор исходных modded block IDs с текущим объединённым.

`LegacyBlockStateProbe.java` принимает путь исходного configured_feature
`cliffs/basalt/seed.json` и новый выходной JSON; classpath тот же официальный
bundle 1.21.1, что у других Java-probes. На сервере с шестью модулями проверены
три basalt axes в X=128,136,144, Y=220, Z=128, соседи в X+1 и stone-column
контроль в X=152. Smooth basalt и соседние basalt сохранились после перезапуска;
stone без подходящего target в столбце был отклонён. Естественные скалы и
все параметры исходного алгоритма blobs этим не проверяются.

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

После восстановления default лишайников осталось **16** отказов: те же 7 basic,
5 старых feature IDs, 2 level_test_distance, replaceable_blocks и missing block
identifier. Все 6 отказов `block` устранены; новых отказов не появилось.

После переноса корней осталось **14**: 7 basic feature type, 5 старых feature IDs,
replaceable_blocks и missing block identifier. Оба отказа level_test_distance
устранены без новых отказов. Список features не сокращался.

После переноса старых ссылок осталось **9**: fix_snow с y_spread=25,
nether_forest_vegetation, четыре dripstone_cluster, forest_rock,
replaceable_blocks у frostfire columns и ошибочная старая block-state запись
у basalt seed. Все пять unknown configured-feature references устранены.

После dripstone остались **4**: три basic feature type (fix_snow,
nether_forest_vegetation, forest_rock) и missing block identifier у basalt seed.
Устранено ещё пять placed-feature отказов без новых пропусков.

После basalt seed остались **3 basic feature type**: snowy/fix_snow,
flower/blue/flowers (nether_forest_vegetation) и cherry/rock (forest_rock).

Полная генерация деревьев, растительности, структур/лута и визуальный паритет
ещё не подтверждены. Не проверены вход лицензированного клиента, мультиплеер
и нативные промышленные механики. Статус остаётся `partial`; нулевое число
доказанно полных портов не меняется по одному успешному запуску мира.

Сторонние JAR, datapack, `.hmod`, подготовленные ресурсы, миры и сырые логи
не входят в репозиторий или публикацию. Основной NeoForge main не меняется.

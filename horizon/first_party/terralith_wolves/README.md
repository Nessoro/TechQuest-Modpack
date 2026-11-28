# TechQuest Terralith Wolves — нативное расширение 0.1.0

Восстанавливает выбор девяти существующих wolf variants по исходным
`c:has_wolf_variant/*` тегам Terralith 2.6.2. Это Rust-код для сборки движка,
не исполняемый Java-мод и не content-only hmod.

Закреплены Horizon `c78187dffffb60f31517eadcb87413386e8ce729` и Mixins
`5a64af938ec86b00d53d16a408aabc0038fb3e57`. Нужны шесть content-модулей
и согласованный world datapack из [локальной установки](../../LOCAL_INSTALL_RU.md).
Исходные девять wolf JSON не копируются в пакет: ID взрослых текстур совпадают
с целевой vanilla, а правила выбора реализованы для этих девяти native IDs.
Другие версии/варианты требуют отдельного переноса.

## Почему нужны два HEAD-хука

У базового движка фиксированные vanilla-условия. Кроме того, content builder
обрезает неизвестные ему custom biome IDs из глобальных mob tags. Полные
определения уже есть в `WorldTables::pack_tags` после подключения world datapack.

`world_tags.rs` перед `Game::biome_facts` читает этот кеш и передаёт результат
через одноразовый контекст `(biome, variant)` текущего потока. `select.rs`
перед `wolf_variant_for` забирает его. Прямые вызовы selector используют c tags,
а без них продолжают vanilla-ветку. Контекст очищается перед каждым расчётом,
при чтении и при несовпадении биома. Остальное тело `biome_facts` сохраняется.
Нет I/O и random draws в этих хуках. Три Rust-теста проверяют однократность,
сброс и изоляцию потоков.

Закреплённый Mixins отклоняет RETURN/OVERWRITE для исходной функции с closure
и `world_biomes!`; два HEAD-хука применяются штатно. Они не требуют изменения
исходного checkout. Адаптированные строки lookup имеют MIT-атрибуцию в
[LICENSE-HORIZON](LICENSE-HORIZON) и [общем notice](../../THIRD_PARTY_NOTICES.md).

Порядок выбора измерен на запущенном Minecraft 1.21.1 с исходными девятью
определениями и искусственными пересекающимися тегами. Он отличается от
bootstrap: ashen, black, chestnut, pale, rusty, snowy, spotted, striped, woods.
Без совпадений — pale. Это существенно для `terralith:savanna_badlands`.

## Проверенная сборка разработчика

В отдельном worktree закреплённого Horizon заменить только документационную
ссылку `CLAUDE.md` обычной копией `AGENTS.md`: Mixins отказывается читать
symlinks. В оригинальном checkout ничего не менять. Например:

```bash
git -C /path/to/pinned-horizon worktree add --detach /path/to/new-clean-source \
  c78187dffffb60f31517eadcb87413386e8ce729
cp --remove-destination /path/to/new-clean-source/AGENTS.md /path/to/new-clean-source/CLAUDE.md
```

Собрать Mixins на указанном commit (`cargo build --release --locked -p
horizon-mixins-cli`), затем из clean source:

```bash
/path/to/horizon-mixins apply \
  --workspace /path/to/new-clean-source \
  --mods /path/to/TechQuest-Modpack/horizon/first_party \
  --out /path/to/new-native-stage
cd /path/to/new-native-stage
CARGO_TARGET_DIR=/path/to/native-target CARGO_BUILD_JOBS=2 cargo build \
  --profile fast --locked --offline --no-default-features \
  --features ureq/native-certs,ureq/proxy-from-env \
  -p horizon-client --bin horizon-client
```

`--offline` предполагает заполненный Cargo cache. В проверенном прогоне:
Rust игры 1.99.1, Rust Mixins 1.95.0, Linux x86-64. Последняя сборка заняла
4m38s с кешем после первичной сборки; это время компиляции, не игровая нагрузка.
Изменились три Rust-файла staged workspace: client_lib.rs, mobs/tame.rs,
game/creatures.rs. Cargo.lock и оригинальные исходники сохранены.

Полученный `native-target/fast/horizon-client` используется как новый
`horizon-engine`. В отдельный каталог native-tools скопировать остальные три
инструмента, LICENSE и research-lock.json из проверенной базовой сборки.
Базовый каталог инструментов сохранить. Пересчитать четыре SHA-256 в копии
build-result.json и указать происхождение staged native build.

Исходный `.hnmod` — zip с `horizon-native.json` в корне и следующими файлами
под `mixins/techquest_terralith_wolves/`:

```text
horizon-mixin.toml
select.rs
world_tags.rs
context.rs
LICENSE-HORIZON
```

Выполнить `cargo-horizon-mod check /path/to/techquest_terralith_wolves.hnmod
--json`. Source bundle проверяется SDK, но исполняется только после компиляции.
Поместить его в `native-tools/native-mods/techquest_terralith_wolves.hnmod`;
в build-result.json добавить список `native_mods` с одной записью:

```json
{
  "id": "techquest_terralith_wolves",
  "version": "0.1.0",
  "mixins_commit": "5a64af938ec86b00d53d16a408aabc0038fb3e57",
  "sha256": "SHA-256 собственного локального source bundle"
}
```

Остальная установка — обычный `install_isolated_server.py install`, с новым
каталогом `--tools`. Установщик проверяет native bundle через SDK, совпадение
pins/ID/version/checksum, записывает расширение в lock и фиксирует пакет/движок
контрольными суммами. `.hnmod` не помещается в `horizon-mods`: код уже скомпилирован
в этом движке. Публикация source bundle и готового движка не выполняется.

Официальный Launcher также имеет `native-build FOLDER --server-output DIR
--version TAG --trust-native-code`; этот альтернативный маршрут в текущем
прогоне не проверялся. Клиент должен запускаться через официальный Launcher
с проверкой владения игрой.

## Проверки

Разработческий reference driver `horizon/probes/live_wolf_priority.py` принимает
`--server-jar` (проверенный bundle 1.21.1), `--source-outside`, `--java`, новые
`--server-dir`/`--output`, `--port` и `--accept-eula`. Он запускает исходный
сервер на loopback с online-mode/whitelist, измеряет девять приоритетов через
reload и штатно останавливается. EULA для изолированных тестов уже принята.

`build_wolf_cases.py` принимает `--work`, `--server-jar`, `--live-priority` и
новый `--output`. `WolfSelectionProbe.java` принимает output JSON и live-priority
JSON; она вызывает настоящий 1.21.1 selector для 512 масок в измеренном порядке.
`wolf_variants.rs` вызывает native selector, читая `DataStore`/world tags:

```text
wolf_variants EFFECTIVE_ROOT VANILLA_ROOT INSTALLED_WORLD SOURCE_CASES MASK_ORACLE
```

Нативные компоненты проверены для 159 исходных биомов и 512 масок, без расхождений.
На 67 vanilla-биомах без Terralith результат совпал с базовым движком.
Реальный Horizon с шестью content-модулями и этим расширением создал все девять
вариантов плюс overlap-case; десять сущностей, варианты и биомы проверены после
save/reopen. Использовались `fillbiome` и summon **без NBT**, чтобы вызвался
настоящий finalizeSpawn. Сервер остановлен; generator audit по-прежнему 0 skips.

[Полный результат и ограничения](../../TERRALITH_WOLF_RUNTIME_RESULT.json).
Естественный спавн, размножение, детские текстуры, визуальный клиент и мультиплеер
ещё не проверены. Промышленные механики TechQuest остаются следующими этапами.

# TechQuest YUNG Dungeons 0.1.0

Нативное расширение Horizon 26.3, закреплённое на `c78187d` и Mixins `5a64af9`.
Один cancellable HEAD-hook для
`horizon_world::worldgen::structure::processor::Processor::evaluates_entire_piece`
возвращает `true` только для `CountCap`; для остальных processors выполняется
исходный метод, в том числе прежняя поддержка vanilla `Capped`.

Расширение работает вместе с производным Better Dungeons hmod, который собирает
`tools/stage_yung_dungeons.py`. Его три small-dungeon processor lists содержат
`horizon:count_cap`: гарантированный первый сундук, шанс 0.2 для следующих,
максимум два, замена лишних на `minecraft:cave_air`. Это исходные настройки
Better Dungeons 5.1.4; произвольные пользовательские min/max не импортируются.
Ранее восстановленные spawner processors также остаются в этом content-модуле.

## Область подсчёта

Pinned Horizon отфильтровывает блоки по chunk bounding box до запуска большинства
processors. Для CountCap это повторяет гарантированный минимум в каждом чанке.
На 17 исходных small dungeons обычный CountCap оставлял 93 контейнера вместо
46 на оригинальном NeoForge. Совпадение одного общего количества тоже недостаточно:
контроль сравнивает все 142 позиции контейнеров, удалённые блоки и loot table IDs.
С расширением совпали 28 сундуков, 18 бочек, 96 cave_air и все 46 loot references.
Проверка 17 прежних спавнеров также прошла; весь набор сохранён после перезапуска.
[Runtime-результат](../../YUNG_CHEST_RUNTIME_RESULT.json).

Hook включает уже имеющийся путь обработки всего шаблона. Запись в мир по-прежнему
ограничена bounding box чанка в `place_in_world`; расширение не снимает clipping
записи, не меняет случайный генератор и не хранит глобальный счётчик.
Проверено чтением MIT-кода pinned Horizon; функция hook написана отдельно.
LGPL Java-код YUNG's не читался и не декомпилировался. Оригинальный мод использован
как работающий black-box; JSON-формат и конфигурация прочитаны как данные.

## Сборка

Собирать через pinned Mixins из неизменённого clean worktree Horizon по
[инструкции wolf extension](../terralith_wolves/README.md). Корень `--mods`
содержит обе директории native-модов: `terralith_wolves` и `yung_dungeons`.
Content-only `expedition_marker` не является native injection.

```bash
/path/to/horizon-mixins apply \
  --workspace /path/to/clean-pinned-horizon \
  --mods /path/to/TechQuest-Modpack/horizon/first_party \
  --out /path/to/new-native-stage
cd /path/to/new-native-stage
CARGO_TARGET_DIR=/path/to/native-target CARGO_BUILD_JOBS=2 cargo build \
  --profile fast --locked --offline --no-default-features \
  --features ureq/native-certs,ureq/proxy-from-env \
  -p horizon-client --bin horizon-client
```

`horizon-native.json` кладётся в корень source `.hnmod`; `horizon-mixin.toml`
и `count_scope.rs` — в `mixins/techquest_yung_dungeons/`. Проверить пакет через
официальный `cargo-horizon-mod check --json`. Хеш source bundle фиксируется
в `build-result.json` новой папки native-tools, рядом с wolf bundle.
Сам SDK-check не подтверждает, что расширение вошло в скомпилированный движок.

Установщик принимает эти native-tools и шесть согласованных content-модулей;
он проверяет оба `.hnmod`, фиксирует engine и source bundles по SHA-256.
Не заменять движок или hmod в старой установке и не редактировать lock.

Реальный серверный тест сравнивает исходные и native container observations
через `probes/reference_yung_containers.py` и
`probes/live_yung_structures.py --reference-containers`, отдельно сохраняя
контроль 17 спавнеров через `--reference`. Выполнить save/reopen и повторить
read-only пробу без повторного размещения структур.

Нативное расширение не переносит остальные dropped processors YUNG's,
не реализует 16 неподдерживаемых определений структур и не подтверждает
игровое открытие сундуков, естественную генерацию или полный модпак.

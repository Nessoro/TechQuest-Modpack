# Эталон Pretty Pipes перед нативным переносом

Из нового состава #48 выбран Pretty Pipes 1.22.0: простой перенос предметов
позволяет начать проверяемую промышленную механику. Этот первый этап запускает
оригинальный мод на отдельном NeoForge и фиксирует поведение для Rust-порта.
Затем базовые контроли повторены [нативным прототипом](first_party/pretty_pipes/README.md);
полный Pretty Pipes по-прежнему не перенесён.

Источник — Modrinth `XExdLWCQ`, version ID `lrhbGGSe`, точный файл/SHA-512
из `source/techquest-post-pr48-candidate.json`. Скачанный JAR сверён побайтно.
Исходники для изучения — tag `1.22.0`, commit
[`1f8ac61c6de5b191f3b28da2c23d8040a231047f`](https://github.com/Ellpeck/PrettyPipes/tree/1f8ac61c6de5b191f3b28da2c23d8040a231047f).
Корневой LICENSE этого commit проверен: MIT, Copyright (c) 2020–2021 Ellpeck.
Прочитаны Registry, PipeBlockEntity, ModuleItem, ExtractionModuleItem и части
PipeItem. Java-код в Horizon не копировался и не запускался как мод Horizon.
При адаптации исходного кода в Rust сохранить copyright/license и атрибуцию.

Original reference: Minecraft 1.21.1 / NeoForge 21.1.264, JDK 25,
один top-level Pretty Pipes JAR с его встроенными библиотеками. Это не запуск
всего состава из 101 проекта. Новая папка теста, отдельные world/Horizon/XDG homes,
seed 263; `127.0.0.1:25612`, online-mode и whitelist, игроков нет.
Приватный loopback RCON — порт 25613. EULA для изолированного теста уже принята.
Переиспользованы ранее установленные библиотеки NeoForge; старые миры и
content-пакеты Horizon не менялись.

## Наблюдения на настоящем сервере

Fixture — два сундука, соединённые тремя pipe blocks, восемь iron ingots:

| Сценарий | В исходном сундуке | В целевом |
| --- | ---: | ---: |
| Нет extraction module, 300 sprint ticks | 8 | 0 |
| Low extraction module, 400 ticks | 0 | 8 |
| Средняя труба разорвана, 100 ticks | 8 | 0 |
| High module, 20 ticks, сохранение партии в пути | 0 | 0 |
| После штатного save/stop и reopen | 0 | 8 |

В последнем случае новые предметы после reopen не создавались: восемь ранее
извлечённых слитков дошли в целевой сундук. Повторный прогон 400 ticks сохранил
ровно восемь, без дублирования. Мир сохранён, обе сессии штатно остановлены.
NBT очереди не экспортировался; нахождение партии в пути подтверждается
опустевшим источником, пустой целью перед stop и последующей доставкой.

Это контроль конечных результатов, не точного tick timing. `/tick sprint`
используется только для ускорения теста и не задаёт тайминг будущей реализации.
Фильтры, приоритеты, ветвления, переполнение, redstone, UI, crafting modules и
мультиплеер пока не проверены. Полный Pretty Pipes и промышленный модпак не перенесены.

## Воспроизведение

Подготовить новый reference server с указанными pinned NeoForge/JAR и приватным
server.properties (loopback, online-mode, whitelist, level-name с префиксом
`techquest-reference-`, RCON, `pause-when-empty-seconds=0`). Пароль не передавать
в командной строке. Сервер запускается отдельно с новыми служебными homes.

```bash
python horizon/probes/reference_pretty_pipes.py \
  --server-dir /path/to/new-reference-server --phase prepare \
  --output /path/to/new-prepare-result.json
# Дождаться завершения процесса сервера и повторно запустить тот же мир.
python horizon/probes/reference_pretty_pipes.py \
  --server-dir /path/to/reference-server --phase verify \
  --output /path/to/new-verify-result.json
```

Prepare создаёт fixture в тестовом мире, проверяет три сценария, сохраняет
партию в пути и останавливает сервер. Verify читает существующий fixture,
проверяет доставку и снова останавливает. Выходные файлы должны быть новыми.
Проба проверяет SHA-512 JAR, EULA, server isolation и отсутствие игроков;
секреты и raw NBT в отчёты не попадают.

Следующий этап — нативные pipe inventory/routing и очередь предметов с сохранением,
после чего повторить эти же контроли на настоящем Horizon 26.3.
[Результат reference-прогона](PRETTY_PIPES_REFERENCE_RESULT.json).

# TechQuest Horizon: экспериментальный порт

Экспериментальная разработка Horizon-версии TechQuest в ветке `experiment/horizon-port-lab`. Основной NeoForge TechQuest 0.3.3-alpha на main не изменяется. Закреплённый вход переноса — main `918b4bf`; MCHeli, TaCZ и ParCool в этот источник не возвращаются.

**Текущий этап:** нативная генерация мира и изолированный сервер 26.3.
Дальнейшие задачи и критерии полного модпака — в [активной цели PR #8](GOAL_PR8_RU.md).
История восстановления общих тегов — [yungsapi и аудит потерь](SHARED_YUNG_TAGS_RU.md).

[Подготовка и проверка сервера](SERVER_TEST_RU.md).
Реальный сервер 26.3 с шестью content-модулями достиг `Done`; сохранение и повторное
открытие мира проверены. Дополнительный локальный адаптер Terralith позволил
подтвердить естественный биом и его сохранение после перезапуска.
Все ранее пропускаемые placed features теперь декодируются: **246 → 0**;
деревья, почва, диск, снег, растительность, корни и dripstone проверены сервером после перезапуска.
Три noise-provider совпали с оригиналом в 384 пробах, patch-композиции — в 1800.
Forest rock совпал в 1124 traces, nether vegetation — в 450. Blue flowers,
включая moss support, проверены после перезапуска. Это серверный прототип
с шестью content-модулями; промышленные Java-механики ещё не перенесены.
Вход клиента, мультиплеер и Java-механики не проверены.
[Серверный результат](SERVER_RUNTIME_RESULT.json) · [Миграция Terralith](TERRALITH_RUNTIME_RU.md).
[Текущий результат генератора](TERRALITH_VEGETATION_RUNTIME_RESULT.json).
[Воспроизводимая локальная установка](LOCAL_INSTALL_RU.md) согласованных шести
hmod и world datapack проверена настоящим стартом и save/reopen.
Все 15 оставшихся outside-файлов Terralith [разобраны](TERRALITH_OUTSIDE_AUDIT.json):
пять recipe advancements восстановлены, девять wolf selectors проверены с
отдельным нативным расширением; один текстовый файл содержит авторские заметки.
Для рецептов прошли 165 нативных
сценариев открытия и 168 сеток крафта, включая alternate-материалы.
[Результат и ограничения проверки](TERRALITH_RECIPES_RUNTIME_RESULT.json).
Нативное [расширение волков](first_party/terralith_wolves/README.md) прошло
159 biome cases и 512 масок; все девять вариантов и overlap-case сохранены
после перезапуска настоящего сервера. Без Terralith 67 vanilla cases не изменились.
[Результат native build и игрового теста](TERRALITH_WOLF_RUNTIME_RESULT.json).
[Проверка структур YUNG's](YUNG_RUNTIME_RU.md): четыре структуры размещены,
208 блоков-кандидатов сохранились после перезапуска. В малых подземельях
восстановлен выбор моба спавнеров: 17 случаев совпали с исходным NeoForge,
включая save/reopen. Из 20 определений структур 16 пока не поддерживаются.
Ограничения сундуков затем восстановлены с отдельным нативным расширением:
142 позиции, 46 loot references и 17 спавнеров совпали с исходным NeoForge
до и после перезапуска. [Текущий результат YUNG's](YUNG_CHEST_RUNTIME_RESULT.json).
Остальные custom processors ещё требуют переноса.

## Уже сделано

1. [Снимок NeoForge 0.3.3](source/techquest-0.3.3-candidate.json): актуальный main `918b4bf`, 89 закреплённых Modrinth-проектов и исходные метаданные. [Происхождение](source/SOURCE.md). Это **не** готовый Horizon-модпак; отчёты ниже о старых 86 компонентах — история прежнего входа.
2. [План по каждому моду](tools/port_inventory.py): offline JSON/Markdown-отчёт с классификацией. Команда: `python horizon/tools/port_inventory.py`. Полный перенос исходных модов ещё не подтверждён: **0 полных портов**. Частичные игровые проверки перечислены в runtime-отчётах.
3. [Первый собственный Horizon-мод](first_party/expedition_marker/): **TechQuest Expedition Marker**, простой блок из ванильных материалов с рецептом, добычей и моделью. API Horizon 0.2, тип content, сторона both. **Это оригинальный прототип, не перенос Create/IC2/Wyrmroost.**
4. [Структурная сборка демонстрационного ZIP](tools/build_demo_hmod.py) и unit-тесты. **Ни наличие .hmod, ни успешный unit-тест не подтверждают реальную загрузку в Horizon.**

## Тестирование из корня репозитория

```bash
python horizon/tools/port_inventory.py
python horizon/tools/build_demo_hmod.py
python -m unittest discover -s horizon/tests -v
```

Вывод: `horizon/out/port-inventory.json`, `horizon/out/port-inventory.md`, `horizon/out/techquest_expedition_marker.hmod`. Это только экспериментальный пакет. Для проверки **официальным SDK** нужен установленный Rust/Cargo:

```bash
cargo install --git https://github.com/horizon-rust/horizon cargo-horizon-mod
cd horizon/first_party/expedition_marker
cargo horizon-mod build
cargo horizon-mod check target/horizon-mod/techquest_expedition_marker.hmod
```

Для полноценного запуска нужен Horizon 26.3 и собственная легально купленная Minecraft Java Edition.

## Импорт исходного модпака через Horizon

В приложении Horizon откройте **Modpacks → Import a pack file** и выберите скачанный `.mrpack` из успешного запуска GitHub Actions NeoForge TechQuest. В таблице будут отдельные статусы **Ported / Partial / Not yet / Not needed**. Только после импорта можно говорить об измеренном покрытии:

```bash
horizon-launcher modpack import /path/to/TechQuest.mrpack
horizon-launcher modpack list
horizon-launcher modpack port <pack> --from /path/to/your/legal/mods
```

Horizon умеет локально импортировать только некоторые данные/структуры/модели, но **не исполняет Java-логику**. В нём Minecraft 26.3, в оригинальном TechQuest 1.21.1 / NeoForge. Пользоваться старым сервером или миром без резервной копии **не следует**.

## Следующие кандидаты на реальный перенос

- **Мир и структуры:** сначала исследовать Terralith, YUNG's Better Dungeons и Strongholds. Переносить лишь разрешённые JSON/ресурсы, если не используются Java-генераторы. Нужны их оригинальные файлы и фактический coverage.
- **Интерфейс:** Xaero, HP и Forgematica потребуют переписывания в native Rust или поиска существующих модов Horizon.
- **Геймплей:** BuildCraft/IC2/Create/Mekanism/AE2, Wyrmroost, Legendary Monsters — отдельные большие проекты на нативном API, с проверкой прав авторов и серверной логики.
- **Оптимизация:** Sodium/FerriteCore не копировать автоматически: сравнить собственные возможности движка Horizon.
- **Производительность:** сравнивать FPS/RAM/TPS только после восстановления одинаковых механик и миров, иначе сравнение некорректно.

Документация: [Horizon Modpacks](https://playhorizon.dev/docs/modpacks), [Horizon Mods](https://github.com/horizon-rust/horizon/blob/main/docs/mods.md).

**Лицензии:** чужие JAR/ассеты не хранятся в ветке, никакой декомпиляции или републикации. Миры NeoForge/Horizon хранить отдельно.


## Результат первого группового переноса данных — 7 ноября 2026

GitHub Actions [#42382390837](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42382390837) **завершился успешно**. Официальный `horizon-port-pack` скачал оригинальные JAR из источников Modrinth (с проверкой хешей), обработал 4 мода YUNG's и создал отдельные локальные каталоги данных Horizon:

| Мод | Файлов в промежуточном пакете | Worldgen-файлов | Статус |
| --- | ---: | ---: | --- |
| Better Dungeons | 313 | 282 | **partial** |
| Better Strongholds | 137 | 120 | **partial** |
| Better Mineshafts | 33 | 14 | **partial** |
| Better Nether Fortresses | 203 | 187 | **partial** |
| **Итого** | **686** | **603** | 4 частичных переноса |

Обновлённое покрытие: **4 partial / 45 not yet / 37 not needed / 0 ported** из 86 компонентов. Дополнительно обработано 27 таблиц лута. Перенесённые данные и чужие JAR **не опубликованы**, в артефакте доступен лишь отчёт [Coverage-ONLY](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42382390837/artifacts/13578440342).

Это **не подтверждённый игровой порт**: не проверялись загрузка в реальном Horizon 26.3, генерация/совместимость структур, YUNG API, поведение процессоров, сервер и Tailscale. Для перехода от `partial` к `ported` нужны отдельные тесты, подтверждение прав на распространение и игровые сравнения.

## Достигнутый этап SDK

В [отдельном SDK-прогоне #42384517149](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42384517149) все четыре перенесённых content-пакета YUNG's прошли официальный `cargo-horizon-mod build/check`. **4 SDK-валидных / 4 частичных переноса / 0 доказанно рабочих игровых портов.** Проблема общего namespace `yungsapi` и неучтённых файлов требует отдельного разбора. Подробнее: [YUNG_SDK_VALIDATION_RU.md](YUNG_SDK_VALIDATION_RU.md).

## Пробный перенос Terralith

В [CI #42384762013](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42384762013) временный Terralith content-мод (1896 файлов) прошёл официальный SDK. Статус — только `partial`: 124 файла вынесены в `outside`, полноценную генерацию биомов и совместимость с YUNG's не проверяли. Код, JAR, структуры и текстуры Terralith **не публиковались**. См. [TERRALITH_LOCAL_RU.md](TERRALITH_LOCAL_RU.md).

## Совместная проверка пяти портированных наборов данных

[GitHub Actions #42385201713](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42385201713): пять модов (4 YUNG's + Terralith) успешно обработаны в одном `horizon-port-pack` workspace, получили `partial` и прошли индивидуальную SDK-проверку. Общее покрытие 86 компонентов: **5 partial / 44 not yet / 37 not needed / 0 ported**. Это не подтверждённый игровой запуск; см. [COMBINED_WORLDGEN_RU.md](COMBINED_WORLDGEN_RU.md).

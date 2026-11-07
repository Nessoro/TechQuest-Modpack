# TechQuest Horizon Port Lab

**Начало экспериментального переноса; НЕ готовая Horizon-сборка.** Создано в отдельной ветке experiment/horizon-port-lab от main. Основной TechQuest 0.3.2 и экспериментальный PR #5 NeoForge 0.3.3 не изменяются.

## Уже сделано

1. [Снимок NeoForge 0.3.3](source/techquest-0.3.3-candidate.json): все моды из PR #5 на 7 ноября 2026 г. (commit 07eb420ca0c7124c7d7d75ebb125508c4d6731fe); это **не** готовый Horizon-модпак.
2. [План по каждому моду](tools/port_inventory.py): offline JSON/Markdown-отчёт с классификацией. Команда: `python horizon/tools/port_inventory.py`. Все реальные статусы Horizon — **unverified**, количество перенесённых сторонних модов — **0**.
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

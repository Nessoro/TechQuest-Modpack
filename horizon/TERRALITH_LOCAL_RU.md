# Terralith: локальный пробный перенос генерации мира на Horizon

**Статус: эксперимент, не игровой порт.** Цель — расширить Horizon Edition за пределы 4 частично перенесённых модов YUNG's и проверить ключевой мод генерации биомов Terralith.

Источник: в официальном [отчёте Horizon по TechQuest](OFFICIAL_INVENTORY.md) Terralith находится в категории **data-tier**, но на начальном этапе имеет статус `not yet`. Для переноса используются оригинальный хеш-проверенный `.mrpack` из [TechQuest Actions #42372848633](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42372848633) и официальный `horizon-port-pack` по зафиксированному коммиту.

Workflow: [horizon-terralith-local.yml](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/horizon-terralith-local.yml).

Проверка выполняет `import`, `inventory`, `fetch terralith`, повторный `inventory --offline`, `carry terralith`, `report`, затем официальный `cargo-horizon-mod build` и `check --json` для временного `terralith.hmod`.

Технические критерии:
- Из Modrinth получен исходный файл, его путь и метаданные подтверждены официальной инвентаризацией.
- Успешно создан каталог `carry` с `horizon-mod.toml` и файлами данных.
- Официальный SDK принимает сформированный временный `.hmod` как content API 0.2.
- По итогам workflow доступны только `coverage.md`, `coverage.json` и `sdk-check.json`. **Никаких Terralith JAR, исходников, текстур, структур, HMOD не выкладывается**.

**Лицензия Terralith не рассматривается как универсальное разрешение на свободное перераспространение:** даже после успешного SDK нельзя публиковать собственный сборочный `.hmod` или модифицированные ресурсы без проверки конкретных условий автора и допустимых способов распространения.

**Что ещё отсутствует:** реальная загрузка Horizon 26.3, генерация биомов и структур, проверка цветовых карт, переходов между биомами, совместимости с YUNG's, проверка сохранений и мультиплеера. SDK-проверка касается формата/структуры, а не паритета генерации Minecraft 1.21.1.

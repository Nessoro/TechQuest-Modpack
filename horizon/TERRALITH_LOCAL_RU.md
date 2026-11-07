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

## Результат запуска — 7 ноября 2026

**[GitHub Actions #42384762013](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42384762013) — success.** Официальный `horizon-port-pack` скачал и проверил оригинальный `Terralith_1.21.1_v2.6.2_Neoforge.jar`, после чего локально перенёс **1 895 файлов исходных данных** (с `horizon-mod.toml` в итоге **1 896 файлов**). При преобразовании отчёт показывает 6 обновлённых рецептов, 43 таблицы лута и **124 файла outside**. Затем официальный `cargo-horizon-mod build/check --json` успешно проверил временный `terralith.hmod`.

Результат этого **отдельного** прогона: **1 partial / 48 not yet / 37 not needed**. Архив отчётов без содержимого мода: [Terralith-LOCAL-SDK-Report-ONLY](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42384762013/artifacts/13579495044).

Важно: это не единый прогон со всеми четырьмя модулями YUNG's. В сумме в отдельных технических тестах имеются **пять отдельных SDK-валидных частичных пакетов**, но не доказана совместимость этих пяти между собой, с Horizon в игре или с Minecraft 26.3. `outside` и лицензия Terralith требуют анализа до любого распространения.

# TechQuest 0.3.3 — Refined Storage / JEI Integration 1.0.0

## Область изменения

**Ветка:** `feat/micro5-refined-storage-jei-033`; база — `feat/micro5-opac-claims-033` (PR #43). Новое дополнение оформлено в отдельном **draft PR #45**, без изменения `main` и текущего опубликованного релиза.

Предложение: [Issue #44](https://github.com/Nessoro/TechQuest-Modpack/issues/44).

- Minecraft Java **1.21.1**, NeoForge **21.1.264**, Java **21**.
- [Официальный Modrinth 1.0.0, NeoForge](https://modrinth.com/mod/refined-storage-jei-integration/version/BYZmHubv) — ID проекта `VzR5wiLo`, ID версии `BYZmHubv`, лицензия MIT.
- Официальный файл `refinedstorage-jei-integration-neoforge-1.0.0.jar` (58 343 байта).
- SHA-512: `95f91c5d634dd144c6acb8dcf946df47a1c09d348e987b00469acc8b5977c09a02f9810cc2d0636d07053c46f029cc3403c52c0759968a6a4673d643fd1543c2`.
- SHA-1: `40dd3e88285159c99d32f6b677af4d214f58b906`.
- Хеши/зависимости проверены **прямым запросом к официальному Modrinth API** через успешный GitHub Actions metadata probe 14.11.2026.

## Зависимости

Для этой версии Modrinth сообщает две **обязательные** зависимости по ID, *без жёстко запрошенных version_id*:

1. `u6dRKJwZ` — **JEI 19.64.0.455** уже установлен в TechQuest, файл `jei-1.21.1-neoforge-19.64.0.455.jar`.
2. `KDvYkUg3` — **Refined Storage 2.0.9** уже установлен, файл `refinedstorage-neoforge-2.0.9.jar`.

Новые библиотеки не добавляются. Applied Energistics 2 (AE2), Refined Storage, Open Parties and Claims, Xaero, IC2 Nostalgia, Create, Mekanism, BuildCraft и другие существующие моды **не удаляются**. Отдельную установку старых версий JEI/RS не допускать.

## Проверки

- `modlist.json`: новая обязательная запись клиент+сервер и exact Modrinth pin (SHA-512).
- `tests/test_refined_storage_jei_integration.py`: платформа, сохранение RS 2.0.9, JEI 19.64, AE2, OPAC, точный JAR и `.mrpack` без дубликатов.
- `.github/workflows/build-alpha.yml`: проверка фактических JAR SHA-512 для нового аддона и его существующих зависимостей на клиенте и сервере, проверка индекса `.mrpack` и включения аддона в Windows GUI.
- `.github/workflows/smoke-client.yml`: загрузка точного полного профиля, автоматизированный запуск реального клиента Minecraft до TitleScreen в Xvfb, сохранение логов. Это **не равно** тесту функций мода в игре.

### Приёмка в реальном игровом мире — остаётся выполнить

1. На чистом тестовом мире создать контроллер, Crafting Grid и Pattern Grid в Refined Storage.
2. Проверить доступность JEI, выбор рецепта, перенос ингредиентов из JEI в обе сетки, показ отсутствующих компонентов и их автокрафт.
3. Проверить клавиши R/U, синхронизацию поиска JEI ↔ Grid, перенос ингредиентов в фильтры.
4. Проверить отсутствие конфликтов с AE2, механиками контейнеров, сохранением и повторным открытием мира.
5. Проверить подключение к выделенному серверу с **точно одинаковыми JAR** у клиентов, мультиплеер, TPS/MSPT и игровые ошибки.
6. Проверить переустановку GUI без удаления существующих миров, конфигураций и карты Xaero.

**Без реальной игры нельзя объявлять полную совместимость.** Не сливать PR, не заменять текущий релиз, не удалять миры или настройки. Для тестирования использовать отдельный профиль и резервную копию.

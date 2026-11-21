# Следующая фаза: официальная SDK-проверка четырёх YUNG's content-модулей

В отчёте [групповой конвертации YUNG's](YUNG_BATCH_RU.md) подтверждено **4 частичных переноса** и **686 файлов промежуточных данных**, но это только работа конвертера `horizon-port-pack`. Новый workflow [Horizon YUNG converted content SDK validation](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/horizon-yung-sdk-validation.yml) проверяет, примет ли эти данные **официальный Horizon Content API 0.2**.

Пайплайн:
1. Скачать оригинальный `.mrpack` из TechQuest Actions #42372848633 и собрать официальный Horizon `horizon-port-pack` + `cargo-horizon-mod` с закреплённой ревизии `c78187dffffb60f31517eadcb87413386e8ce729`.
2. Локально скачать только четыре JAR YUNG's по источникам/хешам Modrinth. Повторить `inventory` после скачивания, поскольку ID CurseForge/Modrinth отличается от NeoForge-ID внутри JAR.
3. Перенести данные в четыре временные папки `carry/` (доступны только ephemeral GitHub runner).
4. Для каждого мода запустить официальный `cargo-horizon-mod build` и `cargo-horizon-mod check --json`. Проверяющий скрипт `horizon/tools/validate_yung_sdk.py` фиксирует, сколько файлов собралось, наличие манифеста и фактический вывод SDK.
5. Публиковать только `sdk-validation.json` и `coverage.*` — **не** переносимые структуры, ассеты, исходные JAR или собранные сторонние `.hmod`.

Критерии: успешный SDK — **только** валидность контейнера с контентом для официального парсера Horizon. Для смены статуса `partial` на `ported` по-прежнему требуются реальные проверки генерации структуры в Horizon 26.3, loot/пулов и данных, игровой сервер и лицензии.

Если какая-либо проверка не пройдёт, workflow завершится ошибкой и опубликует причину для каждого мода в JSON; это диагностический результат, а не потеря уже конвертированных данных.

Исходный NeoForge 0.3.2 и 0.3.3 PR #5 не изменяются.

## Подтверждённый результат проверки (7 ноября 2026)

[GitHub Actions #42384517149](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42384517149) завершился **успешно: официальный Horizon SDK принял все 4/4 промежуточных content-модуля**.

| Исходный NeoForge мод | Временных файлов в папке carry | Официальный SDK |
| --- | ---: | --- |
| YUNG's Better Dungeons (`betterdungeons`) | 313 | `sdk_validated` |
| YUNG's Better Strongholds (`betterstrongholds`) | 137 | `sdk_validated` |
| YUNG's Better Mineshafts (`bettermineshafts`) | 33 | `sdk_validated` |
| YUNG's Better Nether Fortresses (`betterfortresses`) | 203 | `sdk_validated` |

CI-артефакт: [TechQuest-Horizon-YUNG-SDK-Validation-METADATA-ONLY](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/42384517149/artifacts/13578703994), без копий сторонних файлов.

**Ограничение:** официальный конвертер обнаружил общий namespace `yungsapi`, который запрашивали Better Dungeons и Better Fortresses, и не включил его ни в один мод, чтобы исключить конфликт владельцев. В отчёте конвертации также отмечены 8 файлов как `outside` (суммарно по четырём модам); эти потери надо изучить перед реальным запуском. Формат проверен, но генерация, зависимости и игровые механики ещё **не проверены**. Статус покрытия остается `partial`, не `ported`.

# TechQuest 0.3.3 — журнал разработки

## 2026-11-14 — micro3: RPG Core removal, Compatibility retained

**Техническое задание:** Technical Specification No. 1 (14.11.2026).  
**Репозиторий:** `Nessoro/TechQuest-Modpack`.  
**Только рабочая ветка:** `fix/micro3-remove-first-party-mods-033`, draft PR #30; база `feat/micro2-rpg-core-033`.  
**Состояние на начало ревизии:** `06c07dd931e2180a7e08d62081824758e030dbb6`.  
**Версии:** Minecraft Java 1.21.1, NeoForge 21.1.264, Java 21.

### Проверка исходного состояния

- В draft PR #30 уже исключена генерация `techquest-rpg-core-0.1.0.jar` из `build_pack.py`; `techquest-compat-1.0.0.jar` остаётся в клиентской, серверной сборке и `.mrpack`.
- `scripts/install_server.py` ранее писал новые JAR прямо в существующий каталог, не удаляя старые файлы. Это оставляло риск повторного появления RPG Core/PMMO при обновлении сервера.
- В GUI `ActivateStagedMods` ранее удалял предшествующий бэкап перед активацией; сбой повторного обновления мог уничтожить прежнюю точку возврата.
- Отсутствовал этот журнал и проверка полного равенства инвентаря JAR клиент/сервер/`.mrpack`.

### Изменения в micro3 (только эта ветка)

- `build_pack.py`: явный запрет включения RPG Core и PMMO в Modrinth-index, при сохранении генератора Compatibility.
- `scripts/mods_transaction.py` (новый): загрузка во временную папку, активация нового `mods` через переименование и одна постоянная точка `.techquest-previous-mods`. Старый бэкап временно сохраняется в `.techquest-backup-rotation` и восстанавливается при исключении.
- `scripts/install_client.py`: повторное обновление только профиля с маркером TechQuest, удаление устаревших модов через полную замену набора; существующие `saves`, `config` и `options.txt` не перезаписываются.
- `scripts/install_server.py`: транзакционная замена серверных модов, запрет неизвестного профиля, сохранение `eula.txt`, `world`, серверных настроек; Superb Warfare патчится только во временной серверной копии. Требуется конкретный NeoForge 21.1.264.
- `windows-installer/Program.cs`: безопасная ротация бэкапа при повторном обновлении, запрет RPG/PMMO в манифесте и overrides, самотест двух установок и аварийного возврата, актуальная подпись micro3.
- `scripts/audit_micro3_packages.py` (новый): сверка клиента, сервера и `modrinth.index.json`, проверка идентичного Compatibility JAR и наличия ресурсов рецептов Create–IC2 и Mixin Better Zoom. Создаёт `output/micro3-package-audit.json`. **Это структурная проверка, не игровая.**
- `.github/workflows/build-alpha.yml`: запускает package-аудит; включает `scripts/mods_transaction.py` в оба Python bootstrap-архива; проверяет запрещённые JAR перед сборкой Windows GUI.
- `tests/test_micro3_upgrade.py` (новый) и `tests/test_rpg_core.py`: негативные и позитивные тесты, повторное обновление, сохранение настроек и миров, искусственный сбой и восстановление предыдущего набора.
- `README.md`, `docs/MICROPATCH_MICRO3_RU.md`, `docs/INSTALL_0.3.3_PC_RU.md`: инструкции и риски обновления.
- `modlist.json`, игровой конфиг и списки BuildCraft, Create, IC2, Mekanism, AE2, FTB Ultimine, Physics Mod, Incoming и Patchouli **не изменялись**.

### Проверка и свидетельства

- Команды для воспроизведения: `python -m unittest discover -s tests -v`; `python build_pack.py`; `python scripts/audit_micro3_packages.py`. На Windows: `dotnet publish windows-installer/TechQuestInstaller.csproj -c Release -r win-x64 --self-contained true`, затем `TechQuestInstaller.exe --self-test`.
- Результаты независимых GitHub Actions следует оценивать по **точному commit SHA**, не по зелёной проверке другого коммита. Ранее возникали красные сборки при промежуточных коммитах; обнаруженные проблемы с bundling bootstrap и устаревшими тестовыми утверждениями внесены в исправления.
- До получения полного успешного прохода CI нельзя считать пакет, EXE и антивирусную проверку завершёнными.
- Runtime: фактический старт Minecraft до главного меню, создание мира, рецепты Create↔IC2, Better Zoom, старт сервера до `Done` и подключение клиента для этой ревизии **не подтверждены**. `eula.txt` не менялся; любое принятие EULA — только вручную владельцем.
- Отдельный дефект добычи блоков вверх не исправлялся и не связан автоматически с удалением RPG Core.

### Риски, ограничения и следующий шаг

1. Проверить итоговый GitHub Actions `Build TechQuest alpha`, самотест Windows GUI и `TechQuest-Security-Audit` на одном SHA; приложить отчёты и инвентарь JAR в draft PR #30.
2. Испытать `TechQuestInstaller.exe` в чистом Windows-профиле и поверх управляемого micro2 с RPG Core; провести ручное восстановление и проверку после имитированного сбоя. Не открывать старый мир до отдельного backup.
3. В реальной игре проверить меню, свежий мир, рецепты, Better Zoom; отдельно проверить сервер и клиент **после** самостоятельного принятия EULA.
4. По проблеме самопроизвольной добычи вверх: создать отдельную задачу с последовательностью обычное копание без Ultimine → вертикальная колонка Ultimine → влияние Physics Mod и видео/логом.

**Ограничение:** не объединять PR #30, не менять опубликованную micro2 preview и не выпускать release без отдельного согласования владельца. Статус micro3 — **кандидат, runtime не проверен**.

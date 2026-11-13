# TEST — отдельный диагностический мини-модпак TechQuest

TEST — эксперимент для выяснения причины самопроизвольного разрушения блоков. Он не обновляет и не заменяет основной TechQuest. Программный код находится только в подкаталоге test/ репозитория; исходный modlist.json, основной установщик и текущие миры не меняются.

Требования: Windows 10/11 x64, Minecraft Java 1.21.1, NeoForge 21.1.264, Java 21, официальный Minecraft Launcher.

## Состав

Четыре игровых мода (доступны для независимого или совместного теста):

| Мод | Версия | Источник |
| --- | --- | --- |
| Simple Vein Miner (конкретный аналог «Vein Mining») | 1.2, Modrinth PrOVZx3c | https://modrinth.com/mod/vein-miner-neoforge/version/1.2/ |
| FTB Ultimine (NeoForge) | 2101.1.15, официальный FTB Maven | https://www.curseforge.com/minecraft/mc-mods/ftb-ultimine-forge |
| Physics Mod Lite | 3.0.35, Modrinth wudTG1nk из TechQuest | https://modrinth.com/mod/physicsmod |
| Incoming: Air Strikes & Nukes | 3.10.4, GitHub Release | https://github.com/zentixua/incoming/releases/tag/v3.10.4 |

Для работы FTB Ultimine установщик также ставит FTB Library 2101.1.37 и Architectury API 13.0.11 (Modrinth 1IiqEQGl). Это служебные зависимости; поэтому в режиме TEST_ALL в папке mods шесть, а не четыре JAR.

Версии закреплены, файлы качаются при установке напрямую с первичных источников. Для Modrinth проверяются SHA-512 из API закреплённой версии, для Incoming — закреплённый SHA-256 из основного modlist.json, для FTB Library — SHA-1 из официального Maven, для FTB Ultimine — также встроенный контрольный SHA-1. JAR не распространяются в репозитории.

## Сборка Windows-установщика

Откройте Actions → Build TEST isolated installer:
https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/build-test.yml

Откройте успешный запуск ветки feat/test-isolated-mining-pack или его PR. В Artifacts скачайте TEST-Windows-Installer и извлеките TEST.exe. Для GitHub Actions Artifacts может требоваться вход в GitHub.

Стандартные действия и релизы TechQuest 0.3.3 не меняются.

## Установка и запуск

1. Запустите TEST.exe; папка тестов фиксирована: %LOCALAPPDATA%\TechQuest\TEST.
2. Выберите сценарий (по умолчанию TEST_ALL) и нажмите «Установить TEST отдельно».
3. В официальном Minecraft Launcher создайте НОВУЮ установку с NeoForge 21.1.264, не редактируйте основную TechQuest.
4. В поле Game Directory укажите путь из уведомления установщика, например %LOCALAPPDATA%\TechQuest\TEST\TEST_ALL.
5. Запустите TEST в новом тестовом мире. Если необходима проверка на старом мире, сначала создайте резервную КОПИЮ мира и поместите её в папку saves нового профиля.

После установки любой сценарий остаётся нетронутым: повторный запуск не обновляет и не перезаписывает его файлы. Можно выбрать другой сценарий. Проверенные загрузки переиспользуются из %LOCALAPPDATA%\TechQuest\TEST\.cache.

## Диагностические сценарии

| Профиль | Что проверяем |
| --- | --- |
| TEST_VEIN | Один Simple Vein Miner без остальных |
| TEST_ULTIMINE | FTB Ultimine и необходимые две библиотеки |
| TEST_PHYSICS_OFF | Physics с collapse=false |
| TEST_PHYSICS_ON | Physics с collapse=true (использовать только отдельный тестовый мир) |
| TEST_INCOMING | Только Incoming |
| TEST_ALL | Все четыре игровых мода с collapse=false |

В каждом мире поставьте столб из трёх каменных блоков, сломайте нижний без специальных клавиш и сравните поведение. Повторите с землёй, деревом и рудой. В Simple Vein Miner по умолчанию Left Shift удерживает массовую добычу, а Right Shift переключает её состояние. Различайте мгновенное исчезновение и физическое падение блоков.

## Ограничения и безопасность

- TEST не устанавливает NeoForge автоматически. Требуются Java 21, Minecraft 1.21.1 и NeoForge 21.1.264.
- Не меняет launcher_profiles.json или существующие папки основного TechQuest.
- Не имеет доступа к основным сохранениям; использует собственные новые папки профилей.
- Тестовая версия TEST_PHYSICS_ON специально включает обрушение — не запускайте её с единственной копией ценного мира.
- Успешная компиляция Windows EXE не доказывает запуск Minecraft или полную совместимость модов; эти проверки должны быть проведены в игре.

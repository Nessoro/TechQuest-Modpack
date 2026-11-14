# TechQuest: Industrial Frontier

## 🌐 [Открыть сайт TechQuest →](https://nessoro.github.io/TechQuest-Modpack/)

**[Установка и скачивание](https://nessoro.github.io/TechQuest-Modpack/#download) · [Каталог модов](https://nessoro.github.io/TechQuest-Modpack/#mods) · [Ошибки и предложения](https://nessoro.github.io/TechQuest-Modpack/#feedback)**

> **Minecraft Java 1.21.1 • NeoForge 21.1.x • Java 21 • сервер с друзьями**

TechQuest — большая комплексная сборка вокруг **BuildCraft Community Edition** и **Industrial Craft 2: Nostalgia**. Дополнительно в план включены Create, Mekanism, Modern Industrialization, AE2, магия, развитие, новые мобы и миры.

**Версия: `0.3.3-alpha` — единый тестовый профиль Optimized.** 07.11.2026 владелец подтвердил одиночный мир и игру на `535de72`. Выделенный сервер, весь набор механик и производительность этой версии ещё не подтверждены. Подробности: [проверки 0.3.3](QA_0.3.3_RU.md). Не переносите старый мир без резервной копии.

**Единая тестовая сборка 0.3.3 — изменения PR #5 и #15.** В неё объединены PR #10/#11/#19/#20: Physics Mod Lite с ограниченными обломками, резерв установки NeoForge, зум **Z + колесо**, Controlling, Aquamirae из PR #15. Отдельные ветки этих PR — сохранённые этапы работы, а не разные редакции модпака.

**Воспроизводимый состав и настройки:** версии, SHA-512 и стороны используемых проектов Modrinth закреплены, автоматическая подмена последними релизами отключена. Исправлен заголовок `options.txt` (`version:3955`), чтобы Minecraft загружал современные клавиши и Fast/6/5/60. Существующие пользовательские файлы сохраняются: для новых стартовых настроек используйте новую папку или настройте прежнюю через меню. [Как проверяется сборка](docs/REPRODUCIBLE_BUILDS_RU.md).

**HP и взрывы:** в новой установке числовое текущее/максимальное HP находится сверху по центру, дубль HP/брони Jade выключен. Множитель длительности контузии Explosion Overhaul — 0.25; экранный эффект и тряска Incoming — 0.35, затяжное повреждение слуха выключено. Настройки прочитаны настоящим клиентом до меню; взрывы в мире ещё требуют испытаний. [Подробности и применение к прежнему профилю](compat/client-hud/README.md).

**Камера Incoming:** по умолчанию **N** — камера своего снаряда / следующий; **Shift** — выход, **F5** — смена вида. При переназначении ищите «Камера снаряда» в управлении мода.

**Micro3 (кандидат):** по уточнённому решению владельца из будущих клиентских и серверных сборок удаляется только `TechQuest RPG Core 0.1.0`. `TechQuest Compatibility 1.0.0` **остаётся**: рецепты Create ↔ IC2 и исправление раннего запуска Better Zoom сохраняются. Project MMO также не возвращается. Остальные моды и миры не затрагиваются. Предыдущие micro1/micro2 сохраняются как история. [Изменения micro3](docs/MICROPATCH_MICRO3_RU.md).

**Кандидат micro5 (отдельный PR):** добавлен оригинальный **Iskander Rocket Mod 2.0.1** (NeoForge 1.21.1) с официального Modrinth: баллистическая ракета, пульт X/Z и большой кратер. Точный version ID и SHA-512 закреплены; мод устанавливается клиенту и серверу. Это **не Iskandert's Library** и не Colossal Reactors. Мод крайне разрушителен: реальные испытания только в отдельном тестовом мире. [Инструкция micro5](docs/MICROPATCH_MICRO5_ISKANDER_RU.md).\n\n**Кандидат micro4 (отдельный PR):** добавлены Trash Cans (мусорки) и Pretty Pipes (предметные трубы без двигателей), с закреплёнными зависимостями. **Исправление:** ошибочно выбранный Colossal Reactors и его библиотеки удалены. Требуемый **FTB Industrial Contraptions** пока не включён: официальный релиз отсутствует для Minecraft 1.21.1 / NeoForge. TechQuest Compatibility сохранён; RPG Core исключён. Улучшенные солнечные EU-панели IC2: Nostalgia ожидают проверки совместимости. [Описание micro4](docs/MICROPATCH_MICRO4_RU.md).

**Авиация:** Superb Warfare и Incoming остаются в составе. MCHeli Modern Port, TaCZ и ParCool исключены по решению владельца («не нужен»). Геймпад для самолёта пока не реализован. [Состояние авиации](docs/AIRCRAFT_0.3.3_RU.md) · [Как работает SAM Incoming](docs/INCOMING_SAM_RU.md) · [Физика](docs/PHYSICS_TESTING_RU.md) · [NeoForge через GUI](docs/NEOFORGE_FALLBACK_RU.md) · [Клавиши и зум](docs/CONTROLS_RU.md).

**Дополнение для тестирования 0.3.3:** AcceleratedMcWarfare 1.0.4 Alpha (NeoForge 1.21.1) доступен через кнопку ручного импорта в экспериментальном Windows Installer; основной JAR скачивается пользователем с официальной страницы CurseForge. Файл не распространяется в TechQuest из-за ограничений CDN и лицензии. Подробности: [AMW — установка и тесты](docs/AMW_TESTING_RU.md).

> **Новый экспериментальный курс TechQuest 0.3.3:** больше приключений и исследования без удаления BuildCraft, IC2, Create и Mekanism. В PR #5 добавлены The Aether, Deeper and Darker, When Dungeons Arise, Artifacts, Wyrmroost (драконы), Legendary Monsters и Twisted Mobs (крупные монстры), Forgematica (схемы), Explorer's Compass и крепости YUNG's. Подробности в [плане Adventure & Exploration](docs/ADVENTURE_EXPLORATION_RU.md). Это тестовая ветка, не стабильный релиз.

> **Схемы, другие драконы, гиганты:** в тестовый PR #5 добавлены Wyrmroost 1.4.1, Legendary Monsters 2.2.4, Twisted Mobs и клиентские Forgematica/MaFgLib 0.4.3. IceAndFire CE удалён. Инструкция: [план и риски](docs/SCHEMATICS_DRAGONS_GIANTS_RU.md). Ben's Titans остаётся неподтверждённым кандидатом и в сборку не добавлен.

### Тестовая версия TechQuest 0.3.3 для Windows 11

Альфа 0.3.3 собирается в [GitHub Actions — Build TechQuest alpha](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/build-alpha.yml) для актуальной ревизии исходников. Найдите **успешный запуск последнего коммита**, артефакт `TechQuest-Windows-GUI-Installer` → `TechQuestInstaller.exe`. Сверяйте версию и commit выбранного артефакта. Отчёт `TechQuest-Security-Audit` должен относиться к тому же commit SHA.

GUI устанавливает единый Optimized-профиль без Python/консоли. В кандидате micro3 `TechQuest Compatibility` по-прежнему входит в пакет для работы Create–IC2 и исправления запуска Better Zoom, а `TechQuest RPG Core` исключён; запуск обновлённой сборки всё ещё необходимо проверить. Выбирайте новую пустую папку, установите Java 21 и NeoForge 21.1.264, укажите Game Directory в официальном Launcher. Подробные шаги: [Установка тестовой 0.3.3](docs/INSTALL_0.3.3_PC_RU.md). На сервере Superb Warfare локально исправляется после проверки оригинального SHA. Прежние установки не обновляются автоматически.

Перед выдачей EXE CI проверяет обязательные библиотеки и диапазоны Minecraft/NeoForge внутри JAR,
включая штатную матрицу совместимости FML 4.0.45. Исправлена установка Lithostitched на клиент
для Terralith. Все способы установки используют одинаковые настройки Fast/6/5/60 FPS;
существующий `options.txt` сохраняется. Подробности и ограничения: [проверка совместимости](compat/README.md).

> **Исключены из сборки:** MCHeli Modern Port, TaCZ и ParCool. Причина: «не нужен». Их JAR и оружейные паки не входят в актуальный профиль.

## Навигация

| Раздел | Для чего |
| --- | --- |
| [`modlist.json`](modlist.json) | Список кандидатов, основных и необязательных модов |
| [`build_pack.py`](build_pack.py) | Резолвер Modrinth-зависимостей и сборщик клиентских/серверных файлов |
| [`MODPACK_README_RU.md`](MODPACK_README_RU.md) | Пошаговая установка на ПК и сервере |
| [`ПУБЛИКАЦИЯ_И_САЙТ.md`](ПУБЛИКАЦИЯ_И_САЙТ.md) | Публикация репозитория и сайта, в том числе с телефона |
| [`docs/`](docs/) | Сайт сообщества для GitHub Pages |
| [Баг-репорты](https://github.com/Nessoro/TechQuest-Modpack/issues/new?template=bug_report.yml) | Форма ошибки с полями окружения и воспроизведения |
| [Предложения модов](https://github.com/Nessoro/TechQuest-Modpack/issues/new?template=mod_request.yml) | Форма нового мода и его совместимости |

## Запуск сайта на GitHub Pages

1. Репозиторий уже создан: `Nessoro/TechQuest-Modpack`.
2. В GitHub откройте **Settings → Pages → Build and deployment → Deploy from a branch**.
3. Выберите ветку `main`, папку `/docs`, нажмите **Save**.
4. Сайт опубликован по адресу `https://nessoro.github.io/TechQuest-Modpack/` (GitHub Pages build завершился успешно 17.10.2026).
5. Убедитесь, что вкладка **Issues** включена в Settings → General → Features.

Сайт не хранит сообщения у себя: кнопка «Создать отчёт / Отправить предложение» открывает **заполненный черновик GitHub Issue**, затем пользователь входит в GitHub и подтверждает публикацию. На сайте также автоматически отображаются недавние открытые Issues.

**Если владелец или имя репозитория будут другими:** измените `REPO` в `docs/index.html` и URL в `.github/ISSUE_TEMPLATE/config.yml`.

## Проверка доступности модов

[Автоматическая проверка Modrinth](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/audit-mods.yml) запускается при изменении списка модов, вручную и по понедельникам.

Она создаёт отчёты `compatibility.md` и `compatibility.json` в артефакте `techquest-compatibility-report`: для каждого кандидата показывает наличие подходящей версии под Minecraft 1.21.1 / NeoForge. Это **не** игровой тест. Моды из CurseForge, включая IC2: Nostalgia, проверяются отдельно.

Для локального отчёта: `python scripts/audit_modlist.py`.

## Скачать TechQuest 0.3.3 Optimized (экспериментальная альфа этой ветки)

Теперь **только ОДНА версия клиента**: Full и Lite объединены в TechQuest Optimized. Сохранены BuildCraft, IC2: Nostalgia, Create, Mekanism, Modern Industrialization, AE2, магия, техника, мир и приключения. По умолчанию установлены клиентские Sodium, ImmediatelyFast, More Culling, BadOptimizations, Dynamic FPS, Entity Culling, FerriteCore и ModernFix; Iris исключён, шейдеры отключены.

На странице [Build TechQuest alpha](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/build-alpha.yml) откройте самый новый **успешный** запуск и скачайте из Artifacts:

- **TechQuest-Windows-GUI-Installer** — обычным игрокам на Windows 10/11: скачайте архив, извлеките `TechQuestInstaller.exe`, запустите двойным щелчком. **Без Python, PowerShell и консоли.**
- **TechQuest-1.21.1-alpha-build** — один `TechQuest_1.21.1_0.3.3_ALPHA.mrpack` для Prism/Modrinth-совместимых лаунчеров, общий серверный bootstrap, `jar-metadata-audit.json` и диагностические данные.
- **TechQuest-Security-Audit** — отчёт проверки хешей, ZIP и ClamAV, если этап безопасности завершился успешно. Проверка антивирусом не гарантирует отсутствие всех угроз.

### Установка через официальный Minecraft Launcher (без Prism)

1. Запустите графический `TechQuestInstaller.exe`; отдельного выбора Full/Lite больше нет.
2. Выберите **НОВУЮ пустую папку**, например `C:\\Games\\TechQuest-Optimized`, и нажмите «Установить моды». Старые `mods` не смешивайте с новыми.
3. Установите **Java 21** и **NeoForge 21.1.264** для Minecraft Java 1.21.1. В GUI есть кнопка запуска официального NeoForge Installer. Для установки NeoForge требуется соединение с Maven.
4. В Minecraft Launcher: **Установки → NeoForge 21.1.264 → Изменить → Папка игры**; укажите ту же папку, затем запустите NeoForge.
5. Если переносите прогресс, **сделайте копии** `saves`, `options.txt` и других нужных файлов перед переносом. Никогда не перезаписывайте старые моды и миры без резервной копии.

### Настройки и диагностика производительности

При новой установке автоматически создаётся `options.txt`: **Fast**, прорисовка **6 чанков**, дальность симуляции **5**, частицы **минимальные**, дальность сущностей **50%**, смешивание биомов **0**, mipmap **1**, лимит FPS **60**. Новая установка не трогает существующие настройки в старых папках.

При мощном ПК, но сильных лагах, важно отличать **FPS-просадки** (рендеринг) от **низкого TPS/подлагивания мира** (CPU, эффекты, взрывы, генерация, множество механизмов). Находясь в проблемном мире, откройте profiler `spark` через команду **`/sparkc profiler`**, подождите около 2 минут, затем **`/sparkc profiler --stop`**. Это официально рекомендованный способ диагностики NeoForge; отправьте ссылку из игры для точечного исправления.

Для серверного TPS требуется отдельное профилирование сервера. Автоматически выключать Superb Warfare, Burnt, Explosion Overhaul или Create мы не стали: это изменило бы геймплей/совместимость, а не только оптимизировало графику.

**Проверка игроком:** одиночный мир и игра на `535de72` подтверждены владельцем; воспроизводимых замеров FPS/TPS пока нет. Для первого запуска используйте новый мир и резервные копии. После [исследования](experiments/destruction/README_RU.md) в этой экспериментальной ветке включён Physics Mod Lite; эта добавка требует отдельного игрового теста.

## Incoming: Air Strikes & Nukes — включён в TechQuest 0.3.2

Добавлен [официальный релиз Incoming 3.10.4](https://github.com/zentixua/incoming/releases/tag/v3.10.4) от автора ZentixUA. Он добавляет дроны, крылатые ракеты, РСЗО, бомбардировщик B-2, ПВО и ядерные удары. Мод требуется **как клиенту, так и серверу** с одинаковой версией.

**Критическое требование:** Incoming 3.10.4 работает с NeoForge **21.1.264 или новее**, поэтому у TechQuest изменена версия загрузчика с 21.1.259 на **21.1.264** (Minecraft остаётся 1.21.1, Java 21). Для предыдущих профилей необходимо установить обновлённый NeoForge и использовать отдельную папку TechQuest 0.3.2. Не смешивайте старые и новые версии Incoming, иначе сервер может не принять клиента.

**Откуда скачивается:** официальный релиз автора на GitHub, жёстко закреплённый URL `incoming-3.10.4.jar` и SHA-256 из GitHub Release. Сборщик проверяет размер, SHA-256, ZIP/JAR-целостность и записывает SHA-1/SHA-512 в `.mrpack`. Binary не копируется в репозиторий TechQuest; ссылка загружается установщиком. Права автора — GPLv3.

**Производительность:** ядерные взрывы, разрушение блоков и большие залпы могут давать серьёзные просадки FPS/TPS даже на мощных ПК, особенно рядом с Superb Warfare, Burnt и Explosion Overhaul. Для начала создайте отдельный тестовый мир. Доступ к ядерным ударам лучше оставить администраторам и через конфиг Incoming ограничить разрушение блоков и пожары. Проводите испытания после резервного копирования; реальные игровые тесты совместимости ещё не проведены.

В `Путеводителе TechQuest` (внутриигровая книга Patchouli) добавлена страница про управление Incoming, ракеты, ПВО и влияние взрывов на производительность.

## Боевые моды и разрушения — тестовая интеграция

По запросу в каталог TechQuest для **NeoForge 1.21.1** добавлены:
- [Superb Warfare](https://modrinth.com/mod/superb-warfare) — вооружение, военная техника, авиация; версия `0.8.9.2` (обязательный компонент следующего тестового пакета).
- [Burnt + Additions](https://modrinth.com/mod/burnt) — пожарная система; ветка `1.10.2` (с Geckolib и Cloth Config API).
- [Explosion Overhaul: A new level of destruction](https://modrinth.com/mod/explosion-overhaul-a-new-level-of-destruction) от Vinlanx — взрывы с кинематографическими эффектами; экспериментальный порт `0.2.3.0-neoforge`.
- [DragonRise: Reforge](https://www.curseforge.com/minecraft/mc-mods/sbw-drr/files/9208025) — аддон военной техники к Superb Warfare, файл `dragonrise_reforge-1.5.1-release.jar`. **Ожидает загрузки оригинального JAR и закрепления SHA-512**, поэтому пока **не входит в автоматический .mrpack**. Для локальной проверки можно добавить файл вручную в папки `mods` клиента и сервера.

В список обязательных библиотек также добавлены `lithostitched` (1.8.0, для Terralith) и `irons-lib` (1.21.1-2.x, для Iron's Spells) после ошибки загрузки NeoForge 18 октября 2026 г.

**Важно:** сборка после этого изменения ещё не прошла полноценный тест запуска. Superb Warfare уже имеет разрушение блоков, а Burnt и Explosion Overhaul тоже изменяют мир. На тестовом сервере сначала отключите разрушение мира в Superb Warfare через `/sbw config explosionDestroy false`, сделайте отдельный мир/бэкап и оцените TPS/FPS. Explosion Overhaul для 1.21.1 — alpha; если установлен Create Aeronautics или Valkyrien Skies, автор рекомендует отключить async в конфиге Explosion Overhaul.

## Aquamirae в общей тестовой 0.3.3

[**Aquamirae 7.2.13**](https://modrinth.com/mod/aquamirae/version/lKu7coya) и **Fragmentum 5.4.0** включены в общий состав после объединения PR #15. Они обязательны на клиенте и сервере; GeckoLib 4.9.3 сохранён. Кандидат больше не является отдельной редакцией сборки. [Источники и игровой маршрут](docs/AQUAMIRAE_TESTING_RU.md).

Мод добавляет океанские структуры, существ и босса. Проверка их генерации, боя, сохранения, сервера и FPS/TPS остаётся в QA. По приоритету владельца сначала испытывается авиация, затем геймпад.

## Новое в 0.3 — карта, здоровье и руководства в Minecraft

В сборке **только один оптимизированный профиль** для всех игроков: полная промышленность, магия, оружие, путешествия и уже активные оптимизации. Не нужен выбор Full/Lite. Сторонние шейдеры Iris в основной пакет не включены.

- **[Xaero's Minimap](https://modrinth.com/mod/xaeros-minimap)** — миникарта и метки; **[Xaero's World Map](https://modrinth.com/mod/xaeros-world-map)** — полноэкранная карта (обычно клавиша M, проверьте назначение).
- **[Health Indicator TXF](https://modrinth.com/mod/health-indicator-txf)** — здоровье моба цифрами и полоской при наведении прицела. Дополнительно Jade показывает информацию о мобе/блоке под прицелом.
- **[Patchouli](https://modrinth.com/mod/patchouli)** — наш собственный русский **«Путеводитель TechQuest»**, где 15 разделов о первых шагах, BuildCraft, IC2, Create, Mekanism, AE2, оружии, исследованиях и оптимизации. Руководство находится в творческом инвентаре, вкладка «Инструменты и приспособления».
- **[Open Loader](https://modrinth.com/mod/open-loader)** — загружает небольшой datapack, который должен **выдать книгу каждому игроку при первом входе** и добавить рецепт восстановления книги из обычной книги и компаса. Автоматическая выдача ещё не проверена игровым запуском. При отсутствии книги проверьте логи Patchouli/Open Loader и наличие `config/openloader/packs/techquest_starter_guide.zip`.
- Вариант **Lithium** для оптимизации тиков проверяется сборщиком как необязательная зависимость. Его эффект и совместимость с промышленными модами требуют реальных испытаний.

Карта и индикаторы HP устанавливаются **только на клиент**; на сервере они не требуются. Руководство устанавливается и через Modrinth-импорт, и через графический Windows EXE: файл `patchouli_books/techquest_guide/book.json` и главы книги копируются в корневую папку выбранного профиля.

### Если тормозит даже на мощном компьютере

Отдельные моды оптимизируют отрисовку, но не исправляют перегрузки симуляции. В TechQuest сервер по умолчанию настроен на **view-distance=6, simulation-distance=5**. При тяжёлых битвах, авиации, модовых взрывах и огромных фабриках лаги могут быть вызваны TPS, а не FPS. Установлен **Spark**: используйте профилирование, чтобы найти тормозящий механизм или мод. Эксперименты проводите в новом мире; перед изменениями сохраняйте мир.

**Важное ограничение:** проверка совместимости по версии NeoForge и успешное скачивание JAR не означают отсутствие крашей, высокий FPS или успешный старт сервера. Новые карта, HP и книга ещё не прошли реальный игровой тест.

## IndustrialCraft — обязательный компонент

**BuildCraft и IndustrialCraft — главные моды TechQuest.** Владелец проекта загрузил оригинальный `industrial-craft-2-nostalgia-21.1.0-local.26.jar` в `manual-mods/`. Теперь сборщик автоматически:

1. Проверяет, что JAR присутствует и ZIP-архив не повреждён.
2. Добавляет IndustrialCraft в `modrinth.index.json` для **клиента и сервера** с хешами SHA-1/SHA-512.
3. Ссылается на закреплённый URL GitHub, так что лаунчер и серверный установщик скачивают одинаковые байты.
4. В ходе сборки отдельно проверяет загрузку файла и его хеши.

`.mrpack` содержит **ссылки, не JAR-файлы**. Наличие полной записи IC2 в манифесте ещё не означает успешный игровой запуск. Без разрешения всех правообладателей не следует произвольно перепубликовывать исходный IC2 или порт.

## Серверный smoke-test (по желанию администратора)

Для проверки фактического запуска NeoForge предусмотрен [ручной workflow Smoke-test NeoForge server](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/smoke-server.yml).
Он требует **явного согласия с Minecraft EULA** через переключатель `accept_minecraft_eula`. Workflow скачает моды, установит временный NeoForge 1.21.1, запустит сервер и приложит логи к результату.
**Ограничение:** теперь smoke-test включает загруженный IC2 Nostalgia и требует явного согласия администратора с EULA при ручном запуске. Прохождение теста старта сервера не заменяет испытаний клиента, подключения друзей и устойчивости индустриальных механизмов.

## Собрать файлы модпака

```sh
python build_pack.py --resolve-only   # Получить версии и выявить несовместимые/недоступные моды
python build_pack.py                  # Создать output/client, output/server и .mrpack
python scripts/sync_site_mods.py       # Обновить каталог сайта после правки modlist.json
python -m unittest discover -s tests -v
```

Для сборщика/bootstrap нужны интернет и Python 3.9+; для автотестов и аудита метаданных — Python 3.11+ (CI использует 3.12). Для Minecraft отдельно нужна Java 21. IndustrialCraft 2: Nostalgia уже лежит в `manual-mods/` и включается в клиент/сервер через зафиксированный GitHub URL; оригинальная [страница автора на CurseForge](https://www.curseforge.com/minecraft/mc-mods/industrial-craft-2-nostalgia/files/9217244). При распространении важно самостоятельно проверить соблюдение прав на порт и оригинальный IC2. **Не загружайте чужие JAR, файлы сервера или миры в git:** в `.gitignore` есть соответствующие исключения.

### Важные ссылки

- [BuildCraft Community Edition](https://modrinth.com/mod/buildcraft-community-edition) — официальный релиз `8.0.23+1.21.1+neoforge`.
- [IC2: Nostalgia](https://www.curseforge.com/minecraft/mc-mods/industrial-craft-2-nostalgia) — неофициальный порт, релиз 16.10.2026, требует дополнительных проверок.
- [GitHub Pages: publication source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

Этот проект не связан с Mojang/Microsoft. Все моды принадлежат их авторам; лицензии каждого проекта соблюдаются отдельно. Код сайта и собственные скрипты можно использовать по условиям `LICENSE`.

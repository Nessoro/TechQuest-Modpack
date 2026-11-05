# TechQuest: BuildCraft & IndustrialCraft — 1.21.1 / NeoForge

**Статус: alpha-заготовка с автоматическим разрешением зависимостей, не проверена запуском Minecraft.**

Версия единого профиля: 0.3.2-alpha (5 ноября 2026 г.). Сборка готовится для сервера друзей. Режим online-mode=true, white-list=true. Не используйте в существующем мире без полного бэкапа.

## Что внутри

- Техно-ядро: **BuildCraft Community Edition** 8.0.23 (строгий выбор для NeoForge 1.21.1), **Industrial Craft 2: Nostalgia** (автоматически через закреплённую ссылку GitHub), Create, Mekanism, Modern Industrialization, Applied Energistics 2. Immersive Engineering и некоторые расширения — дополнительные.
- RPG: Iron's Spells 'n Spellbooks, Apotheosis; дополнительно Skill Tree / Project MMO — если доступны подходящие файлы.
- Мобы и боссы: Naturalist, L_Ender's Cataclysm; дополнительно Mowzie's Mobs.
- Мир и исследование: Terralith, YUNG's Better Dungeons; дополнительные шахты.
- Комфорт: рюкзаки, Waystones, Jade, JEI.
- Оптимизация: FerriteCore, ModernFix, Sodium, Entity Culling, ImmediatelyFast, More Culling, BadOptimizations, Dynamic FPS; диагностика Spark.

**Важно:** полный перечень в `modlist.json`. Автоматический установщик проверяет конкретные файлы по версии Minecraft и загрузчику, подтягивает обязательные зависимости, сверяет хеши SHA512/SHA1 и сообщает об отсутствующих необязательных модах. Это **не гарантирует**, что все моды совместимы между собой — только то, что авторы опубликовали версии с нужными тегами.

## Первый запуск на Windows 11 — TechQuest Optimized 0.3.2

**Full и Lite объединены в один клиент.** В нём все прежние игровые механики и оптимизации Sodium, ImmediatelyFast, More Culling, BadOptimizations, Dynamic FPS, EntityCulling, ModernFix и FerriteCore. Отдельный Iris/шейдеры не устанавливаются.

1. В [GitHub Actions](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/build-alpha.yml) откройте **последнюю успешную** сборку и скачайте `TechQuest-Windows-GUI-Installer`.
2. Извлеките `TechQuestInstaller.exe`, запустите двойным щелчком. **Python и консоль не нужны**.
3. Укажите новую пустую папку для модпака и нажмите «Установить моды». Не используйте старый `.minecraft`, если в нём уже лежат Fabric-моды.
4. Установите Java 21 и NeoForge 21.1.264 (официальный графический установщик). В Minecraft Launcher откройте **Установки → NeoForge → Изменить → Папка игры** и укажите выбранную папку.
5. Запустите профиль NeoForge 1.21.1. Создайте пробный мир. Старые миры переносите только после резервной копии.

Для Prism Launcher/Modrinth-совместимого лаунчера также есть **единственный** файл `TechQuest_1.21.1_0.3.2_OPTIMIZED.mrpack` в артефакте `TechQuest-1.21.1-alpha-build`.

Установщик создаёт `options.txt` с быстрым режимом графики, 6 чанками прорисовки и минимальными частицами. Если на хорошем ПК лаги сохраняются, используйте профилирование Spark: `/sparkc profiler`, спустя пару минут `/sparkc profiler --stop`, отправьте полученную ссылку. Сканер безопасности и контрольные суммы не доказывают совместимость модов в игре.

## Запуск выделенного сервера

1. Используйте отдельную пустую папку на сервере. Скопируйте туда **содержимое** `output/server/` (папку `mods/`, `server.properties` и инструкцию). Не перезаписывайте существующие миры и конфиги.
2. Установите **NeoForge 21.1.264** с официального [Maven NeoForge](https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.264/neoforge-21.1.264-installer.jar). На Java 21 выполните `java -jar neoforge-21.1.264-installer.jar --installServer` в папке сервера.
3. Настройте `user_jvm_args.txt` (например `-Xms4G` и `-Xmx8G` при достаточном объёме памяти хоста).
4. Первый запуск `run.bat` на Windows или `./run.sh` на Linux создаст `eula.txt`. Только после принятия условий Mojang укажите `eula=true` и повторите запуск.
5. Поскольку **white-list=true**, разрешите друзей командами в консоли: `whitelist add NickName`. Добавьте операторов `op NickName` при необходимости. **online-mode=true оставьте включённым**.
6. Если друзья подключаются через Интернет, откройте порт 25565/TCP **только где это необходимо**, либо используйте закрытую сеть (например, Tailscale). Защищайте RCON и SSH, обновляйте бэкапы.

**Ограничения:** `.mrpack` содержит ссылки на оригинальные JAR, а не игровые файлы. Не содержит Minecraft, NeoForge, Java или готового мира. Запуск сервера и взаимодействия BuildCraft/IC2 с другими модами в этой среде не тестировались. `output` появляется только после запуска сборщика на компьютере с Интернетом.

## Важные тесты перед игрой

1. Клиент NeoForge запускается без ошибок и загружает главное меню.
2. Чистый выделенный сервер доходит до `Done` и не выгружает моды.
3. Игрок может зайти на сервер с **идентичным набором версий** (сверить с `versions-lock.json`).
4. BuildCraft: карьер, трубы, механизмы, перемещение предметов.
5. IC2: генератор, мацератор, кабель, зарядка электрического инструмента.
6. После создания резервной копии: сохранение и повторная загрузка мира с машинами, генерация новых чанков, базовый тест TPS во время работы карьера и заводов.

## Ссылки на первоисточники

- BuildCraft CE: https://modrinth.com/mod/buildcraft-community-edition
- IC2 Nostalgia: https://www.curseforge.com/minecraft/mc-mods/industrial-craft-2-nostalgia
- Create: https://modrinth.com/mod/create
- Mekanism: https://modrinth.com/mod/mekanism
- Modern Industrialization: https://modrinth.com/mod/modern-industrialization
- NeoForge Maven: https://maven.neoforged.net/releases/net/neoforged/neoforge/
- Modrinth API: https://docs.modrinth.com/api/

Авторские права на каждый мод сохраняются за правообладателями. Для IC2 используется закреплённая в GitHub копия исходного файла от автора порта, а не вложенный в ZIP JAR. Публичное размещение следует отдельно сверить с условиями распространения и правами оригинального IndustrialCraft.
## Интерфейс 0.3.2

Встроены Xaero's Minimap и Xaero's World Map. **Health Indicator TXF** показывает здоровье мобов **цифрами и полоской**; установлена русская книга «Путеводитель TechQuest» через Patchouli. Книга подготовлена для выдачи при первом входе в мир через Open Loader, но работу необходимо проверить в игре.

Для диагностики лагов используйте Spark: FPS — нагрузка на клиент, TPS — нагрузка на встроенный или выделенный сервер. Не пытайтесь увеличивать FPS отключением обязательных модов на стороне клиента при игре на сервере.

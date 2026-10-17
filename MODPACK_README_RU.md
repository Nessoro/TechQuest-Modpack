# TechQuest: BuildCraft & IndustrialCraft — 1.21.1 / NeoForge

**Статус: alpha-заготовка с автоматическим разрешением зависимостей, не проверена запуском Minecraft.**

Дата комплектации: 17 октября 2026 г. Сборка готовится для сервера друзей. Режим online-mode=true, white-list=true. Не используйте в существующем мире без полного бэкапа.

## Что внутри

- Техно-ядро: **BuildCraft Community Edition** 8.0.23 (строгий выбор для NeoForge 1.21.1), **Industrial Craft 2: Nostalgia** (вручную), Create, Mekanism, Modern Industrialization, Applied Energistics 2. Immersive Engineering и некоторые расширения — дополнительные.
- RPG: Iron's Spells 'n Spellbooks, Apotheosis; дополнительно Skill Tree / Project MMO — если доступны подходящие файлы.
- Мобы и боссы: Naturalist, L_Ender's Cataclysm; дополнительно Mowzie's Mobs.
- Мир и исследование: Terralith, YUNG's Better Dungeons; дополнительные шахты.
- Комфорт: рюкзаки, Waystones, Jade, JEI.
- Оптимизация: FerriteCore, ModernFix, дополнительные Sodium, Iris; диагностика Spark при наличии.

**Важно:** полный перечень в `modlist.json`. Автоматический установщик проверяет конкретные файлы по версии Minecraft и загрузчику, подтягивает обязательные зависимости, сверяет хеши SHA512/SHA1 и сообщает об отсутствующих необязательных модах. Это **не гарантирует**, что все моды совместимы между собой — только то, что авторы опубликовали версии с нужными тегами.

## Первый запуск на Windows 11

1. Установите 64-битную **Java 21** и Python 3.9+ (для сборщика). Требуются интернет и свободное место на диске.
2. **Скачайте IC2 Nostalgia самостоятельно** по [странице файла на CurseForge](https://www.curseforge.com/minecraft/mc-mods/industrial-craft-2-nostalgia/files/9217244), положите `industrial-craft-2-nostalgia-21.1.0-local.26.jar` в `manual-mods/`. На момент сборки это новый экспериментальный порт. Не ставьте второй IC2-порт с тем же `mod id`.
3. Дважды щёлкните `СОБРАТЬ_СБОРКУ.bat`. Скрипт делает запросы только к Modrinth API и к указанным CDN релизов, сохраняет `output/versions-lock.json`, скачивает моды и копирует IC2 из `manual-mods` в обе папки.
4. Для игрового клиента проще импортировать `output/TechQuest_1.21.1_0.1.0.mrpack` в **Modrinth App**, который установит NeoForge и моды из Modrinth. **После импорта вручную добавьте IC2 JAR в папку mods этого игрового профиля**: сторонний JAR не вложен в `.mrpack`. Альтернатива: создайте отдельный профиль NeoForge 1.21.1 и перенесите содержимое `output/client/mods/` в его `mods/`.
5. Выделите клиенту примерно 8–10 ГБ RAM. Для начала отключите шейдеры при проверке совместимости.

## Запуск выделенного сервера

1. Используйте отдельную пустую папку на сервере. Скопируйте туда **содержимое** `output/server/` (папку `mods/`, `server.properties` и инструкцию). Не перезаписывайте существующие миры и конфиги.
2. Установите **NeoForge 21.1.259** с официального [Maven NeoForge](https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.259/neoforge-21.1.259-installer.jar). На Java 21 выполните `java -jar neoforge-21.1.259-installer.jar --installServer` в папке сервера.
3. Настройте `user_jvm_args.txt` (например `-Xms4G` и `-Xmx8G` при достаточном объёме памяти хоста).
4. Первый запуск `run.bat` на Windows или `./run.sh` на Linux создаст `eula.txt`. Только после принятия условий Mojang укажите `eula=true` и повторите запуск.
5. Поскольку **white-list=true**, разрешите друзей командами в консоли: `whitelist add NickName`. Добавьте операторов `op NickName` при необходимости. **online-mode=true оставьте включённым**.
6. Если друзья подключаются через Интернет, откройте порт 25565/TCP **только где это необходимо**, либо используйте закрытую сеть (например, Tailscale). Защищайте RCON и SSH, обновляйте бэкапы.

**Ограничения:** modpack не содержит Minecraft, NeoForge, Java, сторонних JAR или готового игрового мира. Запуск сервера и взаимодействия BuildCraft/IC2 с другими модами в этой среде не тестировались. `output` появляется только после запуска сборщика на компьютере с Интернетом.

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

Условия распространения каждого мода принадлежат его автору. Сборщик скачивает файлы с первоисточников и не переупаковывает сторонние `.jar` в предоставляемый ZIP.
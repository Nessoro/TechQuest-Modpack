# TechQuest — общий чек-лист и гайд по поиску боссов

**Версия аддона:** 0.2, эксперимент. **Minecraft 1.21.1 / NeoForge 21.1.264**. Работает как datapack для Open Loader; дополнительный JAR не требуется.

## Что нового

- **34 отслеживаемые цели:** 14 Legendary Monsters (включая 2 мини-боссов), 11 L_Ender's Cataclysm (3 мини-босса), 4 Bosses of Mass Destruction, 3 Aether, Визер и Дракон Энда.
- **Автоматический общий прогресс для LAN** в том же мире. Победа, засчитанная Minecraft игроку, фиксируется в scoreboard и показывается всем друзьям в «Достижениях» (обычно L); позже подключившиеся также получают отметки. Разделы: Legendary (3 измерения), Cataclysm, Mass Destruction, Aether и обычные боссы.
- **Гайд по поиску** одновременно в описании каждого достижения и в новой ванильной книге «Охота на боссов». В книге есть названия структур, биомы, навигационные предметы и условия призыва.
- Книга выдаётся один раз на игрока при входе после установки; если потеряна, её можно изготовить из **книги + Ока Эндера** (JEI покажет рецепт).

## Установка для одиночного мира, открываемого в LAN

1. Сделайте резервную копию папки \`saves/<имя мира>\`.
2. **Полностью закройте Minecraft**.
3. Замените прежний \`techquest_boss_checklist.zip\` новым файлом **с тем же именем** в папке вашей сборки:
   \`config/openloader/packs/techquest_boss_checklist.zip\`.
4. **Не распаковывайте ZIP**. Не держите рядом старую копию с другим именем.
5. Загрузите мир, откройте вкладку достижений «TechQuest: охота на боссов». Книгу ищите в инвентаре после входа.
6. Откройте мир для сети как обычно: друзьям отдельный ZIP не нужен, если вы — хост.

Сохранённые результаты старых 14 противников остаются: пути достижений, фиктивные scoreboard-пользователи и имя objective \`tqb_kills\` **не изменены**.

## Разделы

### Legendary Monsters (14)

**Верхний мир:** Ancient Guardian (Ancient Stronghold / Eye Of Many Ribs); Overgrown Colossus (Mossy Temple / Eye Of Moss); Cloud Golem (Cloudy Temple / Eye Of Air); Dune Sentinel (Ruined Pyramid / Eye Of Sandstorm); Frostbitten Golem (Frostbitten Temple / Eye Of Frost); Possessed Paladin (Abandoned Crypt / Eye Of Ghost).

**Незер:** Skeletosaurus (Skeletosaurus Nest / Eye Of Bones); Lava Eater (Lava Eater's Nest / Eye Of Magma); Warped Fungussus (Warped Mushroom Nest, без отдельного Ока); Withered Abomination (Soul Fortress Remains / Eye Of Soul).

**Энд:** Chorusent (Ancient Tower Remains / Eye Of Chorus); Shulker Mimic (Shulker Tower / Eye Of Shulker); мини-босс Annihilation Pursuer (Space Station); The Obliterator (Space Station: Eye Crystal из Pursuer на Teleport Machine).

### L_Ender's Cataclysm (11)

**Основные боссы (8):** Ender Guardian, Netherite Monstrosity, Ignis, The Harbinger, The Leviathan, Ancient Remnant, Maledictus, Scylla.

**Мини-боссы (3):** Ender Golem, Ignited Revenant, Aptrgangr.

Поиск: Cataclysm Eyes для Ruined Citadel, Soul Forge, Burning Arena, Ancient Factory, Sunken City, Cursed Pyramid, Frosted Prison и Acropolis. В книге указаны условия призыва Игниса, Левиафана и Маледиктуса.

### Bosses of Mass Destruction (4)

Night Lich — Lich Tower в холодных биомах (Soul Star); Void Blossom — глубокая пещера (Void Lily); Nether Gauntlet — арена в Незере; Obsidilith — арена внешних островов Энда.

### The Aether (3)

Slider — Bronze Dungeon; Valkyrie Queen — Silver Dungeon; Sun Spirit — Gold Dungeon.

### Minecraft (2)

Визер и Дракон Энда.

## Правила и ограничения

- **Общий прогресс на мир**, а не на аккаунт между всеми серверами.
- **Одно засчитывание на вид босса**, а не счётчик повторных убийств.
- Убийство должно быть засчитано именно игроку (\`minecraft:player_killed_entity\`). Не все косвенные причины смерти (турели, лава, механизмы) дадут такой зачёт.
- Достижения, полученные *до установки первой версии*, не восстановятся сами. Старый прогресс версии 0.1 сохранится при замене ZIP.
- Названия и примерные места поиска справочные. Моды генерации мира TechQuest могут менять размещение структур; смотрите JEI и Explorer's Compass.
- **Тесты ZIP и GitHub Actions — это не проверка в игре**. Список новых ID требует проверки на настоящем клиенте с закреплёнными JAR (Cataclysm 3.33, BoMD 1.3.3, Aether 1.5.9). В старом мире могут не появиться структуры в уже исследованных чанках.

## Проверка с друзьями

1. Убедиться, что книга выдалась и все семь разделов видны.
2. Убить ранее не убитого босса Legendary Monsters и одного босса другого мода. В обоих случаях участники видят завершение достижения.
3. Выйти другу B, убить босса A, снова зайти другу B и убедиться в получении отметки.
4. Перезапустить Minecraft; проверить отметки и отсутствие выдачи второй книги.
5. Убедиться, что старые 14 отмеченных побед не сброшены.
6. Проверить рецепт книги + Око Эндера через JEI.
7. Открыть \`latest.log\` и проверить отсутствие ошибок парсинга advancement, loot_table, recipe.

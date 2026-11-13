#!/usr/bin/env python3
"""First-party, data-only TechQuest Patchouli guide and starter datapack.

The game guide is stored in patchouli_books/ next to mods/. A small Open Loader
datapack grants the guide to players upon first login and offers a cheap
crafting recipe for replacements. No third-party binaries or scripts run in
Minecraft from this module.
"""
import io
import json
import zipfile

BOOK = "techquest_guide"
BOOK_ID = "patchouli:" + BOOK

CATEGORIES = {
    "first_steps": ("Начало игры", "Основные советы по порядку изучения модов.", "minecraft:compass"),
    "industry": ("Промышленность", "BuildCraft, IC2, Create и механизмы.", "minecraft:piston"),
    "power": ("Энергетика и хранение", "Энергосистемы, Mekanism и AE2.", "minecraft:redstone"),
    "adventure": ("Оружие и приключения", "Мир, техника, магия и сражения.", "minecraft:iron_sword"),
    "exploration": ("Исследование и сокровища", "Новые измерения, подземелья и награды.", "minecraft:filled_map"),
    "navigation": ("Карта и интерфейс", "Миникарта, здоровье мобов и рецепты.", "minecraft:map"),
    "performance": ("Производительность", "Как снизить лаги и найти причину.", "minecraft:clock"),
}

# Key -> (category, icon, title, pages).
ENTRIES = {
    "controls_and_zoom": ("navigation", "minecraft:spyglass", "Зум и управление", [
        ("Зум Z + колёсико", "На новой установке удерживайте Z и вращайте колёсико в обе стороны. Отпустите Z для возврата обычного обзора. Без зума колёсико переключает предметы как обычно; HUD остаётся видимым. Настройки Better Zoom доступны через Моды → Better Zoom → Config."),
        ("Освободили Z", "Клавиша Z выделена для Better Zoom; увеличение миникарты Xaero — F9, первое улучшение Sophisticated Backpacks — F10. Клавиши можно изменить через Настройки → Управление. Установщик сохраняет существующий options.txt; при обновлении старой папки назначения нужно проверить вручную."),
        ("Конфликты", "Controlling добавляет поиск действий, список конфликтов и свободных клавиш. Совпадение может быть намеренным для разных состояний, но нестандартные оружейные действия требуют проверки в игре. Forgematica/MaFgLib используют также собственное меню горячих клавиш; общий экран не покрывает все их сочетания."),
        ("Xbox и джойстики", "Геймпад нужен только для управления самолётом. Такая интеграция пока не реализована: Controlify исключён из состава, поскольку добавляет общее управление Minecraft. После реализации будут проверены авиационные оси, мёртвые зоны и инверсия. Обычная игра остаётся на мыши и клавиатуре.")
    ]),
    "start": ("first_steps", "minecraft:book", "Начало TechQuest", [
        ("С чего начать", "TechQuest — единая техническая и приключенческая сборка. Начните с дерева, камня и железа. Откройте JEI в инвентаре для поиска рецептов. Выберите одно направление техники; не пытайтесь сразу строить все заводы."),
        ("Порядок развития", "$(li)Железо и первые инструменты.$(br)$(li)Create или BuildCraft для первых механизмов.$(br)$(li)IC2 и Mekanism для энергетики.$(br)$(li)AE2 для больших складов.$(br)$(li)Исследование мира, снаряжение, боссы.")
    ]),
    "safety": ("first_steps", "minecraft:shield", "Мир и сохранения", [
        ("Новый мир", "Проверяйте моды в новом мире. Перед обновлениями делайте полную резервную копию папки saves или серверного мира. Переход между несовместимыми версиями модов может повредить чанки и механизмы."),
        ("Для друзей", "На сервере всем нужна одна версия игрового набора TechQuest и NeoForge. Миникарта и индикатор HP устанавливаются только на клиент, они не обязательны серверу.")
    ]),
    "buildcraft": ("industry", "minecraft:piston", "BuildCraft", [
        ("Автоматизация", "BuildCraft добавляет трубы, механизмы и карьер. Начните с транспорта предметов и простых двигателей. В JEI найдите доступные рецепты и изучите их зависимости."),
        ("Первые задачи", "$(li)Сделайте источник энергии для механизма.$(br)$(li)Соедините источник с потребителем.$(br)$(li)Добавьте трубы для предметов.$(br)$(li)Испытайте систему на небольшом объёме, прежде чем строить карьер.")
    ]),
    "ic2": ("industry", "minecraft:furnace", "IndustrialCraft 2", [
        ("Энергия EU", "IC2: Nostalgia использует свою энергосистему EU. Осваивайте генератор, кабели, аккумуляторы и мацератор. Следите за напряжением и характеристиками оборудования."),
        ("Важно", "Не считайте, что кабели IC2 автоматически совместимы с любой сетью FE, RF или Create. Используйте только подтверждённые в игре преобразователи и читайте подсказки JEI.")
    ]),
    "create": ("industry", "minecraft:lever", "Create", [
        ("Вращение", "Create использует механическое вращение, скорость и нагрузку. Начните с водяного колеса, валов и шестерён. Для изучения механизмов наведите курсор на предмет Create в JEI и воспользуйтесь функцией Ponder, если она доступна."),
        ("Лаги заводов", "Очень большие кинетические сети и множество постоянно движущихся механизмов могут снижать FPS и TPS. Проверяйте производительность частями, вместо одновременного запуска всей фабрики.")
    ]),
    "mekanism": ("power", "minecraft:redstone", "Mekanism", [
        ("Энергетика", "В Mekanism изучите генераторы, кабели FE и машины обработки руды. Продвинутые цепочки расширяйте постепенно; особенно следите за количеством одновременно работающих машин."),
        ("Проверка рецептов", "Рецепты зависят от версии Mekanism и дополнительных модов. Нажмите R в JEI для просмотра изготовления и U для применения предмета, если назначения клавиш не изменены.")
    ]),
    "modern_industrialization": ("power", "minecraft:iron_block", "Modern Industrialization", [
        ("Промышленные цепочки", "Modern Industrialization ориентирован на многоступенчатое производство и автоматизацию. Сначала изучите базовые машины и материалы через JEI; затем постепенно подключайте обработку и транспорт ресурсов.")
    ]),
    "ae2": ("power", "minecraft:chest", "Applied Energistics 2", [
        ("Цифровой склад", "AE2 позволяет создавать сетевое хранение и автокрафт. Начните с накопителей, контроллера, терминала и источника питания. Затем изучите каналы и автоматический заказ предметов."),
        ("Встроенное руководство", "У AE2 есть собственная система GuideME. Откройте встроенное руководство мода, если оно доступно в установленной версии, а для точных рецептов используйте JEI.")
    ]),
    "superb": ("adventure", "minecraft:crossbow", "Superb Warfare", [
        ("Военная техника", "Superb Warfare содержит вооружение и боевые машины. Изучайте доступные рецепты через JEI. Проверяйте настройку управления транспортом в меню клавиш, прежде чем взлетать или стрелять."),
        ("Разрушение мира", "Тяжёлые взрывы, огонь и множество снарядов могут резко нагружать сервер. Не испытывайте массовые взрывы рядом с основной базой. Администратору стоит ограничить разрушения мира и сделать бэкап.")
    ]),
    "incoming": ("adventure", "minecraft:fire_charge", "Incoming: авиаудары и ядерное оружие", [
        ("Камера снаряда", "По умолчанию N включает камеру твоего снаряда в полёте; повторное N выбирает следующий, Shift выходит, F5 меняет вид. При переназначении ищи «Камера снаряда» в управлении Incoming. Без снарядов в полёте камера не включится. ЛКМ в камере может задавать новую цель, а не просто менять вид."),
        ("Авиаудары", "Incoming добавляет дроны, крылатые ракеты, Б-2, РСЗО и межконтинентальные ракеты. Наводите цели специальным пультом Strike Designator; у базы можно построить ПВО и сирены."),
        ("SAM: почему не стреляет", "ЗРК стреляет автоматически только по ЧУЖИМ шахедам, Ланцетам, крылатым ракетам и B-2; ракеты владельца и его команды игнорирует. Над ЗРК должно быть открыто небо, чанк должен быть загружен. Положите зенитные ракеты ПКМ или воронкой: каждая переходит из запаса в направляющую за 8 секунд. ПКМ пустой рукой покажет готовые ракеты и запас. Радар до 3000 блоков, пуск до 1500, нужна прямая видимость. МБР и Град не сбивает."),
        ("Для сервера", "Требуются одинаковая версия Incoming 3.10.4 у всех игроков и на сервере, Minecraft 1.21.1 / NeoForge 21.1.264 или новее. Мод нужен и на клиенте, и на сервере."),
        ("Лаги и безопасность мира", "Большие залпы и особенно ядерные удары способны сильно снижать FPS/TPS и разрушать чанки. Сначала испытывайте на отдельном мире. Администратор может ограничить доступ к запуску, отключить разрушение блоков и пожары через настройки мода; перед испытаниями обязательно сохраняйте мир.")
    ]),
    "rpg": ("adventure", "minecraft:enchanted_book", "Магия и боссы", [
        ("Исследование", "Iron's Spells 'n Spellbooks, Apotheosis и моды на боссов усиливают приключения. Сначала соберите броню и лечение. Сложные структуры и боссы лучше проходить группой."),
        ("Подсказки", "Проверяйте способности и ингредиенты через JEI и собственные руководства модов. При сильных просадках FPS уменьшите дистанцию прорисовки и дальность сущностей.")
    ]),
    "bomd": ("adventure", "minecraft:nether_star", "Bosses of Mass Destruction", [
        ("Четыре босса", "Мод Bosses of Mass Destruction (NeoForge 1.21.1) добавляет Night Lich, Obsidilith, Nether Gauntlet и Void Blossom. Боссы встречаются в редких структурах обычного мира, Незера и Энда."),
        ("Подготовка", "Перед битвой приготовьте броню, лечение и точку возврата. Боссы и структуры могут отсутствовать в уже исследованных чанках, поэтому тестируйте их в новом обычном мире."),
        ("С друзьями", "Всем игрокам и выделенному серверу нужен одинаковый мод и обязательные библиотеки. Сначала проверьте битву вдали от заводов, затем следите за TPS и FPS.")
    ]),
    "dragon_expedition": ("exploration", "minecraft:dragon_head", "Wyrmroost: новые драконы", [
        ("Драконы в мире", "Wyrmroost 1.4.1 добавляет новые виды драконов, которые встречаются в обычном мире. Изучайте их поведение и способы приручения. Это не Ice and Fire."),
        ("Полёт и приручение", "Разные виды драконов требуют своего подхода. Подготовьте запас еды и используйте JEI для подсказок. Для игры по Tailscale нужен Wyrmroost у каждого игрока и на сервере."),
        ("FPS и TPS", "Перед исследованием делайте резервную копию мира, особенно при генерации новых чанков. Массовые бои с драконами проводите далеко от заводов.")
    ]),
    "colossal_enemies": ("exploration", "minecraft:nether_star", "Крупные монстры", [
        ("Legendary Monsters", "Сильные боссы, включая Skeletosaurus, Lava Eater и Cloud Golem. Некоторые появляются в особых биомах и требуют серьёзной подготовки."),
        ("Twisted Mobs", "Опасные существа в разных измерениях: зомби Giant/Titan, пауки Goliath и другие мобы."),
        ("Сервер", "Замеряйте TPS через Spark при 1, 3 и 5 крупных мобах и отдельно проверяйте разрушения от Incoming и Superb Warfare.")
    ]),
    "expedition_route": ("exploration", "minecraft:compass", "Маршрут приключения", [
        ("С чего начать", "Откройте карту Xaero, создайте Explorer's Compass и исследуйте структуры в обычном мире. В крупных подземельях When Dungeons Arise можно найти опасных врагов и ценные предметы. Отмечайте место базы, чтобы вернуться."),
        ("Награда за исследование", "Artifacts добавляет уникальные находки в структурах. Обычные сундуки остаются общими для игроков: договаривайтесь о разделении добычи перед экспедицией. Проверяйте, что участники сервера используют одинаковый набор модов."),
        ("Безопасность мира", "Новые структуры генерируются в новых чанках. До обновления сохраните мир; для испытаний используйте свежий обычный мир, а не старый Superflat.")
    ]),
    "aether_expedition": ("exploration", "minecraft:feather", "The Aether: небесный мир", [
        ("Измерение", "The Aether добавляет небесные острова, новых существ, подземелья и боссов. Подготовьте походное снаряжение, еду и точку возвращения; не исследуйте новое измерение без резервной копии мира."),
        ("Производительность", "Большие острова и новые чанки нагружают генерацию. На сервере контролируйте TPS и используйте Spark при задержках.")
    ]),
    "deeper_expedition": ("exploration", "minecraft:sculk_sensor", "Deeper and Darker", [
        ("Тёмные тайны", "Deeper and Darker расширяет Deep Dark и добавляет собственный опасный мир. Исследуйте его по мере развития персонажа, после создания устойчивого снаряжения и запасов лечения."),
        ("Игровая проверка", "Проверьте появление структур и мобов, сохранение мира, переходы между измерениями и повторный вход нескольких игроков.")
    ]),
    "fortress_expedition": ("exploration", "minecraft:ender_eye", "Крепости и подземелья", [
        ("Исследование мира", "When Dungeons Arise добавляет крупные враждебные структуры. YUNG's Better Strongholds обновляет крепости Края, а YUNG's Better Nether Fortresses — крепости Незера."),
        ("Боевое прохождение", "Сначала исследуйте небольшие структуры и собирайте артефакты, потом проходите крепости группой. Используйте Explorer's Compass для поиска зарегистрированных структур."),
        ("Слабые ПК", "Большая генерация мира, особенно с Terralith и другими модами структур, может снижать TPS сервера. Тестируйте отдельно от заводов и массовых взрывов.")
    ]),
    "schematics": ("navigation", "minecraft:paper", "Forgematica: схемы", [
        ("Как Litematica", "Клиентский мод Forgematica позволяет строить по голограмме, проверять блоки и считать материалы. Поддерживает формат .litematic. Нужна библиотека MaFgLib."),
        ("Только клиент", "Forgematica и MaFgLib устанавливаются только игрокам. На выделенный сервер класть эти моды не нужно."),
        ("Производительность", "Отключайте отображение больших голограмм во время боёв и проверяйте конфликты горячих клавиш с Xaero.")
    ]),
    "map": ("navigation", "minecraft:map", "Карта и маршруты", [
        ("Миникарта Xaero", "Xaero's Minimap показывает окружение и точки маршрута. Xaero's World Map открывает полноэкранную карту. Обычно карта открывается клавишей M, но назначение можно изменить: Настройки → Управление."),
        ("Метки", "Сохраняйте метки важных мест: база, карьеры, портал, деревни. Для слабого ПК отключите лишние значки сущностей, тяжёлые эффекты карты и динамическую подгрузку дальних областей.")
    ]),
    "health": ("navigation", "minecraft:iron_sword", "Здоровье мобов", [
        ("Индикация HP", "Health Indicator TXF показывает текущее и максимальное HP числом и полоской сверху по центру, ниже обычной полосы босса. Миникарта остаётся слева. В Jade отключено повторное HP и броня существ, но сохранены подсказки. Старые пользовательские настройки автоматически не меняются."),
        ("Если тормозит", "Частое отображение меток на десятках существ нагружает интерфейс. При плохом FPS снизьте число видимых элементов Health Indicator TXF и отключите неиспользуемые индикаторы.")
    ]),
    "jei": ("navigation", "minecraft:crafting_table", "Рецепты и документация", [
        ("JEI", "JEI — основной справочник рецептов. Откройте инвентарь, найдите нужный предмет, наведите на него курсор и используйте R (рецепт) или U (применение). Назначения клавиш могут отличаться."),
        ("Другие руководства", "Для механизмов Create доступен Ponder, а у AE2 — GuideME. Этот путеводитель TechQuest объясняет общий порядок развития, но точные схемы сборки и рецепты берите из самих модов.")
    ]),
    "fps": ("performance", "minecraft:clock", "Низкий FPS", [
        ("Быстрые настройки", "$(li)Графика Fast.$(br)$(li)Прорисовка 4–6 чанков.$(br)$(li)Частицы Minimal.$(br)$(li)Отключите шейдеры.$(br)$(li)Снизьте дальность сущностей.$(br)$(li)Проверьте, что используется дискретная видеокарта."),
        ("Что уже включено", "Sodium, ImmediatelyFast, More Culling, Entity Culling, BadOptimizations и ModernFix помогают отрисовке. Dynamic FPS уменьшает нагрузку в фоне; не ожидайте от него прироста FPS в активном окне.")
    ]),
    "tps": ("performance", "minecraft:repeater", "Лаги сервера и заводов", [
        ("TPS и FPS", "FPS — скорость кадров на вашем ПК. TPS — скорость обработки мира сервером. Если мобы, машины и блоки обновляются рывками, даже при высоком FPS проблема может быть на стороне TPS."),
        ("Диагностика Spark", "В сборке установлен Spark для профилирования. Администратор может запустить профилирование по официальной документации Spark и проверить, какие моды или механизмы создают нагрузку. Отключайте подозреваемые функции только после сохранения мира.")
    ]),
}

def _json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

def guide_overrides():
    """Return safe relative game-directory paths and bytes for .mrpack overrides."""
    root = "patchouli_books/" + BOOK + "/"
    files = {
        root + "book.json": _json({
            "name": "Путеводитель TechQuest",
            "landing_text": "Добро пожаловать в TechQuest! Здесь описаны первые шаги, техника, карта, HP и оптимизация.$(br2)Подробные рецепты всегда смотрите через JEI.",
            "subtitle": "Industrial Frontier · 0.3.2",
            "version": 0, "show_progress": False,
            "creative_tab": "minecraft:tools_and_utilities",
            "book_texture": "patchouli:textures/gui/book_green.png",
            "model": "patchouli:book_green",
            "use_resource_pack": False,
        })
    }
    for num, (cid, (name, desc, icon)) in enumerate(CATEGORIES.items()):
        files[root + "en_us/categories/" + cid + ".json"] = _json(
            {"name": name, "description": desc, "icon": icon, "sortnum": num * 10})
    for num, (eid, (cid, icon, title, pages)) in enumerate(ENTRIES.items()):
        files[root + "en_us/entries/" + eid + ".json"] = _json({
            "name": title, "category": "patchouli:" + cid, "icon": icon,
            "sortnum": num * 10, "pages": [
                {"type": "patchouli:text", "title": page_title, "text": text}
                for page_title, text in pages]
        })
    files["TECHQUEST_INGAME_GUIDE.txt"] = (
        "TechQuest 0.3.2: Open Creative > Tools and Utilities and find Путеводитель TechQuest.\n"
        "In survival, Open Loader datapack attempts to give the book on first join.\n"
        "Map and waypoints: Xaero's Minimap/World Map (check controls, M often opens map).\n"
        "Health Indicator TXF and Jade show mob health, JEI recipes via R/U, Create Ponder.\n"
        "If the book is missing, verify Patchouli and openloader in the log.\n"
        "The guide is pack-authored and untested in a running Minecraft client.\n"
    ).encode("utf-8")
    files["config/openloader/packs/techquest_starter_guide.zip"] = starter_datapack()
    # A separate named pack is additive, so upgrades preserve an existing
    # original starter_guide.zip and user-created world/config files.
    files["config/openloader/packs/techquest_micropatch_033.zip"] = micro_patch_datapack()
    return files

def starter_datapack():
    """Vanilla 1.21.1 datapack: once-per-player guide and replacement recipe."""
    pack = {
        "pack": {"pack_format": 48, "description": "TechQuest: first-join Patchouli guide"}
    }
    advancement = {
        "criteria": {"first_join": {"trigger": "minecraft:tick"}},
        "rewards": {"loot": ["techquest:starter_guide"]}
    }
    loot = {
        "type": "minecraft:advancement_reward",
        "pools": [{
            "rolls": 1,
            "entries": [{
                "type": "minecraft:item",
                "name": "patchouli:guide_book",
                "functions": [{
                    "function": "minecraft:set_components",
                    "components": {"patchouli:book": BOOK_ID}
                }]
            }]
        }]
    }
    # Patchouli provides this recipe serializer for its book items.
    recipe = {
        "type": "patchouli:shapeless_book_recipe",
        "ingredients": [
            {"item": "minecraft:book"},
            {"item": "minecraft:compass"}
        ],
        "book": BOOK_ID,
    }
    data = {
        "pack.mcmeta": _json(pack),
        "data/techquest/advancement/first_guide.json": _json(advancement),
        "data/techquest/loot_table/starter_guide.json": _json(loot),
        "data/techquest/recipe/guide_book.json": _json(recipe),
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for path, content in data.items():
            z.writestr(path, content)
    return output.getvalue()

def micro_patch_datapack():
    """Additive Open Loader datapack: disable PMMO Vein Mining and sync Apotheosis tiers.
    Separate from the starter guide so upgrading older TechQuest installs does
    not require overwriting any existing starter guide or player config.
    """
    data = {"pack.mcmeta": _json({
        "pack": {"pack_format": 48, "description": "TechQuest micro1: server PMMO + Apotheosis tiers"}
    })}
    # Server-side Project MMO config: preserve skills, disable duplicate vein miner.
    # This is a complete CODEC config because its fields are required.
    data['data/pmmo/config/server.json'] = _json(json.loads("{\"general\":{\"creative_reach\":50,\"salvage_block\":\"minecraft:smithing_table\",\"treasure_enabled\":true,\"brewing_tracked\":true},\"levels\":{\"max_level\":1523,\"static_levels\":[-1],\"loss_on_death\":0.05,\"lose_only_excess\":true,\"global_modifier\":1,\"skill_modifiers\":{\"example_skill\":1},\"xp_min\":200,\"xp_base\":1.025,\"xp_per_level\":1.1},\"requirements\":{\"requirement_enabled\":{}},\"xp_gains\":{\"reuse_penalty\":0,\"perks_plus_config\":false,\"player_actions\":{\"JUMP\":{\"agility\":2.5},\"SPRINT_JUMP\":{\"agility\":2.5},\"CROUCH_JUMP\":{\"agility\":2.5},\"BREATH_CHANGE\":{\"endurance\":1},\"HEALTH_INCREASE\":{\"endurance\":1},\"HEALTH_DECREASE\":{\"endurance\":1},\"SPRINTING\":{\"agility\":2},\"SUBMERGED\":{\"swimming\":1},\"SWIMMING\":{\"swimming\":1},\"DIVING\":{\"swimming\":1},\"SURFACING\":{\"swimming\":1},\"SWIM_SPRINTING\":{\"swimming\":1}},\"damage\":{\"DEAL_DAMAGE\":{\"minecraft:generic_kill\":{\"combat\":1},\"minecraft:player_attack\":{\"combat\":1},\"#minecraft:is_projectile\":{\"archery\":1},\"#pmmo:magic\":{\"magic\":15},\"#pmmo:gun\":{\"gunslinging\":1}},\"RECEIVE_DAMAGE\":{\"minecraft:generic_kill\":{\"endurance\":1},\"#pmmo:environment\":{\"endurance\":10},\"#pmmo:impact\":{\"endurance\":15},\"#pmmo:magic\":{\"magic\":15},\"#minecraft:is_projectile\":{\"endurance\":15}},\"MITIGATE_DAMAGE\":{\"minecraft:generic_kill\":{\"endurance\":10},\"#pmmo:environment\":{\"endurance\":100},\"#pmmo:impact\":{\"endurance\":150},\"#pmmo:magic\":{\"magic\":150},\"#minecraft:is_projectile\":{\"endurance\":150}}}},\"party\":{\"party_range\":50,\"party_bonus\":{\"combat\":1.05,\"endurance\":1.1}},\"mob_scaling\":{\"mob_scale_enabled\":false,\"scaling_aoe\":150,\"mob_scale_base_level\":0,\"boss_scaling\":1.1,\"use_exponential_formula\":true,\"mob_scale_per_level\":1,\"mob_scale_power_base\":1.104088404342588,\"ratios\":{}},\"vein_miner\":{\"vein_enabled\":false,\"require_settings\":false,\"default_consume\":1,\"charge_modifier\":1,\"blacklist\":[\"silentgear:saw\"]}}"))
    # Server-global World Tier: scoreboard persists across world restarts.
    data['data/minecraft/tags/function/load.json'] = _json({'values': ['techquest:worldtier/load']})
    data['data/minecraft/tags/function/tick.json'] = _json({'values': ['techquest:worldtier/tick']})
    data['data/techquest/function/worldtier/load.mcfunction'] = (
        'scoreboard objectives add tq_worldtier dummy\n'
        'execute unless score #global tq_worldtier matches 0.. run scoreboard players set #global tq_worldtier 0\n'
        'scoreboard players set #clock tq_worldtier 0\n'
    ).encode('utf-8')
    data['data/techquest/function/worldtier/tick.mcfunction'] = (
        'scoreboard players add #clock tq_worldtier 1\n'
        'execute if score #clock tq_worldtier matches 20.. run function techquest:worldtier/sync\n'
    ).encode('utf-8')
    tiers = ('frontier', 'ascent', 'summit', 'pinnacle')
    cmds = ['scoreboard players set #clock tq_worldtier 0']
    for i, tier in enumerate(tiers, 1):
        nbt = json.dumps({'neoforge:attachments': {'apotheosis:world_tier': tier}}, separators=(',', ':'))
        data['data/techquest/predicate/worldtier/' + tier + '.json'] = _json({
            'condition': 'minecraft:entity_properties', 'entity': 'this',
            'predicate': {'nbt': nbt}})
        cmds.append('execute as @a if predicate techquest:worldtier/' + tier +
                    ' if score #global tq_worldtier matches ..' + str(i - 1) +
                    ' run scoreboard players set #global tq_worldtier ' + str(i))
    for i, tier in enumerate(tiers, 1):
        cmds.append('execute as @a if score #global tq_worldtier matches ' + str(i) +
                    ' unless predicate techquest:worldtier/' + tier +
                    ' run apoth set_world_tier @s ' + tier)
    data['data/techquest/function/worldtier/sync.mcfunction'] = ('\n'.join(cmds) + '\n').encode('utf-8')
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for path, content in data.items():
            z.writestr(path, content)
    return output.getvalue()

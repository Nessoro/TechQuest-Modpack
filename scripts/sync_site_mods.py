#!/usr/bin/env python3
"""Regenerate the inline catalog in docs/index.html using modlist.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
NAMES = {
    "aquamirae": "Aquamirae",
    "fragmentum": "Fragmentum",
    "better-zoom": "Better Zoom",
    "controlling": "Controlling",
    "searchables": "Searchables",
    "physicsmod": "Physics Mod Lite",
    "buildcraft-community-edition": "BuildCraft Community Edition",
    "ae2": "Applied Energistics 2",
    "irons-spells-n-spellbooks": "Iron's Spells 'n Spellbooks",
    "l_enders-cataclysm": "L_Ender's Cataclysm",
    "bosses-of-mass-destruction-forge": "Bosses of Mass Destruction (NeoForge)",
    "yungs-better-dungeons": "YUNG's Better Dungeons",
    "yungs-better-mineshafts": "YUNG's Better Mineshafts",
    "jei": "Just Enough Items (JEI)",
    "appleskin": "AppleSkin",
    "ferrite-core": "FerriteCore",
    "modernfix": "ModernFix",
    "entityculling": "Entity Culling",
    "sophisticated-backpacks": "Sophisticated Backpacks",
    "modern-industrialization": "Modern Industrialization",
    "mekanism-generators": "Mekanism Generators",
    "iron-chests": "Iron Chests",
    "storagedrawers": "Storage Drawers",
    "mowzies-mobs": "Mowzie's Mobs",
    "farmers-delight": "Farmer's Delight",
    "iris": "Iris Shaders",
    "sodium": "Sodium",
    "immediatelyfast": "ImmediatelyFast",
    "moreculling": "More Culling",
    "badoptimizations": "BadOptimizations",
    "dynamic-fps": "Dynamic FPS",
    "spark": "spark",
    "superb-warfare": "Superb Warfare",
    "burnt": "Burnt + Additions",
    "explosion-overhaul-a-new-level-of-destruction": "Explosion Overhaul",
    "lithostitched": "Lithostitched",
    "irons-lib": "Iron's Lib",
    "xaeros-minimap": "Xaero's Minimap",
    "xaeros-world-map": "Xaero's World Map",
    "health-indicator-txf": "Health Indicator TXF (HP цифрами)",
    "patchouli": "Patchouli — путеводитель TechQuest",
    "open-loader": "Open Loader",
    "aether": "The Aether",
    "deeperdarker": "Deeper and Darker",
    "artifacts": "Artifacts",
    "when-dungeons-arise": "When Dungeons Arise",
    "yungs-better-strongholds": "YUNG's Better Strongholds",
    "yungs-better-nether-fortresses": "YUNG's Better Nether Fortresses",
    "wyrmroost": "Wyrmroost",
    "legendary-monsters": "Legendary Monsters",
    "twisted-mobs": "Twisted Mobs",
    "mafglib": "MaFgLib",
    "forgematica": "Forgematica",
    "explorers-compass": "Explorer's Compass",
    "sophisticated-storage": "Sophisticated Storage",
    "architectury-api": "Architectury API",
    "lithium": "Lithium",
    "trash-cans": "Trash Cans",
    "pretty-pipes": "Pretty Pipes",
}
DESCRIPTIONS = {
    "trash-cans": "Мусорки для предметов, жидкостей и энергии с фильтрами; удаляют содержимое, подключаются к трубам.",
    "pretty-pipes": "Транспортировка предметов и блоков как вещей по трубам без двигателей, маршрутизация и фильтры.",
    "aquamirae": "Океанские структуры, существа и босс в общей тестовой 0.3.3; игровые механики ещё требуют проверки.",
    "fragmentum": "Обязательная библиотека Aquamirae, версия 5.4.0.",
    "better-zoom": "Клиентский зум Z + колесо с плавным возвратом FOV.",
    "controlling": "Поиск назначений, конфликтов и свободных клавиш.",
    "searchables": "Клиентская библиотека поиска для Controlling.",
    "physicsmod": "Ограниченная клиентская физика обломков; игровой тест ещё требуется.",
    "buildcraft-community-edition": "Классическая автоматизация, карьеры, трубы и двигатели.",
    "create": "Шестерни, вращение и автоматизированные производства.",
    "mekanism": "Техническая энергетика и многоуровневая переработка руд.",
    "modern-industrialization": "Промышленные цепочки и заводы.",
    "ae2": "Цифровые склады и промышленная логистика.",
    "l_enders-cataclysm": "Боссы, структуры и сложные сражения.",
    "bosses-of-mass-destruction-forge": "Четыре босса в редких структурах мира, Незера и Энда; новые сражения.",
    "terralith": "Новые биомы и ландшафты.",
    "immediatelyfast": "Более быстрая отрисовка частиц, интерфейса и сущностей.",
    "moreculling": "Убирает лишнюю отрисовку невидимых поверхностей.",
    "badoptimizations": "Оптимизация различных клиентских процессов.",
    "dynamic-fps": "Снижает нагрузку, когда игра в фоне.",

    "yungs-better-dungeons": "Новые вариации подземелий.",
    "superb-warfare": "Огнестрельное оружие, артиллерия, самолёты и бронетехника.",
    "burnt": "Реалистичные пожары, обугленные блоки и распространение огня.",
    "explosion-overhaul-a-new-level-of-destruction": "Мощные взрывы, звуковые эффекты и ударные волны. NeoForge alpha.",
    "lithostitched": "Библиотека генерации мира, необходимая Terralith.",
    "irons-lib": "Библиотека, необходимая Iron's Spells 'n Spellbooks.",
    "xaeros-minimap": "Лёгкая миникарта, точки маршрутов, настройка радаров.",
    "xaeros-world-map": "Полноэкранная карта исследованного мира; обычно открывается M.",
    "health-indicator-txf": "Числовое HP и полоска здоровья мобов при наведении прицела.",
    "patchouli": "Русское внутриигровое руководство по модам TechQuest.",
    "open-loader": "Автоматически подключает datapack выдачи книги в мире.",
    "aether": "Новое небесное измерение, подземелья, исследование островов и боссы.",
    "deeperdarker": "Тайны Deep Dark, новые биомы, измерение Otherside и противники.",
    "artifacts": "Редкие сокровища, уникальные предметы и мимики в структурах.",
    "when-dungeons-arise": "Крупные враждебные подземелья, крепости, корабли и добыча.",
    "yungs-better-strongholds": "Новые сложные крепости с секретами и ловушками.",
    "yungs-better-nether-fortresses": "Переработанные крепости Незера с зонами для исследования.",
    "wyrmroost": "Разнообразные драконы, приручение и полёты.",
    "legendary-monsters": "Крупные боссы: Skeletosaurus, Lava Eater, Cloud Golem.",
    "twisted-mobs": "Зомби Giant/Titan, пауки Goliath и другие опасные существа.",
    "mafglib": "Клиентская библиотека Forgematica.",
    "forgematica": "Голограммы чертежей, .litematic и списки материалов; только клиент.",
    "explorers-compass": "Поиск обычных и модовых структур через удобный компас.",
    "sophisticated-storage": "Улучшаемые сундуки и фильтры; Iron Chests сохранён.",
    "architectury-api": "Библиотека NeoForge для FTB Library и Ultimine.",
    "lithium": "Оптимизация логики и тиков Minecraft; требуется проверка совместимости.",
}
mods = []
for row in cfg["mods"]:
    slug = row["project"]
    mods.append({
        "name": NAMES.get(slug, slug.replace("-", " ").title()),
        "group": row["group"],
        "required": row.get("required", False),
        "description": DESCRIPTIONS.get(slug, "Кандидат; совместимость требует отдельной проверки."),
        "url": "https://modrinth.com/mod/" + slug,
    })
for row in reversed(cfg.get("manual_mods", [])):
    ready = bool(row.get("download_url"))
    mods.insert(1, {
        "name": row["name"],
        "group": row.get("group", "Технологии"),
        "required": row.get("required", False),
        "description": ("IndustrialCraft 2: EU, генераторы и промышленные машины."
                        if ready else
                        "Ожидает файла от владельца проекта. Пока не включён в скачиваемый модпак."),
        "url": row["source"],
    })
for row in reversed(cfg.get("external_mods", [])):
    mods.insert(1, {
        "name": row["name"], "group": row.get("group", "Военная техника"),
        "required": row.get("required", False),
        "description": ("Авиаудары, ПВО, ракеты и ядерные взрывы. Может сильно нагружать сервер."
                        if row["name"].startswith("Incoming") else
                        "Библиотека или инструмент FTB Ultimine для NeoForge 1.21.1."),
        "url": row["source"],
    })
index = ROOT / "docs" / "index.html"
source = index.read_text(encoding="utf-8")
marker = "window.TQ_MODS = "
start = source.find(marker)
if start < 0:
    raise SystemExit("inline mod data marker is missing")
end = source.find(";\n", start)
if end < 0:
    raise SystemExit("inline mod data terminator is missing")
payload = json.dumps(mods, ensure_ascii=False, indent=2).replace("</", "<\\/")
source = source[:start] + marker + payload + source[end:]
index.write_text(source, encoding="utf-8")
print("Updated inline catalog:", len(mods), "mods")

#!/usr/bin/env python3
"""Regenerate the inline catalog in docs/index.html using modlist.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
NAMES = {
    "buildcraft-community-edition": "BuildCraft Community Edition",
    "ae2": "Applied Energistics 2",
    "irons-spells-n-spellbooks": "Iron's Spells 'n Spellbooks",
    "l_enders-cataclysm": "L_Ender's Cataclysm",
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
    "spark": "spark",
}
DESCRIPTIONS = {
    "buildcraft-community-edition": "Классическая автоматизация, карьеры, трубы и двигатели.",
    "create": "Шестерни, вращение и автоматизированные производства.",
    "mekanism": "Техническая энергетика и многоуровневая переработка руд.",
    "modern-industrialization": "Промышленные цепочки и заводы.",
    "ae2": "Цифровые склады и промышленная логистика.",
    "l_enders-cataclysm": "Боссы, структуры и сложные сражения.",
    "terralith": "Новые биомы и ландшафты.",
    "yungs-better-dungeons": "Новые вариации подземелий.",
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
for row in cfg.get("manual_mods", []):
    mods.insert(1, {
        "name": row["name"], "group": "Технологии",
        "required": row["required"],
        "description": "Экспериментальный порт IndustrialCraft 2 — машины, EU и энергетика.",
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

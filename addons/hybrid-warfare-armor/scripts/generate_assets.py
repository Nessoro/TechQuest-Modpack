"""Generate recipes and tags ONLY. No PNG, model, icon or skin-pack assets.

The result of each smithing recipe is the ORIGINAL Superb Warfare item with
a single custom component. Minecraft 1.21.1 SmithingTransformRecipe copies all
base components and patches this component: base durability, enchants, ArmorPlate
custom data and any pre-existing trim stay intact.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "src/main/resources"
RECIPES = RES / "data/techquest_hybrid/recipe"
TRIMMABLE = RES / "data/minecraft/tags/item/trimmable_armor.json"

TECH = {
    "ic2": ("ic2:quantum_helmet", "ic2:quantum_chestplate"),
    "mi": ("modern_industrialization:quantum_helmet", "modern_industrialization:quantum_chestplate"),
    "mek": ("mekanism:mekasuit_helmet", "mekanism:mekasuit_bodyarmor"),
    "oritech": ("oritech:exo_helmet", "oritech:exo_chestplate"),
}
BASES = {
    "ru_helmet_6b47": "helmet",
    "ru_chest_6b43": "chest",
    "us_helmet_pasgt": "helmet",
    "us_chest_iotv": "chest",
    "ge_helmet_m_35": "helmet",
}

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def generate():
    # Remove obsolete recipes from the previous experimental generator.
    RECIPES.mkdir(parents=True, exist_ok=True)
    for file in RECIPES.glob("*.json"):
        file.unlink()

    count = 0
    for tech, (helmet_donor, chest_donor) in TECH.items():
        for name, slot in BASES.items():
            original = "superbwarfare:" + name
            donor = helmet_donor if slot == "helmet" else chest_donor
            write_json(RECIPES / (tech + "_" + name + ".json"), {
                "type": "minecraft:smithing_transform",
                "template": {"item": "minecraft:netherite_upgrade_smithing_template"},
                "base": {"item": original},
                "addition": {"item": donor},
                "result": {
                    "id": original,
                    "components": {"techquest_hybrid:technology": tech},
                },
            })
            count += 1

    # Vanilla smithing templates + pigments can be applied on ORIGINAL SBW items.
    write_json(TRIMMABLE, {
        "replace": False,
        "values": ["superbwarfare:" + name for name in BASES],
    })

    # Explicitly no original assets or new texture files are shipped.
    print(f"Generated {count} fusion recipes for 5 original Superb Warfare items; no textures")

if __name__ == "__main__":
    generate()

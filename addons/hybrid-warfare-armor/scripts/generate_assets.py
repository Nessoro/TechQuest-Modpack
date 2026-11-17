"""Deterministically generate 20 hybrid items, smithing recipes and four skin palettes.
Uses only Python standard library; developer/CI build step, never needed by players.
"""
from pathlib import Path
import json
import random
import struct
import zlib
import zipfile
from pilot_texture import texture as mek_ru_pilot_texture

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "src/main/resources"
TECH = {
    "ic2": ("IC2: Nostalgia", "ic2:quantum_helmet", "ic2:quantum_chestplate", (245, 144, 40)),
    "mi": ("Modern Industrialization", "modern_industrialization:quantum_helmet",
           "modern_industrialization:quantum_chestplate", (153, 100, 245)),
    "mek": ("Mekanism", "mekanism:mekasuit_helmet", "mekanism:mekasuit_bodyarmor", (58, 184, 238)),
    "oritech": ("Oritech", "oritech:exo_helmet", "oritech:exo_chestplate", (76, 215, 168)),
}
BASE = {
    "ru_helmet_6b47": ("superbwarfare:ru_helmet_6b47", "helmet", "6B47"),
    "ru_chest_6b43": ("superbwarfare:ru_chest_6b43", "chest", "6B43"),
    "us_helmet_pasgt": ("superbwarfare:us_helmet_pasgt", "helmet", "PASGT"),
    "us_chest_iotv": ("superbwarfare:us_chest_iotv", "chest", "IOTV"),
    "ge_helmet_m_35": ("superbwarfare:ge_helmet_m_35", "helmet", "M35"),
}
PALETTES = {
    "factory": ((66, 74, 64), (112, 115, 92), (29, 36, 34)),
    "urban": ((65, 78, 92), (106, 119, 130), (26, 34, 49)),
    "arctic": ((173, 185, 179), (220, 227, 213), (77, 94, 105)),
    "nightops": ((37, 41, 50), (71, 74, 87), (16, 20, 29)),
}

def output(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def png(path, width, height, pixels):
    raw = b"".join(b"\x00" + b"".join(bytes(pixels[y * width + x]) for x in range(width))
                   for y in range(height))
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def armor_pixels(key, base_id, palette, accent):
    width, height = 64, 32
    pixels = [(0, 0, 0, 0)] * (width * height)
    rng = random.Random(key + base_id + palette)
    main, light, shadow = PALETTES[palette]
    areas = [(0, 0, 31, 15)] if "helmet" in base_id else [(0, 16, 15, 31), (16, 16, 55, 31)]
    def fill(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            pixels[y * width + x] = color + (255,)
    for left, top, right, bottom in areas:
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                fill(x, y, main if rng.random() > .27 else rng.choice([light, shadow]))
        for x in range(left, right + 1):
            fill(x, top, shadow); fill(x, bottom, shadow)
        for y in range(top, bottom + 1):
            fill(left, y, shadow); fill(right, y, shadow)
        for x in range(left + 3, min(right, left + 18), 4):
            fill(x, top + 4, accent)
    return pixels

def icon_pixels(base_id, palette, accent):
    p = [(0, 0, 0, 0)] * 256
    main, light, shadow = PALETTES[palette]
    helmet = "helmet" in base_id
    for y in range(2, 13):
        for x in range(2, 14):
            inside = ((4 <= x <= 11 and 3 <= y <= 11) if helmet else
                      ((4 <= x <= 11 and 3 <= y <= 14) or (2 <= x <= 13 and 5 <= y <= 8)))
            if inside:
                c = shadow if x in (2, 13) or y in (2, 12) else main
                if y in (6, 7) and 5 <= x <= 10: c = light
                if 7 <= x <= 9 and y == 5: c = accent
                p[y * 16 + x] = c + (255,)
    return p

def main():
    names_ru, names_en, ids = {}, {}, []
    for tech, (title, donor_helmet, donor_chest, accent) in TECH.items():
        for base_id, (original, slot, label) in BASE.items():
            item = tech + "_" + base_id
            ids.append("techquest_hybrid:" + item)
            donor = donor_helmet if slot == "helmet" else donor_chest
            output(RES / "data/techquest_hybrid/recipe" / (item + ".json"), {
                "type": "minecraft:smithing_transform",
                "template": {"item": "minecraft:netherite_upgrade_smithing_template"},
                "base": {"item": original},
                "addition": {"item": donor},
                "result": {"id": "techquest_hybrid:" + item},
            })
            output(RES / "assets/techquest_hybrid/models/item" / (item + ".json"), {
                "parent": "minecraft:item/generated",
                "textures": {"layer0": "techquest_hybrid:item/" + item},
            })
            names_ru["item.techquest_hybrid." + item] = "Гибридная броня " + title + " — " + label
            names_en["item.techquest_hybrid." + item] = title + " Hybrid Armor — " + label
            for palette in PALETTES:
                if palette == "factory":
                    textures = RES / "assets/techquest_hybrid/textures"
                else:
                    textures = ROOT / "skin-packs" / ("TechQuest_Hybrid_" + palette) / "assets/techquest_hybrid/textures"
                # Pilot 6B47/6B43 hybrid uses hand-authored vanilla UV artwork.
                # Other items retain the procedural prototype textures for now.
                armor_map = (mek_ru_pilot_texture("helmet" if slot == "helmet" else "vest")
                             if tech == "mek" and palette == "factory"
                             and base_id in ("ru_helmet_6b47", "ru_chest_6b43")
                             else armor_pixels(tech, base_id, palette, accent))
                png(textures / "models/armor" / (item + "_layer_1.png"), 64, 32,
                    armor_map)
                png(textures / "item" / (item + ".png"), 16, 16,
                    icon_pixels(base_id, palette, accent))
    # Complete the visual set with two new Mekanism-powered pieces.
    # Superb Warfare itself supplies only the 6B47 helmet and 6B43 vest.
    for part, donor in (("leggings", "mekanism:mekasuit_pants"),
                        ("boots", "mekanism:mekasuit_boots")):
        item = "mek_ru_" + part
        ids.append("techquest_hybrid:" + item)
        output(RES / "data/techquest_hybrid/recipe" / (item + ".json"), {
            "type": "minecraft:smithing_transform",
            "template": {"item": "minecraft:netherite_upgrade_smithing_template"},
            "base": {"item": "minecraft:netherite_" + part},
            "addition": {"item": donor},
            "result": {"id": "techquest_hybrid:" + item},
        })
        output(RES / "assets/techquest_hybrid/models/item" / (item + ".json"), {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": "techquest_hybrid:item/" + item},
        })
        names_ru["item.techquest_hybrid." + item] = (
            "Гибридная броня Mekanism — " + ("поножи" if part == "leggings" else "ботинки"))
        names_en["item.techquest_hybrid." + item] = "Mekanism Hybrid " + part.title()
        img = [(0, 0, 0, 0)] * 256
        for y in range(3, 14):
            for x in range(2, 14):
                leg = (part == "leggings" and
                       ((4 <= x <= 11 and y <= 6) or
                        (4 <= x <= 6 and y >= 7) or
                        (9 <= x <= 11 and y >= 7)))
                boot = (part == "boots" and
                        (((3 <= x <= 6) or (9 <= x <= 12)) and y >= 6 and
                         (y < 11 or x in (3,4,5,9,10,11,12))))
                if leg or boot:
                    base = (46, 59, 81) if (x+y) % 5 else (73, 86, 108)
                    img[y*16+x] = (*base, 255)
        for x in (5,10):
            img[10*16+x] = (15, 117, 246, 255)
        png(RES / "assets/techquest_hybrid/textures/item" / (item + ".png"),
            16, 16, img)
    output(RES / "assets/techquest_hybrid/lang/ru_ru.json", names_ru)
    output(RES / "assets/techquest_hybrid/lang/en_us.json", names_en)
    output(RES / "data/minecraft/tags/item/trimmable_armor.json", {"replace": False, "values": ids})
    output(RES / "data/c/tags/item/armors.json", {"replace": False, "values": ids})
    # Superb Warfare checks this tag for the higher 30-point armor-plate capacity.
    output(RES / "data/superbwarfare/tags/item/military_armor.json",
           {"replace": False, "values": [x for x in ids if "_chest_" in x]})
    output(RES / "data/minecraft/tags/item/head_armor.json",
           {"replace": False, "values": [x for x in ids if "helmet" in x]})
    output(RES / "data/minecraft/tags/item/chest_armor.json",
           {"replace": False, "values": [x for x in ids if "chest" in x]})
    for palette in PALETTES:
        if palette == "factory":
            continue
        folder = ROOT / "skin-packs" / ("TechQuest_Hybrid_" + palette)
        output(folder / "pack.mcmeta", {"pack": {"pack_format": 34,
               "description": "TechQuest Hybrid Warfare Armor: " + palette}})
        with zipfile.ZipFile(ROOT / "skin-packs" / ("TechQuest_Hybrid_" + palette + ".zip"),
                             "w", zipfile.ZIP_DEFLATED) as archive:
            for path in folder.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(folder))
    from generate_3d_textures import generate as generate_pilot_3d
    generate_pilot_3d()
    from tactical_v2 import generate as tactical_blue_v2
    upgraded = tactical_blue_v2()
    print("Generated", len(ids), "hybrid items with", len(upgraded),
          "new Tactical Blue V2 wearable 3D atlases")

if __name__ == "__main__":
    main()

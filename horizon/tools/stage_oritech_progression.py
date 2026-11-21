"""Pinned public-data subset for the first Oritech crafting route.

Uses Horizon's own pinned Rust recipe/loot and worldgen upgraders. Never reads
Java dependencies or packages their code. Generated assets stay in private stage.
"""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from stage_pretty_pipes import NEOFORGE_SHA256
from stage_terralith_content import read_checked

MATERIALS = ("raw_nickel", "raw_platinum", "nickel_ingot", "platinum_ingot",
             "steel_ingot", "electrum_ingot", "magnetic_coil", "biosteel_ingot")
ORES = {"nickel_ore": "iron_ore", "deepslate_nickel_ore": "deepslate_iron_ore",
        "deepslate_platinum_ore": "deepslate_diamond_ore", "endstone_platinum_ore": "diamond_ore"}
RECIPES = ("crafting/core1", "crafting/basicgen", "crafting/electricfurnacealt",
           "crafting/magnet", "crafting/alloy/steel", "crafting/alloy/electrum",
           "nickel_ingot_from_smelting_raw_nickel", "nickel_ingot_from_blasting_raw_nickel",
           "platinum_ingot_from_smelting_raw_platinum", "platinum_ingot_from_blasting_raw_platinum")
PROCESSING_MATERIALS = ("motor", "quartz_dust", "raw_silicon", "silicon")
PROCESSING_RECIPES = ("motor/motorcraft", "crafting/pulverizer", "crafting/electricfurnace",
                      "crafting/alloy/rawsilicon", "silicon_from_smelting_raw_silicon")


def add_progression(payloads, raw, neoforge_jar, content_tool, port_pack, parent, pulverizer=False):
    materials = (*MATERIALS, *PROCESSING_MATERIALS) if pulverizer else MATERIALS
    recipe_names = (*RECIPES, *PROCESSING_RECIPES) if pulverizer else RECIPES
    neo = read_checked(neoforge_jar)
    if hashlib.sha256(neo).hexdigest() != NEOFORGE_SHA256:
        raise ValueError("expected pinned NeoForge 21.1.264 universal JAR")
    for tool in (content_tool, port_pack):
        if tool is None or not tool.is_file():
            raise ValueError("progression needs the pinned content helper and datapack upgrader")
    source_data, source_assets, tags, missing = [], [], {}, set()

    def data(name, value): payloads[name] = (json.dumps(value, indent=2) + "\n").encode()
    with zipfile.ZipFile(io.BytesIO(raw)) as original, zipfile.ZipFile(io.BytesIO(neo)) as neoforge:
        def take(name, asset=False):
            value = original.read(name)
            (source_assets if asset else source_data).append({"path": name, "sha256": hashlib.sha256(value).hexdigest()})
            return value

        def resolve(tag, active=()):
            if tag in tags: return tags[tag]
            if tag in active: raise ValueError("cyclic source tag")
            ns, path = tag.split(":", 1); name = f"data/{ns}/tags/item/{path}.json"
            found = False; values = set()
            for archive in (neoforge, original):
                if name not in archive.namelist(): continue
                found = True; value = json.loads(archive.read(name))
                if value.get("replace"): values.clear()
                for entry in value["values"]:
                    ident = entry if isinstance(entry, str) else entry["id"]
                    if ident.startswith("#"):
                        child = ident[1:]; child_ns, child_path = child.split(":", 1)
                        child_name = f"data/{child_ns}/tags/item/{child_path}.json"
                        if not any(child_name in z.namelist() for z in (neoforge, original)) and isinstance(entry, dict) and entry.get("required") is False:
                            missing.add(child); continue
                        values.update(resolve(child, (*active, tag)))
                    else:
                        if not ident.startswith("minecraft:") and ident not in {"oritech:"+m for m in materials}:
                            raise ValueError("source tag needs an unported material: " + ident)
                        values.add(ident)
            if not found: raise ValueError("unresolved required source tag: " + tag)
            tags[tag] = sorted(values); return tags[tag]

        recipes = {f"data/oritech/recipe/{r}.json": json.loads(take(f"data/oritech/recipe/{r}.json")) for r in recipe_names}
        for recipe in recipes.values():
            ingredients = list(recipe.get("key", {}).values()) + ([recipe["ingredient"]] if "ingredient" in recipe else [])
            for ingredient in ingredients:
                if "tag" in ingredient and ingredient["tag"].startswith("c:"): resolve(ingredient["tag"])
        if pulverizer:
            resolve("c:gems/quartz")
        for tag, values in tags.items():
            ns, path = tag.split(":", 1); data(f"data/{ns}/tags/item/{path}.json", {"values": values})
        loot = {f"data/oritech/loot_table/blocks/{o}.json": json.loads(take(f"data/oritech/loot_table/blocks/{o}.json")) for o in ORES}
        loot.update({name: json.loads(value) for name, value in payloads.items() if name.startswith("data/oritech/loot_table/")})
        upgraded = subprocess.run([str(content_tool.resolve()), "upgrade"], input=json.dumps({"recipes": recipes, "loot": loot}), capture_output=True, text=True, check=True)
        normalized = json.loads(upgraded.stdout)
        for section in ("recipes", "loot"):
            for name, value in normalized[section].items(): data(name, value)

        if pulverizer:
            name = "data/oritech/recipe/pulverizer/quartz.json"
            recipe = json.loads(take(name))
            if recipe.get("type") != "oritech:pulverizer" or len(recipe.get("ingredients", [])) != 1 or len(recipe.get("results", [])) != 1:
                raise ValueError("expected the selected original quartz pulverizer recipe")
            converted = []
            for ingredient in recipe["ingredients"]:
                if set(ingredient) == {"tag"}:
                    converted.append("#" + ingredient["tag"])
                elif set(ingredient) == {"item"}:
                    converted.append(ingredient["item"])
                else:
                    raise ValueError("unsupported original processing ingredient")
            recipe["ingredients"] = converted
            data(name, recipe)

        for material in materials:
            data(f"data/oritech/horizon/item/{material}.json", {"template": "minecraft:iron_ingot", "max_stack_size": 64})
            model = f"assets/oritech/models/item/{material}.json"; payloads[model] = take(model, True)
            texture = json.loads(payloads[model])["textures"]["layer0"].split(":", 1)[1]
            name = f"assets/oritech/textures/{texture}.png"; payloads[name] = take(name, True)
            data(f"assets/oritech/items/{material}.json", {"model": {"type": "minecraft:model", "model": f"oritech:item/{material}"}})
        for ore, template in ORES.items():
            data(f"data/oritech/horizon/block/{ore}.json", {"template": "minecraft:" + template})
            for name in (f"assets/oritech/blockstates/{ore}.json", f"assets/oritech/models/block/{ore}.json", f"assets/oritech/models/item/{ore}.json", f"assets/oritech/textures/block/{ore}.png"):
                payloads[name] = take(name, True)
            data(f"assets/oritech/items/{ore}.json", {"model": {"type": "minecraft:model", "model": f"oritech:item/{ore}"}})
        for language in ("en_us", "ru_ru"):
            name = f"assets/oritech/lang/{language}.json"; labels = json.loads(payloads[name]); source = json.loads(original.read(name))
            for key in [*("item.oritech."+m for m in materials), *("block.oritech."+o for o in ORES)]: labels[key] = source[key]
            data(name, labels)
        name = "data/minecraft/tags/block/mineable/pickaxe.json"
        data(name, {"values": json.loads(payloads[name])["values"] + ["oritech:"+o for o in ORES]})
        for kind in ("needs_iron_tool", "needs_stone_tool"):
            name = f"data/minecraft/tags/block/{kind}.json"; source = json.loads(take(name))
            data(name, {"values": [v for v in source["values"] if v in {"oritech:"+o for o in ORES}]})
        with tempfile.TemporaryDirectory(prefix="oritech-worldgen-", dir=parent) as tmp:
            root = Path(tmp); raw_pack = root / "raw"; raw_pack.mkdir()
            (raw_pack / "pack.mcmeta").write_text(json.dumps({"pack": {"pack_format": 48, "description": "Pinned Oritech ore subset"}}))
            for feature in ("ore_nickel", "ore_platinum", "ore_platinum_end"):
                names = [f"data/oritech/worldgen/placed_feature/{feature}.json", f"data/oritech/neoforge/biome_modifier/{feature}.json"]
                if feature != "ore_platinum_end": names.append(f"data/oritech/worldgen/configured_feature/{feature}.json")
                for name in names:
                    f = raw_pack / name; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(take(name))
            subprocess.run([str(port_pack.resolve()), "upgrade-datapack", str(raw_pack), str(root / "out")], check=True, capture_output=True, text=True)
            for f in (root / "out/data").rglob("*"):
                if f.is_file(): payloads[str(f.relative_to(root / "out"))] = f.read_bytes()
    return {"recipes": list(recipe_names), "materials": list(materials), "ores": list(ORES),
            "source_data": source_data, "source_assets": source_assets, "resolved_common_tags": tags,
            "missing_optional_legacy_tags": sorted(missing), "worldgen_features": ["ore_nickel", "ore_platinum", "ore_platinum_end"],
            "content_tool_sha256": hashlib.sha256(read_checked(content_tool)).hexdigest(),
            "port_pack_sha256": hashlib.sha256(read_checked(port_pack)).hexdigest(), "native_version_required": "0.2.0" if pulverizer else "0.1.0",
            "processing_recipes": ["pulverizer/quartz"] if pulverizer else [],
            "required_core_patch": "techquest_biome_modifiers:0.1.0"}

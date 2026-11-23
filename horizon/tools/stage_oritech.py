#!/usr/bin/env python3
"""Stage the isolated Oritech energy prototype and optional starter content.

The default 0.1 subset uses the pinned CC0 core texture and translated names.
The generator/furnace use simple cube models and vanilla textures. No Java,
GeckoLib animations are not packaged. --progression adds ten source recipes,
ore generation/loot and the first route's materials; it is not a full mod port.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from stage_terralith_content import read_checked

ROOT = Path(__file__).resolve().parents[1]
BLOCKS = ("basic_generator_block", "powered_furnace_block", "machine_core_1")


def stage(jar, sdk, output, progression=False, neoforge_jar=None, content_tool=None, port_pack=None, pulverizer=False, foundry=False, assembler=False, energy_pipes=False, wrench=False, waterlogging=False, machine_use=False, stack_limits=False):
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.absolute().parents):
        raise ValueError("output must be a new directory without symlinks")
    for parent in output.absolute().parents:
        if (parent / "level.dat").exists() or (parent / "horizon-resources.json").exists():
            raise ValueError("stage outside worlds and resources")
    pin = json.loads(read_checked(ROOT / "source/techquest-post-pr48-candidate.json"))["modrinth_lock"]["4sYI62kA"]
    raw = read_checked(jar)
    if pin["version"] != "1.2.13" or hashlib.sha512(raw).hexdigest() != pin["sha512"]:
        raise ValueError("expected pinned Oritech 1.2.13")
    machine_use = machine_use or stack_limits
    waterlogging = waterlogging or machine_use
    wrench = wrench or waterlogging
    energy_pipes = energy_pipes or wrench
    assembler = assembler or energy_pipes
    foundry = foundry or assembler
    pulverizer = pulverizer or foundry
    progression = progression or pulverizer
    version = "0.10.0" if stack_limits else "0.9.0" if machine_use else "0.8.0" if waterlogging else "0.7.0" if wrench else "0.6.0" if energy_pipes else "0.5.0" if assembler else "0.4.0" if foundry else "0.3.0" if pulverizer else "0.2.0" if progression else "0.1.0"
    blocks = (*BLOCKS, "pulverizer_block") if pulverizer else BLOCKS
    if foundry: blocks = (*blocks, "foundry_block")
    if assembler: blocks = (*blocks, "assembler_block")
    payloads = {"horizon-mod.toml": ('id = "oritech"\nname = "TechQuest Oritech energy prototype"\nversion = "' + version + '"\napi = "0.2"\nside = "both"\ncapabilities = ["registries"]\n').encode()}
    license_text = read_checked(ROOT / "first_party/oritech/LICENSE-ORITECH").decode()
    # SDK content packages keep assets/data/manifest; retain the dedication in
    # manifest comments, as for the existing Pretty Pipes notice.
    payloads["horizon-mod.toml"] = ("\n".join("# " + line for line in license_text.splitlines()) + "\n").encode() + payloads["horizon-mod.toml"]

    def data(name, value):
        payloads[name] = (json.dumps(value, indent=2) + "\n").encode()

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for language in ("en_us", "ru_ru"):
            name = f"assets/oritech/lang/{language}.json"
            original = json.loads(archive.read(name))
            data(name, {key: original[key] for key in ("block.oritech." + b for b in blocks)})
        name = "assets/oritech/textures/block/machine_core_1.png"
        payloads[name] = archive.read(name)
    for block in blocks:
        definition = {"template": "minecraft:iron_block", "properties": {"hardness": 5.0, "occludes": False}}
        variants = {"": {"model": f"oritech:block/{block}"}}
        if block in ("foundry_block", "assembler_block"):
            definition["state_properties"] = {"facing": {"type": "enum", "values": ["north", "east", "south", "west"]}}
            definition["default_state"] = {"facing": "north"}
            variants = {"facing="+face: {"model": f"oritech:block/{block}", "y": y} for face,y in (("north",0),("east",90),("south",180),("west",270))}
        data(f"data/oritech/horizon/block/{block}.json", definition)
        data(f"assets/oritech/blockstates/{block}.json", {"variants": variants})
        data(f"assets/oritech/models/item/{block}.json", {"parent": f"oritech:block/{block}"})
        data(f"assets/oritech/items/{block}.json", {"model": {"type": "minecraft:model", "model": f"oritech:item/{block}"}})
        textures = {"all": "oritech:block/machine_core_1"} if block == "machine_core_1" else {
            "top": "minecraft:block/iron_block", "side": "minecraft:block/iron_block",
            "front": "minecraft:block/" + ("blast_furnace_front" if block == "basic_generator_block" else "furnace_front")}
        data(f"assets/oritech/models/block/{block}.json", {"parent": "minecraft:block/cube_all" if block == "machine_core_1" else "minecraft:block/orientable", "textures": textures})
        data(f"data/oritech/loot_table/blocks/{block}.json", {"type": "minecraft:block", "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "oritech:" + block}], "conditions": [{"type": "minecraft:survives_explosion"}]}]})
        if block != "machine_core_1":
            slots = {"basic_generator_block": 1, "powered_furnace_block": 2, "pulverizer_block": 3, "foundry_block": 3, "assembler_block": 5}[block]
            menu = {"slots": slots, "data_slots": 5}
            if slots > 1:
                menu["results"] = [4] if block == "assembler_block" else [2] if block == "foundry_block" else list(range(1, slots))
            data(f"data/oritech/horizon/menu/{block}.json", menu)
    data("data/minecraft/tags/block/mineable/pickaxe.json", {"values": ["oritech:" + b for b in blocks]})
    if energy_pipes:
        add_energy_pipes(payloads, raw, data, tight_selection=wrench, waterlogging=waterlogging)
    progression_report = None
    if progression:
        if any(p is None for p in (neoforge_jar, content_tool, port_pack)):
            raise ValueError("--progression requires --neoforge-jar, --content-tool and --port-pack")
        from stage_oritech_progression import add_progression
        progression_report = add_progression(payloads, raw, neoforge_jar, content_tool, port_pack, output.absolute().parent, pulverizer=pulverizer, foundry=foundry, assembler=assembler, energy_pipes=energy_pipes, wrench=wrench, machine_use=machine_use, stack_limits=stack_limits)
    with tempfile.TemporaryDirectory(prefix="oritech-stage-", dir=output.absolute().parent) as tmp:
        root = Path(tmp) / "module"
        for name, content in payloads.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        subprocess.run([str(sdk.resolve()), "build"], cwd=root, check=True, capture_output=True, text=True)
        package = root / "target/horizon-mod/oritech.hmod"
        verdict = json.loads(subprocess.run([str(sdk.resolve()), "check", str(package), "--json"], cwd=root, check=True, capture_output=True, text=True).stdout)
        if not verdict.get("ok"):
            raise ValueError("SDK rejected energy prototype")
        report = {"schema": 1, "prototype_version": version, "source_version": "1.2.13", "source_jar_sha512": pin["sha512"],
                  "sha256": hashlib.sha256(package.read_bytes()).hexdigest(), "sdk_validated": True,
                  "requires_native_module": "techquest_oritech", "blocks": list(blocks),
                  "energy_pipe_blocks": ["energy_pipe", "energy_pipe_connection"] if energy_pipes else [],
                  "wrench_and_default_tight_cable_selection": wrench,
                  "basic_cable_waterlogging": waterlogging,
                  "machine_menu_and_wrench_neighbor_dispatch": machine_use,
                  "inventory_component_stack_limits": stack_limits,
                  "java_code_included": False, "original_recipes_ported": bool(progression), "all_original_recipes_ported": False,
                  "progression_subset": progression_report, "full_mod_ported": False, "gameplay_tested": False}
        (root / "techquest-oritech-trial.json").write_text(json.dumps(report, indent=2) + "\n")
        root.rename(output)
    return report


def add_energy_pipes(payloads, raw, data, tight_selection=False, waterlogging=False):
    """Basic CC0 geometry with a normal wire and a separate item-less endpoint."""
    directions = ("down", "up", "north", "south", "west", "east")
    boxes = {"core": [6, 6, 6, 10, 10, 10], "down": [6, 0, 6, 10, 6, 10],
             "up": [6, 10, 6, 10, 16, 10], "north": [6, 6, 0, 10, 10, 6],
             "south": [6, 6, 10, 10, 10, 16], "west": [0, 6, 6, 6, 10, 10],
             "east": [10, 6, 6, 16, 10, 10]}
    # Historical 0.6 keeps cube selection. Wrench 0.7 uses the original
    # default tight selection, with the same thin geometry as collision.
    properties = {d: {"type": "enum", "values": ["0", "1"]} for d in directions}
    properties.update({k: {"type": "boolean"} for k in ("straight", "waterlogged")})
    if waterlogging:
        # HeavyCore's only inherited state is waterlogged. Its pinned MIT
        # binding supplies SimpleWaterloggedBlock, placement and neighbor-fluid
        # ticks, without adding axis/facing states or replacing cable geometry.
        del properties["waterlogged"]
    shapes = {",".join(str((mask >> i) & 1) for i in range(6)):
              [boxes["core"], *(boxes[d] for i, d in enumerate(directions) if mask & (1 << i))]
              for mask in range(64)}
    if tight_selection:
        # Model elements use pixels; Horizon's BlockShapes uses block units.
        # Preserve historical 0.6 bytes, correcting both outlines and collision
        # for the new wrench profile.
        shapes = {key: [[v / 16 for v in box] for box in value]
                  for key, value in shapes.items()}
    for block in ("energy_pipe", "energy_pipe_connection"):
        definition = {
            "template": "minecraft:heavy_core" if waterlogging else "minecraft:iron_block", "item": block == "energy_pipe",
            "properties": {"hardness": 1.0, "explosion_resistance": 2.0, "occludes": False},
            "state_properties": properties, "collision_shapes": {"properties": list(directions), "values": shapes}}
        if tight_selection: definition["shapes"] = definition["collision_shapes"]
        if waterlogging:
            definition["properties"]["sounds"] = "minecraft:iron_block"
            if block == "energy_pipe":
                definition["components"] = {"minecraft:rarity": "common"}
        data(f"data/oritech/horizon/block/{block}.json", definition)
        data(f"assets/oritech/blockstates/{block}.json", {"multipart": [
            {"apply": {"model": "oritech:block/techquest_energy_core"}}] + [
            {"when": {d: "1"}, "apply": {"model": f"oritech:block/techquest_energy_{d}"}} for d in directions]})
    faces = {face: {"texture": "#cable"} for face in directions}
    for name, bounds in boxes.items():
        data(f"assets/oritech/models/block/techquest_energy_{name}.json", {
            "parent": "minecraft:block/block", "textures": {"cable": "minecraft:block/copper_block", "particle": "minecraft:block/copper_block"},
            "elements": [{"from": bounds[:3], "to": bounds[3:], "faces": faces}]})
    data("assets/oritech/models/item/energy_pipe.json", {"parent": "oritech:block/techquest_energy_core"})
    data("assets/oritech/items/energy_pipe.json", {"model": {"type": "minecraft:model", "model": "oritech:item/energy_pipe"}})
    with zipfile.ZipFile(io.BytesIO(raw)) as original:
        for language in ("en_us", "ru_ru"):
            name = f"assets/oritech/lang/{language}.json"
            labels = json.loads(payloads[name]); source = json.loads(original.read(name))
            labels["block.oritech.energy_pipe"] = source["block.oritech.energy_pipe"]
            labels["block.oritech.energy_pipe_connection"] = source["block.oritech.energy_pipe"]
            data(name, labels)
        for block in ("energy_pipe", "energy_pipe_connection"):
            name = f"data/oritech/loot_table/blocks/{block}.json"
            data(name, json.loads(original.read(name)))
    name = "data/minecraft/tags/block/mineable/pickaxe.json"
    data(name, {"values": json.loads(payloads[name])["values"] + ["oritech:energy_pipe", "oritech:energy_pipe_connection"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("jar", "sdk", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--progression", action="store_true")
    parser.add_argument("--stack-limits", action="store_true", help="component stack limits for portable-container preparation; implies --machine-use")
    parser.add_argument("--machine-use", action="store_true", help="held-item machine menus and original neighboring-cable wrench dispatch; implies --waterlogging")
    parser.add_argument("--waterlogging", action="store_true", help="basic cable SimpleWaterlogged behavior; implies --wrench")
    parser.add_argument("--wrench", action="store_true", help="craftable basic cable wrench and default tight selection; implies --energy-pipes")
    parser.add_argument("--energy-pipes", action="store_true", help="basic energy cables; implies --assembler")
    parser.add_argument("--assembler", action="store_true", help="four-input coils/motors; implies --foundry")
    parser.add_argument("--foundry", action="store_true", help="selected three-core foundry/alloy route; implies --pulverizer")
    parser.add_argument("--pulverizer", action="store_true", help="add the selected quartz/silicon processing route (implies --progression)")
    for name in ("neoforge-jar", "content-tool", "port-pack"):
        parser.add_argument("--" + name, type=Path)
    print(json.dumps(stage(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()

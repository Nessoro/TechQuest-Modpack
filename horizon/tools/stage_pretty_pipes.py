#!/usr/bin/env python3
"""Build private content for the native Pretty Pipes transport prototype.

Registers a pipe, four module/material items and their five source recipes.
No Java code is copied. Stage/SDK checks alone do not test gameplay.
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

SOURCE = Path(__file__).resolve().parents[1] / "source/techquest-post-pr48-candidate.json"
NEOFORGE_SHA256 = "dd8680641ad05f3d796a77829c682ee999e3907e3dae77074c39ee804dc33411"
RECIPE_NAMES = ("pipe", "blank_module", "low_extraction_module",
                "medium_extraction_module", "high_extraction_module")


def glass_members(raw):
    """Resolve public c:glass_blocks JSON from the pinned minimal reference.

    Missing optional legacy Forge tags are recorded; other mod contributions
    are outside this isolated reference's tested membership.
    """
    if hashlib.sha256(raw).hexdigest() != NEOFORGE_SHA256:
        raise ValueError("expected the pinned NeoForge 21.1.264 universal JAR")
    missing, seen, members = set(), set(), set()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        def visit(tag):
            if tag in seen:
                return
            seen.add(tag)
            ns, path = tag.split(":", 1)
            name = f"data/{ns}/tags/item/{path}.json"
            for entry in json.loads(archive.read(name))["values"]:
                value = entry if isinstance(entry, str) else entry["id"]
                if value.startswith("#"):
                    child = value[1:]
                    child_ns, child_path = child.split(":", 1)
                    child_name = f"data/{child_ns}/tags/item/{child_path}.json"
                    if child_name not in archive.namelist() and isinstance(entry, dict) and entry.get("required") is False:
                        missing.add(child)
                    else:
                        visit(child)
                else:
                    if not value.startswith("minecraft:"):
                        raise ValueError("unexpected non-vanilla glass in reference")
                    members.add(value)
        visit("c:glass_blocks")
    if len(members) != 18:
        raise ValueError("unexpected glass membership in pinned reference")
    return sorted(members), sorted(missing)


def stage(jar, sdk, output, neoforge_jar):
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError("output must be new, without symlink parents")
    for p in output.absolute().parents:
        if (p / "level.dat").exists() or (p / "horizon-resources.json").exists():
            raise ValueError("stage outside worlds and resources")
    pin = json.loads(read_checked(SOURCE))["modrinth_lock"]["XExdLWCQ"]
    raw = read_checked(jar)
    if pin["version"] != "1.22.0" or hashlib.sha512(raw).hexdigest() != pin["sha512"]:
        raise ValueError("expected the pinned original Pretty Pipes 1.22.0 JAR")
    glass, missing_tags = glass_members(read_checked(neoforge_jar))
    payloads = {"horizon-mod.toml": b'id = "prettypipes"\nname = "TechQuest Pretty Pipes transport prototype"\nversion = "0.6.0"\napi = "0.2"\nside = "both"\ncapabilities = ["registries"]\n'}
    license_text = read_checked(Path(__file__).resolve().parents[1] /
                                "first_party/pretty_pipes/LICENSE-PRETTY-PIPES").decode()
    payloads["horizon-mod.toml"] = ("\n".join("# " + line for line in license_text.splitlines()) + "\n").encode() + payloads["horizon-mod.toml"]

    def data(name, value):
        payloads[name] = (json.dumps(value, indent=2) + "\n").encode()

    # Three visible module slots and 64 slots hidden by native_screen on both
    # client and server. Hidden queue slots refuse all menu transfers.
    data("data/prettypipes/horizon/menu/pipe.json", {"slots": 67, "data_slots": 21})

    data("data/prettypipes/horizon/block/pipe.json", {
        "template": "minecraft:chorus_plant", "properties": {"hardness": 2.0, "occludes": False},
        "connects_to": "#prettypipes:connects", "thickness": 4.0})
    data("data/prettypipes/tags/block/connects.json", {"values": [
        "minecraft:chest", "minecraft:trapped_chest", "minecraft:barrel", "minecraft:hopper",
        "minecraft:furnace", "minecraft:blast_furnace", "minecraft:smoker",
        {"id": "oritech:basic_generator_block", "required": False},
        {"id": "oritech:powered_furnace_block", "required": False}]})
    faces = {face: {"texture": "#pipe"} for face in ("up", "down", "north", "south", "east", "west")}
    boxes = {"core": ([6, 6, 6], [10, 10, 10]), "down": ([6, 0, 6], [10, 6, 10]),
             "up": ([6, 10, 6], [10, 16, 10]), "north": ([6, 6, 0], [10, 10, 6]),
             "south": ([6, 6, 10], [10, 10, 16]), "west": ([0, 6, 6], [6, 10, 10]),
             "east": ([10, 6, 6], [16, 10, 10])}
    for name, (low, high) in boxes.items():
        data(f"assets/prettypipes/models/block/techquest_pipe_{name}.json", {
            "parent": "minecraft:block/block", "textures": {"pipe": "prettypipes:block/pipe", "particle": "prettypipes:block/pipe"},
            "elements": [{"from": low, "to": high, "faces": faces}]})
    data("assets/prettypipes/blockstates/pipe.json", {"multipart": [
        {"apply": {"model": "prettypipes:block/techquest_pipe_core"}}] + [
        {"when": {d: "true"}, "apply": {"model": f"prettypipes:block/techquest_pipe_{d}"}}
        for d in boxes if d != "core"]})
    data("assets/prettypipes/items/pipe.json", {"model": {"type": "minecraft:model", "model": "prettypipes:block/techquest_pipe_core"}})
    source_assets = []
    source_data = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        item_name_keys = {"block.prettypipes.pipe"} | {"item.prettypipes." + n for n in RECIPE_NAMES if n != "pipe"}
        language_keys = set(item_name_keys)
        language_keys |= {"info.prettypipes." + n for n in ("whitelist", "blacklist", "whitelist.description", "blacklist.description")}
        language_keys |= {"dir.prettypipes." + n for n in ("down", "up", "north", "south", "west", "east", "all")}
        for language in ("en_us", "ru_ru"):
            name = f"assets/prettypipes/lang/{language}.json"
            original_language = json.loads(archive.read(name))
            if (not item_name_keys <= original_language.keys()
                    or (language == "en_us" and not language_keys <= original_language.keys())):
                raise ValueError("missing source item names")
            data(name, {key: original_language[key] for key in sorted(language_keys) if key in original_language})
        for recipe in RECIPE_NAMES:
            name = f"data/prettypipes/recipe/{recipe}.json"
            original = archive.read(name)
            value = json.loads(original)
            if value.get("type") != "minecraft:crafting_shaped":
                raise ValueError("unexpected source recipe type")
            for symbol, ingredient in value["key"].items():
                if set(ingredient) == {"item"}:
                    value["key"][symbol] = ingredient["item"]
                elif ingredient == {"tag": "c:glass_blocks"}:
                    value["key"][symbol] = "#prettypipes:source/glass_blocks"
                else:
                    raise ValueError("unexpected source recipe ingredient")
            data(name, value)
            source_data.append({"path": name, "sha256": hashlib.sha256(original).hexdigest()})
        loot = "data/prettypipes/loot_table/blocks/pipe.json"
        original = archive.read(loot)
        value = json.loads(original)
        conditions = value["pools"][0]["conditions"]
        if conditions != [{"condition": "minecraft:survives_explosion"}]:
            raise ValueError("unexpected original pipe loot condition")
        # 26.3 dispatches loot conditions by `type`; keeping the 1.21.1
        # discriminator silently makes this condition fail in the engine.
        conditions[0] = {"type": "minecraft:survives_explosion"}
        data(loot, value)
        source_data.append({"path": loot, "sha256": hashlib.sha256(original).hexdigest()})
        data("data/prettypipes/tags/item/source/glass_blocks.json", {"values": glass})
        names = ["assets/prettypipes/textures/block/pipe.png"]
        for item in ("blank_module", "low_extraction_module", "medium_extraction_module", "high_extraction_module"):
            data(f"data/prettypipes/horizon/item/{item}.json", {
                "template": "minecraft:paper", "max_stack_size": 64 if item == "blank_module" else 16})
            data(f"assets/prettypipes/models/item/{item}.json", {
                "parent": "minecraft:item/generated", "textures": {"layer0": f"prettypipes:item/{item}"}})
            data(f"assets/prettypipes/items/{item}.json", {
                "model": {"type": "minecraft:model", "model": f"prettypipes:item/{item}"}})
            names.append(f"assets/prettypipes/textures/item/{item}.png")
        for name in names:
            payloads[name] = archive.read(name)
            source_assets.append({"path": name, "sha256": hashlib.sha256(payloads[name]).hexdigest()})
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pretty-pipes-", dir=output.parent) as temporary:
        root = Path(temporary) / "content"
        for name, content in payloads.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        built = subprocess.run([str(sdk.resolve()), "build"], cwd=root, capture_output=True, text=True)
        if built.returncode:
            raise ValueError("SDK build rejected prototype: " + (built.stderr or built.stdout)[:1000])
        package = root / "target/horizon-mod/prettypipes.hmod"
        verdict = json.loads(subprocess.run([str(sdk.resolve()), "check", str(package), "--json"],
                             cwd=root, check=True, capture_output=True, text=True).stdout)
        checksum = hashlib.sha256(package.read_bytes()).hexdigest()
        if not verdict.get("ok") or verdict["report"].get("sha256") != checksum:
            raise ValueError("SDK rejected the content prototype")
        report = {"schema": 1, "id": "prettypipes", "prototype_version": "0.6.0",
                  "source_version": "1.22.0", "source_jar_sha512": pin["sha512"],
                  "sha256": checksum, "sdk_validated": True, "source_assets": source_assets,
                  "requires_native_module": "techquest_pretty_pipes", "java_code_included": False,
                  "recipes_ported": True, "recipe_count": 5, "loot_table_count": 1,
                  "loot_condition_discriminators_normalized": 1,
                  "source_data": source_data, "glass_reference_neoforge": "21.1.264",
                  "glass_reference_sha256": NEOFORGE_SHA256,
                  "glass_members": glass, "missing_optional_legacy_tags": missing_tags,
                  "other_mod_glass_contributions_ported": False,
                  "module_menu_declared": True, "visible_module_slots": 3,
                  "hidden_transport_slots": 64, "gui_runtime_tested": False,
                  "gui_ported": False, "gameplay_tested": False,
                  "full_mod_ported": False}
        (root / "techquest-pretty-pipes-trial.json").write_text(json.dumps(report, indent=2) + "\n")
        root.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("jar", "sdk", "output", "neoforge-jar"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(stage(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()

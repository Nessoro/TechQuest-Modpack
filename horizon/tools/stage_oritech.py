#!/usr/bin/env python3
"""Stage three blocks for the isolated Oritech energy prototype, not a full port.

The original pinned CC0 JAR supplies only core texture and translated names.
The generator/furnace use simple cube models and vanilla textures. No Java,
GeckoLib animations, original recipes or unimplemented items are packaged.
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


def stage(jar, sdk, output):
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.absolute().parents):
        raise ValueError("output must be a new directory without symlinks")
    for parent in output.absolute().parents:
        if (parent / "level.dat").exists() or (parent / "horizon-resources.json").exists():
            raise ValueError("stage outside worlds and resources")
    pin = json.loads(read_checked(ROOT / "source/techquest-post-pr48-candidate.json"))["modrinth_lock"]["4sYI62kA"]
    raw = read_checked(jar)
    if pin["version"] != "1.2.13" or hashlib.sha512(raw).hexdigest() != pin["sha512"]:
        raise ValueError("expected pinned Oritech 1.2.13")
    payloads = {"horizon-mod.toml": b'id = "oritech"\nname = "TechQuest Oritech energy prototype"\nversion = "0.1.0"\napi = "0.2"\nside = "both"\ncapabilities = ["registries"]\n'}
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
            data(name, {key: original[key] for key in ("block.oritech." + b for b in BLOCKS)})
        name = "assets/oritech/textures/block/machine_core_1.png"
        payloads[name] = archive.read(name)
    for block in BLOCKS:
        data(f"data/oritech/horizon/block/{block}.json", {"template": "minecraft:iron_block", "properties": {"hardness": 5.0, "occludes": False}})
        data(f"assets/oritech/blockstates/{block}.json", {"variants": {"": {"model": f"oritech:block/{block}"}}})
        data(f"assets/oritech/models/item/{block}.json", {"parent": f"oritech:block/{block}"})
        data(f"assets/oritech/items/{block}.json", {"model": {"type": "minecraft:model", "model": f"oritech:item/{block}"}})
        textures = {"all": "oritech:block/machine_core_1"} if block == "machine_core_1" else {
            "top": "minecraft:block/iron_block", "side": "minecraft:block/iron_block",
            "front": "minecraft:block/" + ("blast_furnace_front" if block == "basic_generator_block" else "furnace_front")}
        data(f"assets/oritech/models/block/{block}.json", {"parent": "minecraft:block/cube_all" if block == "machine_core_1" else "minecraft:block/orientable", "textures": textures})
        data(f"data/oritech/loot_table/blocks/{block}.json", {"type": "minecraft:block", "pools": [{"rolls": 1, "entries": [{"type": "minecraft:item", "name": "oritech:" + block}], "conditions": [{"type": "minecraft:survives_explosion"}]}]})
        if block != "machine_core_1":
            menu = {"slots": 1 if block == "basic_generator_block" else 2, "data_slots": 5}
            if block == "powered_furnace_block":
                menu["results"] = [1]
            data(f"data/oritech/horizon/menu/{block}.json", menu)
    data("data/minecraft/tags/block/mineable/pickaxe.json", {"values": ["oritech:" + b for b in BLOCKS]})
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
        report = {"schema": 1, "prototype_version": "0.1.0", "source_version": "1.2.13", "source_jar_sha512": pin["sha512"],
                  "sha256": hashlib.sha256(package.read_bytes()).hexdigest(), "sdk_validated": True,
                  "requires_native_module": "techquest_oritech", "blocks": list(BLOCKS),
                  "java_code_included": False, "original_recipes_ported": False, "full_mod_ported": False, "gameplay_tested": False}
        (root / "techquest-oritech-trial.json").write_text(json.dumps(report, indent=2) + "\n")
        root.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("jar", "sdk", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(stage(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()

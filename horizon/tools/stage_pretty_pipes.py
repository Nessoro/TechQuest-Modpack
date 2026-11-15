#!/usr/bin/env python3
"""Build private content for the native Pretty Pipes transport prototype.

Only a pipe and four module/material items are registered. No Java code is
copied; recipes and player module interactions are not claimed by this stage.
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


def stage(jar, sdk, output):
    if output.exists() or output.is_symlink() or any(p.is_symlink() for p in output.parents):
        raise ValueError("output must be new, without symlink parents")
    for p in output.absolute().parents:
        if (p / "level.dat").exists() or (p / "horizon-resources.json").exists():
            raise ValueError("stage outside worlds and resources")
    pin = json.loads(read_checked(SOURCE))["modrinth_lock"]["XExdLWCQ"]
    raw = read_checked(jar)
    if pin["version"] != "1.22.0" or hashlib.sha512(raw).hexdigest() != pin["sha512"]:
        raise ValueError("expected the pinned original Pretty Pipes 1.22.0 JAR")
    payloads = {"horizon-mod.toml": b'id = "prettypipes"\nname = "TechQuest Pretty Pipes transport prototype"\nversion = "0.1.0"\napi = "0.2"\nside = "both"\ncapabilities = ["registries"]\n'}
    license_text = read_checked(Path(__file__).resolve().parents[1] /
                                "first_party/pretty_pipes/LICENSE-PRETTY-PIPES").decode()
    payloads["horizon-mod.toml"] = ("\n".join("# " + line for line in license_text.splitlines()) + "\n").encode() + payloads["horizon-mod.toml"]

    def data(name, value):
        payloads[name] = (json.dumps(value, indent=2) + "\n").encode()

    data("data/prettypipes/horizon/block/pipe.json", {
        "template": "minecraft:chorus_plant", "properties": {"hardness": 2.0, "occludes": False},
        "connects_to": "#prettypipes:connects", "thickness": 4.0})
    data("data/prettypipes/tags/block/connects.json", {"values": [
        "minecraft:chest", "minecraft:trapped_chest", "minecraft:barrel", "minecraft:hopper",
        "minecraft:furnace", "minecraft:blast_furnace", "minecraft:smoker"]})
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
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
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
        report = {"schema": 1, "id": "prettypipes", "prototype_version": "0.1.0",
                  "source_version": "1.22.0", "source_jar_sha512": pin["sha512"],
                  "sha256": checksum, "sdk_validated": True, "source_assets": source_assets,
                  "requires_native_module": "techquest_pretty_pipes", "java_code_included": False,
                  "recipes_ported": False, "gui_ported": False, "gameplay_tested": False,
                  "full_mod_ported": False}
        (root / "techquest-pretty-pipes-trial.json").write_text(json.dumps(report, indent=2) + "\n")
        root.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("jar", "sdk", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    print(json.dumps(stage(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Restore fixed-mob processors and default chest limits in Better Dungeons.

Reads public JSON data from the pinned original JAR, never Java code. This
partial adapter leaves all other dropped processors explicitly unresolved.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import tomllib
import zipfile

from stage_terralith_content import read_checked

SOURCE_SHA1 = "73a660c13063450e555e5e2c015ae24d606b32b4"
VERSION = "1.21.1-NeoForge-5.1.4"


def upgraded_states(value):
    if isinstance(value, list):
        return [upgraded_states(item) for item in value]
    if isinstance(value, dict):
        # The carried vanilla rule uses the 26.3 block-state spelling.
        return {({"Name": "id", "Properties": "properties"}.get(key, key)):
                upgraded_states(item) for key, item in value.items()}
    return value


def replacements(jar: Path, carry: Path):
    data = read_checked(jar)
    if hashlib.sha1(data).hexdigest() != SOURCE_SHA1:
        raise ValueError("expected the pinned Better Dungeons 5.1.4 JAR")
    payloads, unresolved, provenance = {}, [], {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("duplicate source archive entries")
        for mob in ("skeleton", "spider", "zombie"):
            name = f"data/betterdungeons/worldgen/processor_list/small_dungeon/small_dungeon_{mob}.json"
            raw = archive.read(name)
            original = json.loads(raw)
            expected = [upgraded_states(p) for p in original["processors"]
                        if p["processor_type"].startswith("minecraft:")]
            if json.loads(read_checked(carry / name)) != {"processors": expected}:
                raise ValueError("carried rules differ from reviewed source: " + name)
            converted, restored, chest_caps = [], 0, 0
            for processor in original["processors"]:
                kind = processor["processor_type"]
                if kind.startswith("minecraft:"):
                    converted.append(upgraded_states(processor))
                elif kind == "betterdungeons:mob_spawner_processor":
                    if processor != {"processor_type": kind, "spawner_mob": f"minecraft:{mob}"}:
                        raise ValueError("unreviewed fixed-mob processor fields")
                    converted.append({"processor_type": "horizon:spawner_mobs",
                                      "mobs": [{"entity": {"id": f"minecraft:{mob}"}, "weight": 1}],
                                      "delay": 20, "min_spawn_delay": 200, "max_spawn_delay": 800,
                                      "spawn_count": 4, "max_nearby_entities": 6,
                                      "required_player_range": 16, "spawn_range": 4})
                    # The pinned native processor constructs fresh NBT without
                    # its block-entity ID. Placement then leaves an inert block.
                    # A rule appends that ID while retaining the typed fields.
                    converted.append({"processor_type": "minecraft:rule", "rules": [{
                        "input_predicate": {"predicate_type": "minecraft:block_match",
                                            "block": "minecraft:spawner"},
                        "location_predicate": {"predicate_type": "minecraft:always_true"},
                        "output_state": {"id": "minecraft:spawner"},
                        "block_entity_modifier": {"type": "minecraft:append_static",
                                                  "data": {"id": "minecraft:mob_spawner"}}}]})
                    restored += 1
                elif kind == "betterdungeons:small_dungeon_chest_processor":
                    if processor != {"processor_type": kind}:
                        raise ValueError("unreviewed chest processor fields")
                    # Native CountCap is documented for this processor; use
                    # the original default configuration, not arbitrary limits.
                    converted.append({"processor_type": "horizon:count_cap",
                                      "blocks": ["minecraft:chest", "minecraft:trapped_chest"],
                                      "min": 1, "max": 2, "chance": 0.2,
                                      "replacement": {"id": "minecraft:cave_air"}})
                    chest_caps += 1
                else:
                    unresolved.append({"file": name, "processor_type": kind})
            if restored != 1:
                raise ValueError("expected exactly one fixed-mob processor per list")
            if chest_caps != 1:
                raise ValueError("expected exactly one chest processor per list")
            payloads[name] = (json.dumps({"processors": converted}, indent=2) + "\n").encode()
            provenance[name] = hashlib.sha256(raw).hexdigest()
    return payloads, unresolved, provenance


def stage(work: Path, jar: Path, sdk: Path, output: Path):
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("output must be new")
    if any(parent.is_symlink() for parent in output.parents):
        raise ValueError("symlink in output parents")
    carry = work.resolve() / "mods/betterdungeons/carry"
    for source in (work.resolve(), jar.resolve(), sdk.resolve()):
        if output == source or source in output.parents or output in source.parents:
            raise ValueError("stage separately from source inputs")
    for parent in output.parents:
        if (parent / "level.dat").exists() or (parent / "horizon-resources.json").exists():
            raise ValueError("stage outside worlds and prepared resources")
    manifest = read_checked(carry / "horizon-mod.toml")
    meta = tomllib.loads(manifest.decode())
    if (meta.get("id"), meta.get("version"), meta.get("api"), meta.get("side")) != (
            "betterdungeons", VERSION, "0.2", "both"):
        raise ValueError("unexpected source module identity")
    overrides, unresolved, provenance = replacements(jar, carry)
    payloads = {"horizon-mod.toml": manifest}
    for kind in ("assets", "data"):
        for path in sorted((carry / kind).rglob("*")):
            if path.is_symlink():
                raise ValueError("symlink in carried input")
            if path.is_file():
                payloads[path.relative_to(carry).as_posix()] = read_checked(path)
    payloads.update(overrides)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".yung-dungeons-", dir=output.parent) as temporary:
        root = Path(temporary) / "content"
        for name, data in payloads.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        subprocess.run([str(sdk.resolve()), "build"], cwd=root, check=True,
                       capture_output=True, text=True, timeout=180)
        package = root / "target/horizon-mod/betterdungeons.hmod"
        verdict = json.loads(subprocess.run([str(sdk.resolve()), "check", str(package), "--json"],
                             cwd=root, check=True, capture_output=True, text=True, timeout=180).stdout)
        facts = verdict.get("report", {})
        checksum = hashlib.sha256(package.read_bytes()).hexdigest()
        if (not verdict.get("ok") or facts.get("sha256") != checksum or
                (facts.get("id"), facts.get("version"), facts.get("api"), facts.get("side")) !=
                ("betterdungeons", VERSION, "0.2", "both")):
            raise ValueError("SDK rejected derived module identity")
        report = {"schema": 1, "minecraft": "26.3", "id": "betterdungeons",
                  "source_version": VERSION, "source_jar_sha1": SOURCE_SHA1,
                  "source_json_sha256": provenance, "sha256": checksum,
                  "restored_fixed_mob_processors": 3, "adapted_files": sorted(overrides),
                  "restored_chest_limit_processors": 3,
                  "chest_configuration": {"min": 1, "max": 2, "chance": 0.2,
                                          "replacement": "minecraft:cave_air",
                                          "source_configuration": "original mod defaults"},
                  "native_spawner_block_entity_id_restored": True,
                  "still_dropped_in_selected_lists": unresolved,
                  "source_files_modified": False, "sdk_validated": True,
                  "random_trace_parity_verified": False, "full_mod_ported": False}
        (root / "techquest-dungeons-trial.json").write_text(json.dumps(report, indent=2) + "\n")
        root.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("work", "jar", "sdk", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    report = stage(**vars(parser.parse_args()))
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("still_dropped_in_selected_lists", "source_json_sha256")}, indent=2))


if __name__ == "__main__":
    main()

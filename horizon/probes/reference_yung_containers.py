#!/usr/bin/env python3
"""Read original small-dungeon containers and removed chest positions via RCON."""
import argparse
import json
from pathlib import Path
import re
import tomllib

from reference_yung_spawners import Reference


def verify_default_limits(server):
    config = tomllib.loads((server / "config/betterdungeons-neoforge-1_21.toml").read_text())
    small = config["YUNG's Better Dungeons"]["Small Dungeons"]
    if (small.get("Small Dungeon Min Chest Count"), small.get("Small Dungeon Max Chest Count")) != (1, 2):
        raise ValueError("the partial adapter supports original default chest limits only")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir", "plans", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    reference = Reference(args.server_dir)
    verify_default_limits(args.server_dir)
    plans = json.loads(args.plans.read_text())
    if plans["seed"] != 263 or any(p["id"] != "betterdungeons:small_dungeon" for p in plans["plans"]):
        parser.error("expected the reviewed small-dungeon plan")
    if "There are 0 " not in reference.command("list"):
        raise ValueError("reference server must have no connected players")
    structures = []
    for plan in plans["plans"]:
        candidates = []
        for candidate in plan["block_entity_candidates_before_processors"]:
            if candidate["block"] == "minecraft:spawner":
                continue
            position = " ".join(map(str, candidate["position"]))
            actual = None
            for block in (candidate["block"], "minecraft:air", "minecraft:cave_air"):
                if "Test passed" in reference.command(f"execute if block {position} {block}"):
                    actual = block
                    break
            record = {"position": candidate["position"], "expected_block": candidate["block"],
                      "actual_block": actual, "block_present": actual == candidate["block"],
                      "loot_table": None}
            if record["block_present"]:
                response = reference.command(f"data get block {position}")
                loot = re.search(r'LootTable: "([a-z0-9_:/.\-]+)"', response)
                record["loot_table"] = loot.group(1) if loot else None
            candidates.append(record)
        structures.append({"id": plan["id"], "chunk": plan["chunk"], "candidates": candidates})
    report = {"schema": 1, "minecraft": "1.21.1", "seed": 263,
              "source_configuration": "original mod defaults", "structures": structures}
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    all_candidates = [c for s in structures for c in s["candidates"]]
    print("Original container candidates:", len(all_candidates),
          "still present:", sum(c["block_present"] for c in all_candidates))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read actual block entities at a planner's candidates; never place structures.

Candidates precede processors/overlap: a missing candidate is recorded, not
treated as a failed structure. No accounts, game NBT or raw logs are exported.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import uuid


def observe(binary: Path, server: Path, plan: dict) -> dict:
    def command(line):
        return subprocess.run([str(binary), "--dir", str(server), "cmd", line],
                              capture_output=True, text=True, check=True,
                              timeout=90).stdout

    observations = []
    for candidate in plan["block_entity_candidates_before_processors"]:
        position = " ".join(map(str, candidate["position"]))
        marker = "TQ_BLOCK_" + uuid.uuid4().hex
        present = marker in command(
            f"execute if block {position} {candidate['block']} run say {marker}")
        result = {"position": candidate["position"], "expected_block": candidate["block"],
                  "block_present": present, "template": candidate["template"],
                  "source_loot_table": candidate["source_loot_table"],
                  "source_spawn_entity": candidate["source_spawn_entity"]}
        result["actual_block"] = candidate["block"] if present else None
        if not present:
            for block in ("minecraft:air", "minecraft:cave_air"):
                marker = "TQ_REPLACEMENT_" + uuid.uuid4().hex
                if marker in command(f"execute if block {position} {block} run say {marker}"):
                    result["actual_block"] = block
                    break
        if present:
            # Sequential queries keep command responses associated with their
            # own block; only identifiers and numeric spawner fields leave here.
            response = command(f"data get block {position}")
            if f"{', '.join(map(str, candidate['position']))} has the following block data:" not in response:
                raise RuntimeError("block entity response missing or belongs to another position")
            loot = re.search(r'LootTable: "([a-z0-9_:/.\-]+)"', response)
            spawn = re.search(r'SpawnData: \{entity: \{id: "([a-z0-9_:/.\-]+)"', response)
            result.update(loot_table=loot.group(1) if loot else None,
                          spawn_entity=spawn.group(1) if spawn else None,
                          spawn_potential_entity_matches=(
                              f'SpawnPotentials: [{{data: {{entity: {{id: "{spawn.group(1)}"}}}}' in response
                              if spawn else None),
                          spawner_fields={key: int(match.group(1)) for key in (
                              "Delay", "MinSpawnDelay", "MaxSpawnDelay", "SpawnCount",
                              "MaxNearbyEntities", "RequiredPlayerRange", "SpawnRange")
                              if (match := re.search(rf'\b{key}: (-?\d+)s\b', response))})
        observations.append(result)
    return {"id": plan["id"], "chunk": plan["chunk"], "piece_count": plan["piece_count"],
            "candidates": observations}


def compare_reference(report, reference):
    if (reference.get("minecraft"), reference.get("seed")) != ("1.21.1", report["seed"]):
        raise ValueError("expected the original 1.21.1 oracle with the same seed")
    originals = {tuple(p["position"]): p for p in reference["probes"]}
    actuals = {tuple(c["position"]): c for s in report["structures"] for c in s["candidates"]
               if c["expected_block"] == "minecraft:spawner"}
    if not originals or set(originals) != set(actuals) or len(originals) != len(reference["probes"]):
        raise ValueError("reference spawner positions differ from native cases")
    mismatches = []
    for position, expected in originals.items():
        actual = actuals[position]
        if (not actual["block_present"] or
                actual.get("spawn_entity") != expected["spawn_entity"] or
                actual.get("spawner_fields") != expected["fields"] or
                actual.get("spawn_potential_entity_matches") is not True or
                expected.get("potential_entity_matches") is not True):
            mismatches.append(list(position))
    return {"cases": len(originals), "numeric_fields_compared": len(originals) * 7,
            "source_mobs": sorted({p["spawn_entity"] for p in originals.values()}),
            "mismatch_positions": mismatches}


def compare_containers(report, reference):
    if (reference.get("minecraft"), reference.get("seed")) != ("1.21.1", report["seed"]):
        raise ValueError("expected original container observations with the same seed")
    expected = {tuple(c["position"]): c for s in reference["structures"] for c in s["candidates"]}
    actual = {tuple(c["position"]): c for s in report["structures"] for c in s["candidates"]
              if c["expected_block"] != "minecraft:spawner"}
    if not expected or set(expected) != set(actual):
        raise ValueError("reference container positions differ from native cases")
    mismatches = []
    for pos, original in expected.items():
        native = actual[pos]
        if original["actual_block"] is None:
            raise ValueError("original container replacement was not classified")
        if (native["actual_block"] != original["actual_block"] or
                native["expected_block"] != original["expected_block"] or
                native.get("loot_table") != original["loot_table"]):
            mismatches.append({"position": list(pos), "expected_block": original["actual_block"],
                               "actual_block": native["actual_block"],
                               "expected_loot": original["loot_table"],
                               "actual_loot": native.get("loot_table")})
    return {"cases": len(expected), "original_containers": sum(c["block_present"] for c in expected.values()),
            "native_containers": sum(c["block_present"] for c in actual.values()),
            "mismatches": mismatches}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--plans", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=Path,
                        help="Optional output of reference_yung_spawners.py")
    parser.add_argument("--reference-containers", type=Path,
                        help="Optional output of reference_yung_containers.py")
    args = parser.parse_args()
    plans = json.loads(args.plans.read_text())
    if args.output.exists():
        parser.error("output already exists")
    report = {"schema": 1, "seed": plans["seed"], "minecraft": plans["minecraft"],
              "mode": "read-only block entity observations after explicit manual placement",
              "natural_generation_verified": False, "loot_opening_verified": False,
              "spawner_activation_verified": False,
              "structures": [observe(args.binary.resolve(), args.server_dir.resolve(), p)
                             for p in plans["plans"]]}
    if args.reference:
        report["original_comparison"] = compare_reference(report, json.loads(args.reference.read_text()))
    if args.reference_containers:
        report["container_comparison"] = compare_containers(report, json.loads(args.reference_containers.read_text()))
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    for structure in report["structures"]:
        present = [c for c in structure["candidates"] if c["block_present"]]
        print(structure["id"], "present candidates:", len(present),
              "spawners:", sum(c.get("spawn_entity") is not None for c in present),
              "loot references:", sum(c.get("loot_table") is not None for c in present))
    if args.reference and report["original_comparison"]["mismatch_positions"]:
        raise SystemExit("original/native spawner comparison failed; see output")
    if args.reference_containers and report["container_comparison"]["mismatches"]:
        raise SystemExit("original/native container comparison failed; see output")


if __name__ == "__main__":
    main()

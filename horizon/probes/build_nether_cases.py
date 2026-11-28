#!/usr/bin/env python3
"""Use only input labels from the vanilla oracle to build native vegetation vectors."""
import importlib.util
import json
from pathlib import Path
import sys


def main():
    reference, output = map(Path, sys.argv[1:])
    if output.exists():
        raise ValueError("output must be new")
    spec = importlib.util.spec_from_file_location(
        "adapter", Path(__file__).parents[1] / "tools/prepare_terralith_worldgen.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    names = ["stone", "dirt", "granite", "andesite", "diorite", "blackstone"]
    provider = {"type": "minecraft:weighted", "entries": [
        {"data": {"id": "minecraft:" + name}, "weight": weight}
        for name, weight in zip(names, [3, 7, 20, 20, 20, 50])]}
    native, count = adapter.normalize_nether_vegetation({"type": "minecraft:nether_forest_vegetation",
        "spread_width": 8, "spread_height": 4, "state_provider": provider})
    if count != 1:
        raise AssertionError("not transformed")
    rows = [{**{key: row[key] for key in ("support", "mode", "origin_y", "seed")}, "native": native}
            for row in json.loads(reference.read_text())["cases"]]
    output.write_text(json.dumps(rows) + "\n")
    print(f"Wrote {len(rows)} vegetation input vectors")


if __name__ == "__main__":
    main()

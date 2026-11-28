#!/usr/bin/env python3
"""Build native input vectors from oracle input labels, never from its results."""
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
    native, count = adapter.normalize_forest_rocks({"type": "minecraft:forest_rock",
                                                  "state": {"id": "minecraft:mossy_cobblestone"}})
    if count != 1:
        raise AssertionError("not transformed")
    rows = [{"support": row["support"], "seed": row["seed"], "native": native}
            for row in json.loads(reference.read_text())["cases"]]
    output.write_text(json.dumps(rows) + "\n")
    print(f"Wrote {len(rows)} rock input vectors")


if __name__ == "__main__":
    main()

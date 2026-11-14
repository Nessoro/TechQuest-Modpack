#!/usr/bin/env python3
"""Synthetic patch vectors; expected traces come from the official 1.21.1 loop."""
import importlib.util
import itertools
import json
from pathlib import Path
import sys


def main():
    output = Path(sys.argv[1])
    if output.exists():
        raise ValueError("refusing to overwrite vectors")
    spec = importlib.util.spec_from_file_location(
        "adapter", Path(__file__).parents[1] / "tools/prepare_terralith_worldgen.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    cases = []
    for seed, tries, spreads, kind, child_offset, accept in itertools.product(
            [0, 1, -1, 263, 2**63-1], [0, 1, 7, 64], [(0, 0), (7, 3), (12, 16), (16, 16)],
            ["random_patch", "flower"], [False, True], [False, True]):
        placement = []
        if child_offset:
            def uniform(low, high):
                return {"type": "minecraft:uniform", "min_inclusive": low, "max_inclusive": high}
            placement.append({"type": "minecraft:offset", "x": uniform(-2, 2),
                              "y": uniform(-1, 1), "z": uniform(-2, 2)})
        placement.append({"type": "minecraft:block_predicate_filter", "predicate": {
            "type": "minecraft:matching_blocks", "blocks": ["minecraft:stone"]}})
        patch = {"type": "minecraft:" + kind, "tries": tries,
                 "xz_spread": spreads[0], "y_spread": spreads[1],
                 "feature": {"feature": {"type": "minecraft:no_op"}, "placement": placement}}
        native, count = adapter.normalize_patches(patch)
        if count != 1:
            raise AssertionError("patch was not transformed")
        cases.append({"seed": seed, "tries": tries, "xz_spread": spreads[0],
                      "y_spread": spreads[1], "kind": kind, "child_offset": child_offset,
                      "accept_alternate": accept, "native": native})
    output.write_text(json.dumps(cases) + "\n")
    print(f"Wrote {len(cases)} patch vectors")


if __name__ == "__main__":
    main()

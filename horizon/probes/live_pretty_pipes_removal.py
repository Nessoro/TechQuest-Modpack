#!/usr/bin/env python3
"""Compare loaded-pipe removal with the independent original onRemove oracle."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

from live_pretty_pipes import Native, verify

POSITION = "256 210 128"
CONTEXT = "execute positioned " + POSITION
ITEMS = "@e[type=minecraft:item,distance=..6]"


def drops(native):
    raw = native.command(f"{CONTEXT} as {ITEMS} run data get entity @s Item")
    result = {}
    for line in raw.splitlines():
        item = re.search(r'\bid:\s*"([a-z0-9_:/.\-]+)"', line)
        count = re.search(r'\bcount:\s*(\d+)', line)
        if item and count:
            result[item[1]] = result.get(item[1], 0) + int(count[1])
    return result, raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir", "original", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--observe-only", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    lock = verify(args.server_dir)
    if "prettypipes" not in lock["modules"]:
        raise ValueError("installed Pretty Pipes required")
    expected = json.loads(args.original.read_text())["checks"]["removal"]
    native = Native(args.server_dir, Path(lock["server_binary"]))
    try:
        native.command("tick freeze")
        native.command("forceload add 240 112 272 144")
        deadline = time.monotonic() + 45
        while "Test passed" not in native.command(f"execute if loaded {POSITION}"):
            if time.monotonic() >= deadline:
                raise TimeoutError("removal fixture chunk not loaded")
            time.sleep(0.1)
        native.command(f"{CONTEXT} run kill {ITEMS}")
        native.command('summon minecraft:item 256.5 210.5 128.5 {Item:{id:"minecraft:gold_nugget",count:3},PickupDelay:32767s}')
        control, raw = drops(native)
        if control != {"minecraft:gold_nugget": 3}:
            raise RuntimeError("drop observation positive control failed: " + raw[:600])
        native.command(f"{CONTEXT} run kill {ITEMS}")
        checks = {}
        same_pipe_preserved = []
        repeated_removal_safe = []
        for mode in ("replace", "destroy"):
            native.command(f"setblock {POSITION} minecraft:air")
            native.command("setblock 255 210 128 minecraft:chest")
            if "Changed the block" not in native.command(f"setblock {POSITION} prettypipes:pipe"):
                raise RuntimeError("pipe placement failed")
            # A synthetic queue and module inventory, matching the original's
            # onRemove fixture. Natural transport is tested separately.
            native.command(f'data merge block {POSITION} {{modules:{{Size:3,Items:[{{Slot:0b,id:"prettypipes:low_extraction_module",count:1}}]}},Items:[{{Slot:0b,id:"minecraft:iron_ingot",count:8}}]}}')
            state = native.command(f"data get block {POSITION}")
            if 'prettypipes:low_extraction_module' not in state or 'minecraft:iron_ingot' not in state:
                raise RuntimeError("fixture NBT not installed")
            native.command(f"{CONTEXT} run kill {ITEMS}")
            before_up = "Test passed" in native.command(f"execute if block {POSITION} prettypipes:pipe[up=true]")
            target_up = "false" if before_up else "true"
            if "Changed the block" not in native.command(f"setblock {POSITION} prettypipes:pipe[up={target_up}] strict"):
                raise RuntimeError("same-pipe property control did not change state")
            state = native.command(f"data get block {POSITION}")
            intact = ('prettypipes:low_extraction_module' in state and
                      'minecraft:iron_ingot' in state and drops(native)[0] == {})
            same_pipe_preserved.append(intact)
            if not intact:
                raise AssertionError("changing only a pipe property lost its inventory")
            native.command(f"setblock {POSITION} minecraft:air" + (" destroy" if mode == "destroy" else ""))
            actual, raw = drops(native)
            native.command(f"setblock {POSITION} minecraft:air")
            repeated_removal_safe.append(drops(native)[0] == actual)
            removed = "Test passed" in native.command(f"execute if block {POSITION} minecraft:air")
            checks[mode] = {"dropped": actual, "pipe_removed": removed}
        passed = all(checks[mode] == expected[mode] for mode in checks)
        if not all(repeated_removal_safe):
            raise AssertionError("repeated removal duplicated contents")
        report = {"schema": 1, "minecraft": "26.3", "checks": checks,
                  "matches_original": passed, "queue_and_module_fixture_injected": True,
                  "drop_query_positive_control_passed": True,
                  "same_pipe_state_preserves_inventory": all(same_pipe_preserved),
                  "repeated_removal_no_duplicates": all(repeated_removal_safe),
                  "creative_player_dispatch_tested": False, "real_client_tested": False}
        with args.output.open("x") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(json.dumps(report))
        if not passed and not args.observe_only:
            raise AssertionError("pipe removal differs from original")
    finally:
        native.command("save-all flush")
        subprocess.run([str(native.binary), "--dir", str(native.server), "stop"],
                       check=True, capture_output=True, text=True, timeout=90)


if __name__ == "__main__":
    main()

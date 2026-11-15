#!/usr/bin/env python3
"""Original Pretty Pipes 1.22.0 oracle in a private, fresh NeoForge test world.

The prepare phase creates its fixture, checks routing controls, saves an item
batch in flight and stops. Reopen the same server, then run verify. No native
Horizon port is claimed by this developer harness.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from reference_yung_spawners import Reference

SOURCE = Path(__file__).resolve().parents[1] / "source/techquest-post-pr48-candidate.json"
INPUT, OUTPUT, MODULE = "128 200 176", "132 200 176", "129 200 176"


def observe(reference, position):
    response = reference.command(f"data get block {position} Items")
    if f"{position.replace(' ', ', ')} has the following block data:" not in response:
        raise RuntimeError("inventory response missing or belongs to another position")
    ids = re.findall(r'id: "([a-z0-9_:/.\-]+)"', response)
    counts = list(map(int, re.findall(r'\bcount: (\d+)', response)))
    if len(ids) != len(counts) or any(i != "minecraft:iron_ingot" for i in ids):
        raise RuntimeError("unexpected fixture item or inventory encoding")
    if not ids and not response.rstrip().endswith("[]"):
        raise RuntimeError("unrecognized empty inventory encoding")
    return sum(counts)


def snapshot(reference):
    return {"input": observe(reference, INPUT), "output": observe(reference, OUTPUT)}


def sprint(reference, ticks):
    def clock():
        match = re.search(r"The time is (\d+)", reference.command("time query gametime"))
        if not match:
            raise RuntimeError("original game clock unavailable")
        return int(match.group(1))
    before = clock()
    if "sprinting" not in reference.command(f"tick sprint {ticks}"):
        raise RuntimeError("original tick sprint rejected")
    deadline = time.monotonic() + 30
    while clock() < before + ticks:
        if time.monotonic() >= deadline:
            raise TimeoutError("original tick sprint did not finish")
        time.sleep(0.05)


def module(reference, tier):
    text = f'{{modules:{{Size:3,Items:[{{Slot:0b,id:"prettypipes:{tier}_extraction_module",count:1}}]}}}}'
    if "Modified block data" not in reference.command(f"data merge block {MODULE} {text}"):
        raise RuntimeError("module fixture update failed")
    if f'"prettypipes:{tier}_extraction_module"' not in reference.command(f"data get block {MODULE} modules"):
        raise RuntimeError("original extraction module not installed")


def inventory(reference, position, count):
    items = f'[{{Slot:0b,id:"minecraft:iron_ingot",count:{count}}}]' if count else "[]"
    reference.command(f"data merge block {position} {{Items:{items}}}")
    if observe(reference, position) != count:
        raise RuntimeError("inventory fixture update failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("prepare", "verify"), required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    pin = json.loads(SOURCE.read_text())["modrinth_lock"]["XExdLWCQ"]
    if pin["version"] != "1.22.0":
        raise ValueError("review another Pretty Pipes version before running this oracle")
    jar = args.server_dir / "mods" / pin["filename"]
    if hashlib.sha512(jar.read_bytes()).hexdigest() != pin["sha512"]:
        raise ValueError("reference mod differs from the pinned source")
    reference = Reference(args.server_dir)
    if "There are 0 " not in reference.command("list"):
        raise ValueError("reference test requires zero connected players")
    reference.command("tick freeze")
    reference.command("forceload add 112 160 144 192")
    deadline = time.monotonic() + 30
    while "Test passed" not in reference.command(f"execute if loaded {INPUT}"):
        if time.monotonic() >= deadline:
            raise TimeoutError("reference fixture chunk not loaded")
        time.sleep(0.1)
    checks = {}
    if args.phase == "prepare":
        reference.command("fill 124 198 172 136 204 180 minecraft:air")
        for position, block in ((INPUT, "minecraft:chest"), (OUTPUT, "minecraft:chest"),
                                (MODULE, "prettypipes:pipe"), ("130 200 176", "prettypipes:pipe"),
                                ("131 200 176", "prettypipes:pipe")):
            if "Changed the block" not in reference.command(f"setblock {position} {block}"):
                raise RuntimeError("reference fixture block placement failed")
        inventory(reference, INPUT, 8)
        sprint(reference, 300)
        checks["without_extraction_module"] = snapshot(reference)
        assert checks["without_extraction_module"] == {"input": 8, "output": 0}
        module(reference, "low")
        sprint(reference, 400)
        checks["low_module_delivery"] = snapshot(reference)
        assert checks["low_module_delivery"] == {"input": 0, "output": 8}
        reference.command("setblock 130 200 176 minecraft:air")
        inventory(reference, INPUT, 8)
        inventory(reference, OUTPUT, 0)
        sprint(reference, 100)
        checks["disconnected_network"] = snapshot(reference)
        assert checks["disconnected_network"] == {"input": 8, "output": 0}
        reference.command("setblock 130 200 176 prettypipes:pipe")
        module(reference, "high")
        sprint(reference, 20)
        checks["saved_while_in_flight"] = snapshot(reference)
        assert checks["saved_while_in_flight"] == {"input": 0, "output": 0}
        if "Saved the game" not in reference.command("save-all flush"):
            raise RuntimeError("reference world save failed")
    else:
        checks["immediately_after_reopen"] = snapshot(reference)
        sprint(reference, 400)
        checks["delivery_after_reopen"] = snapshot(reference)
        assert checks["delivery_after_reopen"] == {"input": 0, "output": 8}
        reference.command("save-all flush")
    report = {"schema": 1, "phase": args.phase, "source_minecraft": "1.21.1",
              "loader": "NeoForge 21.1.264", "pretty_pipes": "1.22.0",
              "version_id": pin["version_id"], "jar_sha512": pin["sha512"],
              "online_mode": True, "whitelist": True, "bind": "127.0.0.1",
              "seed": 263, "players_connected": 0, "checks": checks,
              "horizon_port_tested": False, "exact_transfer_timing_tested": False}
    if "Stopping the server" not in reference.command("stop"):
        raise RuntimeError("reference stop not acknowledged")
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("Pretty Pipes original", args.phase, "checks:", checks)


if __name__ == "__main__":
    main()

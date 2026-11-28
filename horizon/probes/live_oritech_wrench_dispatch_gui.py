#!/usr/bin/env python3
"""Check machine menu/neighbor wrench dispatch through a real local GUI.

Blocks, core flags/geometry, inventory, 333 E cable buffers, travel and time
are scalar fixtures. The original menu-request boundary is compared with an
actual Horizon window. No account, full menu renderer or Java packet claim.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

from graphical_fixture import GraphicalFixture

POS = (129, 200, 176)
WIRE = (128, 200, 176)
TOOL = "oritech:wrench"
AIR = "minecraft:air"
MACHINES = {"oritech:"+name+"_block": n for name, n in
            (("basic_generator", 1), ("pulverizer", 3), ("powered_furnace", 2), ("foundry", 3), ("assembler", 5))}
coord = lambda p: " ".join(map(str, p))


def selected(row):
    main, off = row["main"], row["off"]
    primary = (main, off) in ((TOOL, AIR), (AIR, TOOL))
    normal = not row["creative"] and not row["initial_cooldown"]
    if row["block"] in MACHINES and row["assembled_fixture"] and normal and primary:
        return True
    if row["block"] == "oritech:basic_generator_block" and row["connected"]:
        if normal and not row["wet"] and not primary:
            return True
        if row["initial_cooldown"] or row["creative"] and primary:
            return True
    return (normal and row["connected"] and not row["wet"] and main == TOOL and off == AIR
            and (not row["assembled_fixture"] or row["block"] in ("minecraft:chest", "minecraft:stone")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("server-dir", "work", "original"):
        parser.add_argument("--"+key, type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0, help="diagnostic prefix, never a complete acceptance run")
    args = parser.parse_args()
    original = json.loads(args.original.read_text())
    assert original["original_server_use_item_on_and_use_item_executed"]
    rows = [row for row in original["rows"] if selected(row)]
    if args.limit:
        rows = rows[:args.limit]
    game = GraphicalFixture(args.server_dir, args.work, ("0.8.0", "0.9.0"), "machine-dispatch", "TQDispatchGui", module="oritech", frozen=True)
    cmd, call, settle = game.command, game.call, game.settle
    checks, timings = [], []

    def wire():
        b = call("block", *WIRE)
        props = dict(v.split("=", 1) for v in b["state"].split("[", 1)[1].rstrip("]").split(","))
        out = {"block": b["block"], "properties": props, "has_energy": b["block"] == "oritech:energy_pipe_connection"}
        if out["has_energy"]:
            raw = cmd("data get block "+coord(WIRE)+" energy")
            out["energy"] = int(re.search(r"block data:\s*(-?\d+)", raw)[1])
        return out

    def setup(row):
        call("close"); call("key", "shift", "up"); settle()
        cmd("gamemode " + ("creative" if row["creative"] else "survival"))
        cmd("fill 126 200 174 132 202 178 minecraft:air")
        cmd("clear @s")
        suffix = "{techquest_assembled:1b}" if row["assembled_fixture"] and row["block"] in MACHINES else ""
        cmd("setblock "+coord(POS)+" "+row["block"]+suffix)
        if row["assembled_fixture"] and row["block"] in ("oritech:powered_furnace_block", "oritech:foundry_block", "oritech:assembler_block"):
            offsets = [(0, 1, 0)] if row["block"] == "oritech:powered_furnace_block" else [(1, 0, 0), (0, 1, 0), (1, 1, 0)]
            for dx, dy, dz in offsets:
                p = (POS[0]+dx, POS[1]+dy, POS[2]+dz)
                cmd("setblock "+coord(p)+f" oritech:machine_core_1{{techquest_core_used:1b,controller_x:{-dx},controller_y:{-dy},controller_z:{-dz}}}")
        before = row["before"]["wire"]
        cmd("setblock "+coord(WIRE)+" oritech:energy_pipe[waterlogged="+str(row["wet"]).lower()+"]")
        state = before["block"]+"["+",".join(k+"="+v for k,v in sorted(before["properties"].items()))+"]"
        cmd("setblock "+coord(WIRE)+" "+state)
        if before["has_energy"]:
            cmd("data merge block "+coord(WIRE)+" {energy:"+str(before["energy"])+"}")
        assert wire() == before, row["name"]
        if row["off"] != AIR:
            cmd("give @s "+row["off"]); call("select", row["off"])
            call("key", "f", "tap"); settle()
        if row["main"] != AIR:
            cmd("give @s "+row["main"]); call("select", row["main"])
        cmd("tp @s 126.5 200 176.1")
        if row["shift"]:
            call("key", "shift", "down"); settle()
        eye = call("state")["player"]["eye"]
        dx, dy, dz = POS[0]+.01-eye[0], POS[1]+.8-eye[1], POS[2]+.1-eye[2]
        yaw = math.degrees(math.atan2(-dx, dz))
        pitch = math.degrees(math.atan2(-dy, math.hypot(dx, dz)))
        call("look", yaw, pitch); settle(); call("wait", 12)
        target = call("looking-at")["block"]
        assert target["pos"] == list(POS) and target["face"] == "west", (row["name"], target)
        return yaw, pitch

    def click(row, angles):
        if row["initial_cooldown"]:
            yaw, pitch = angles
            lines = ["status", "look 0 -90", "mouse right click", f"look {yaw} {pitch}", "mouse right click", "wait 1", "screen", "status"]
            result = subprocess.run([str(game.ctl), "--socket", str(game.socket), "script", "-"],
                                    input="\n".join(lines)+"\n", cwd=game.work, env=game.env,
                                    capture_output=True, text=True, check=True, timeout=30)
            replies = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            timings.append({"case": row["name"], "lines": lines, "replies": replies})
            assert 0 < replies[5]["ticks"]-replies[0]["ticks"] <= 8, timings[-1]
            return replies[6]
        call("mouse", "right", "click"); settle()
        return call("screen")

    def check(row, screen):
        expected = row["click"]
        assert (screen["screen"] == "container") == expected["menu_requested"], (row, screen)
        if expected["menu_requested"]:
            slots = {s["slot"] for s in screen["slots"] if 300 <= s["slot"] < 500}
            assert len(slots) == expected["menu_slots"]-36, (row["name"], screen)
        actual = wire()
        assert actual == expected["after"]["wire"], (row["name"], actual, expected["after"]["wire"])
        counts = Counter()
        for entry in expected["inventory"]:
            counts[entry["item"]] += entry["count"]
        assert call("inventory")["counts"] == dict(counts), (row["name"], call("inventory"), counts)
        return {"case": row["name"], "block": row["block"], "shift": row["shift"], "wet": row["wet"],
                "creative": row["creative"], "main": row["main"], "off": row["off"],
                "menu_open": expected["menu_requested"], "wire": actual, "inventory": dict(counts)}

    try:
        game.start("matrix")
        cmd("difficulty peaceful"); cmd("gamemode spectator")
        cmd("tp @s 126.5 200 176.1"); call("wait-ready", timeout=180)
        cmd("tick freeze"); cmd("forceload add 112 160 144 192"); call("wait", 40)
        cmd("fill 124 199 173 134 199 179 minecraft:glass")
        for i, row in enumerate(rows):
            angles = setup(row); screen = click(row, angles)
            checked = check(row, screen); checks.append(checked)
            (game.work/"matrix-progress.json").write_text(json.dumps(checks, indent=2)+"\n")
            if i == 0 and screen["screen"] == "container":
                call("screenshot", game.work/"held-wrench-machine-menu.png")
            print("matched", i+1, "/", len(rows), row["name"], row["block"], flush=True)
        saved_row = next(row for row in original["rows"] if row["block"] == "oritech:basic_generator_block" and row["wet"] and not row["connected"] and row["shift"] and row["main"] == TOOL and row["off"] == AIR and not row["creative"])
        setup(saved_row); call("key", "shift", "up"); settle()
        saved = wire(); inventory = call("inventory")["counts"]
        call("screenshot", game.work/"wet-disconnected-neighbor.png"); call("save")
    finally:
        game.stop()
    try:
        game.start("physical-reopen")
        cmd("tick freeze")
        assert wire() == saved and call("inventory")["counts"] == inventory
        call("key", "shift", "down"); settle()
        eye = call("state")["player"]["eye"]
        delta = [POS[0]+.01-eye[0], POS[1]+.8-eye[1], POS[2]+.1-eye[2]]
        call("look", math.degrees(math.atan2(-delta[0],delta[2])), math.degrees(math.atan2(-delta[1],math.hypot(delta[0],delta[2])))); settle()
        call("wait", 12); call("mouse", "right", "click"); settle()
        reopened = wire()
        assert reopened["block"] == "oritech:energy_pipe_connection" and reopened["energy"] == 0 and reopened["properties"]["waterlogged"] == "true", reopened
        call("key", "shift", "up"); settle()
        call("screenshot", game.work/"restored-neighbor-connected.png")
        assert call("status")["server"]["decode_errors"] == 0
    finally:
        game.stop()
    result = {"schema": 1, "content_version": game.version, "matched_cases": len(checks), "diagnostic_prefix_only": bool(args.limit),
              "checks": checks, "timing_observations": timings, "wet_disabled_neighbor_reopen_and_reconnect": True,
              "scalar_endpoint_energy_seeded": 333, "assembly_and_inventory_fixtures": True,
              "protocol_decode_errors": 0, "licensed_multiplayer_tested": False,
              "screenshots_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in game.work.glob("*.png")}}
    (game.work/"checked-result.json").write_text(json.dumps(result, indent=2)+"\n")
    print("Machine dispatch matched", len(checks), "original cases and physical wet-neighbor reopen")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Craft and use two cable wrenches through a real local graphical player.

Metals, cable blocks, generator, platform, bench, travel and time are fixtures.
No account is used. Buffer-discard checks deliberately seed 333 energy; they
are scalar contracts, not an energy-production or survival progression proof.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

from graphical_fixture import GraphicalFixture
from live_oritech_gathered_gui import GatheredChain, TABLE

A = (-2268, 201, 2272)
B = (-2267, 201, 2272)
WRENCH = "oritech:wrench"
coord = lambda p: " ".join(map(str, p))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir", "work"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    game = GraphicalFixture(args.server_dir, args.work, "0.7.0", "wrench-controls", "TQWrenchGui", module="oritech", frozen=True)
    test = GatheredChain(game)
    cmd, call, settle = game.command, game.call, game.settle
    observations = []

    def states():
        return [call("block", *p)["state"] for p in (A, B)]

    def aim():
        # A diagonal center ray avoids the opposite outer arm. This is an
        # actual thin-outline hit, not a forced block/face fixture.
        cmd(f"tp @s {A[0]+1.2} 200.5 {A[2]+.05}")
        call("look", math.degrees(math.atan2(.7, .45)), math.degrees(math.atan2(.62, math.hypot(.7, .45))))
        settle()
        assert call("looking-at")["block"]["pos"] == list(A)

    def click():
        call("mouse", "right", "click")
        settle()

    def pair():
        cmd("setblock " + coord(A) + " minecraft:air")
        cmd("setblock " + coord(B) + " minecraft:air")
        cmd("setblock " + coord(A) + " oritech:energy_pipe")
        cmd("setblock " + coord(B) + " oritech:energy_pipe")
        assert "east=1" in states()[0] and "west=1" in states()[1]

    def disabled():
        value = states()
        assert "east=0" in value[0] and "west=0" in value[1], value
        return value

    def tools():
        inv = call("inventory")
        assert inv["counts"].get(WRENCH) == 2, inv
        assert inv["offhand"]["item"] == WRENCH and inv["offhand"]["count"] == 1, inv

    def endpoint_aim():
        # Stand north of the full-cube provider, so neither the player's
        # body nor its ray passes through it. This ray also reaches the
        # disconnected cable's center from its east side.
        cmd(f"tp @s {A[0]+1.1} 200.5 {A[2]-.31}")
        call("look", math.degrees(math.atan2(.6, .91)), math.degrees(math.atan2(.665, math.hypot(.6, .91))))
        settle()
        assert call("looking-at")["block"]["pos"] == list(A)

    def rapid(lines):
        # One ctl connection, normal input commands; preserve complete JSON
        # replies for reviewing the timing, rather than asserting tick freeze
        # also freezes the player's cooldown (it does not).
        result = subprocess.run([str(game.ctl), "--socket", str(game.socket), "script", "-"],
                                input="\n".join(lines)+"\n", cwd=game.work, env=game.env,
                                capture_output=True, text=True, timeout=30, check=True)
        replies = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        observations.append({"lines": lines, "replies": replies})
        (game.work/"timing-observations.json").write_text(json.dumps(observations, indent=2)+"\n")
        return replies

    def shift_remove(creative, endpoint):
        cmd("gamemode " + ("creative" if creative else "survival"))
        cmd("setblock " + coord(B) + (" oritech:basic_generator_block" if endpoint else " oritech:energy_pipe"))
        cmd("setblock " + coord(A) + " minecraft:air")
        cmd("setblock " + coord(A) + " oritech:energy_pipe")
        expected = "oritech:energy_pipe_connection" if endpoint else "oritech:energy_pipe"
        assert call("block", *A)["block"] == expected
        if endpoint:
            cmd("data merge block " + coord(A) + " {energy:333}")
        before = test.counts().get("oritech:energy_pipe", 0)
        cmd(f"tp @s {A[0]+.5} 200 {A[2]-2}")
        call("select", WRENCH)
        call("key", "shift", "down"); settle()
        call("look-at-block", *A); settle(); click()
        call("key", "shift", "up"); settle()
        assert call("block", *A)["block"] == "minecraft:air"
        drops = [e for e in call("entities", 12, "minecraft:item")["entities"]
                 if e.get("item", {}).get("item") == "oritech:energy_pipe"]
        assert sum(e["item"]["count"] for e in drops) == 1, drops
        cmd("tick unfreeze")
        cmd(f"tp @s {A[0]+.5} 200 {A[2]+.5}"); call("wait", 35)
        cmd("tick freeze")
        assert test.counts().get("oritech:energy_pipe", 0) == before+1
        tools()
        return {"creative": creative, "endpoint": endpoint, "drops": 1, "discarded_buffer": 333 if endpoint else 0}

    try:
        game.start("craft-controls-save")
        cmd("difficulty peaceful"); cmd("gamemode spectator")
        cmd("tp @s -2271.5 200 2275.5"); call("wait-ready", timeout=180)
        cmd("tick freeze"); cmd("forceload add -2288 2256 -2240 2288")
        call("wait", 40)
        cmd("fill -2275 199 2267 -2261 199 2278 minecraft:glass")
        cmd("setblock " + coord(TABLE) + " minecraft:crafting_table")
        cmd(f"setblock {B[0]} 200 {B[2]} minecraft:stone_slab[type=bottom]")
        cmd(f"setblock {B[0]} 200 {B[2]-1} minecraft:stone_slab[type=bottom]")
        cmd("clear @s"); cmd("gamemode survival")
        cmd("give @s oritech:steel_ingot 6"); cmd("give @s oritech:nickel_ingot 2")
        cmd("tp @s -2271.5 200 2274.5")
        for _ in range(2):
            test.craft([" a ", " ba", "a  "], {"a": "oritech:steel_ingot", "b": "oritech:nickel_ingot"}, WRENCH)
        call("select", WRENCH); call("key", "f", "tap"); settle()
        tools(); call("select", WRENCH); settle()
        pair(); aim(); click(); main_off = disabled()
        call("wait", 12); aim(); click()
        assert "east=1" in states()[0] and "west=1" in states()[1]
        test.empty_hand(); assert call("status")["offhand"]["item"] == WRENCH
        aim(); call("wait", 12); click(); offhand_off = disabled()
        call("wait", 12); aim(); click()
        assert "east=1" in states()[0]
        # Check a rapid repeat is suppressed. State inspection and the second
        # input fit inside the eight-tick interval in this pinned local run.
        call("select", WRENCH); aim(); call("wait", 12)
        yaw, pitch = math.degrees(math.atan2(.7, .45)), math.degrees(math.atan2(.62, math.hypot(.7, .45)))
        miss = rapid(["status", "look 0 -90", "mouse right click", f"look {yaw} {pitch}",
                      "mouse right click", "wait 1", "block " + coord(A), "status"])
        assert "east=1" in miss[6]["state"] and 0 < miss[5]["ticks"]-miss[0]["ticks"] < 8, miss
        call("wait", 12)
        empty_slot = next(i+1 for i, slot in enumerate(call("inventory")["hotbar"]) if not slot.get("item"))
        quick = rapid(["status", "mouse right click", "wait 1", "block " + coord(A),
                       f"select {empty_slot}", "mouse right click", "wait 1", "block " + coord(A), "status"])
        assert "east=0" in quick[3]["state"] and quick[3]["state"] == quick[7]["state"], quick
        assert 0 < quick[6]["ticks"] - quick[0]["ticks"] < 8, quick
        tools(); saved = disabled(); saved_inventory = test.counts()
        call("screenshot", game.work/"disabled-pair.png"); call("save")
    finally:
        game.stop()
    try:
        game.start("reopen-shift")
        cmd("tick freeze")
        assert states() == saved and test.counts() == saved_inventory
        tools(); call("select", WRENCH); aim(); call("wait", 12); click()
        assert "east=1" in states()[0] and "west=1" in states()[1]
        cmd("setblock " + coord(B) + " oritech:basic_generator_block")
        cmd("data merge block " + coord(A) + " {energy:333}")
        assert call("block", *A)["block"] == "oritech:energy_pipe_connection"
        endpoint_aim(); call("wait", 12); click()
        assert call("block", *A)["block"] == "oritech:energy_pipe" and "east=0" in states()[0]
        assert "not a block entity" in cmd("data get block " + coord(A)).lower()
        endpoint_aim(); call("wait", 12); click()
        assert call("block", *A)["block"] == "oritech:energy_pipe_connection"
        assert cmd("data get block " + coord(A) + " energy").rstrip().endswith(" 0")
        removals = [shift_remove(creative, endpoint) for endpoint in (False, True) for creative in (False, True)]
        pair(); call("select", WRENCH); aim(); call("wait", 12); click(); final = disabled()
        final_inventory = test.counts(); tools()
        call("screenshot", game.work/"shift-drops-collected.png"); call("save")
    finally:
        game.stop()
    try:
        game.start("final-reopen"); cmd("tick freeze")
        assert states() == final and test.counts() == final_inventory
        tools(); status = call("status"); assert status["server"]["decode_errors"] == 0
    finally:
        game.stop()
    result = {"schema": 1, "content_version": "0.7.0", "native_version": "0.6.0",
              "crafts": test.crafts, "mainhand_disabled": main_off, "offhand_disabled": offhand_off,
              "rapid_repeat_suppressed": True, "miss_consumes_shared_cooldown": True, "cross_hand_repeat_suppressed": True,
              "last_provider_disconnect_discards_333_reconnect_starts_zero": True,
              "timing_observations": observations, "shift_removals": removals,
              "two_physical_reopens_exact": True, "tool_count_unchanged": 2,
              "saved": saved, "final": final, "final_inventory": final_inventory, "decode_errors": 0,
              "exact_cooldown_expiry_or_all_neighbor_callbacks_tested": False,
              "licensed_multiplayer_or_complete_progression": False,
              "screenshots_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in game.work.glob("*.png")}}
    (game.work/"checked-result.json").write_text(json.dumps(result, indent=2)+"\n")
    print("Crafted two wrenches; both hands, rapid repeat, four Shift drops and two physical reopens passed")


if __name__ == "__main__":
    main()

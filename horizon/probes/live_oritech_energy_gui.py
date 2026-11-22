#!/usr/bin/env python3
"""Exercise assembly, real menu packets, connected energy and physical save/reopen.

Blocks are placed as creative test fixtures. Fuel/input enter through mouse/menu
packets; energy, burn progress and output are never injected. No account login.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from graphical_fixture import GraphicalFixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir", "work"): parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    game = GraphicalFixture(args.server_dir, args.work, ("0.1.0", "0.2.0", "0.3.0", "0.4.0"), "techquest-oritech-gui", "TQEnergyGui", module="oritech", frozen=True)
    call, cmd, settle = game.call, game.command, game.settle
    def number(x, key):
        value = cmd(f"data get block {x} 200 0 {key}")
        match = re.search(r"has the following block data:\s*(-?\d+)", value)
        assert match, value
        return int(match[1])
    def state():
        return {"generator_energy": number(0, "energy"), "generator_progress": number(0, '"oritech.machine_progress"'),
                "burn": number(0, "storedBurn"), "furnace_energy": number(1, "energy"),
                "furnace_progress": number(1, '"oritech.machine_progress"'),
                "generator_items": cmd("data get block 0 200 0 Items").split("block data:")[-1].strip(),
                "furnace_items": cmd("data get block 1 200 0 Items").split("block data:")[-1].strip()}
    def screen(count):
        reply = call("screen"); assert reply["screen"] == "container", reply
        slots = {s["slot"]: s for s in reply["slots"]}
        assert {s for s in slots if 300 <= s < 500} == set(range(300, 300+count)), reply
        return reply, slots
    def insert(ident, count, x, slots):
        cmd(f"give @s {ident} {count}"); call("select", 8); settle()
        call("interact", x, 200, 0); settle(); reply, visible = screen(slots)
        source = next(i for i, s in visible.items() if i < 36 and s.get("item") == ident)
        call("click-slot", source); settle()
        # A furnace's result slot must refuse player insertion.
        if slots == 2:
            call("click-slot", 301); settle(); reply, visible = screen(slots)
            assert reply["carried"]["item"] == ident and visible[301].get("item") is None, reply
        call("click-slot", 300); settle(); reply, visible = screen(slots)
        assert visible[300]["item"] == ident and visible[300]["count"] == count, reply
        assert reply.get("carried") is None, reply
        call("screenshot", game.work / ("generator-menu.png" if slots == 1 else "furnace-menu.png"))
        call("close"); settle()
    def step(n): cmd(f"tick step {n}"); call("wait", n+8)
    try:
        game.start("prepare")
        cmd("fill -3 199 -3 5 199 5 minecraft:stone"); cmd("tick freeze")
        cmd("setblock 0 200 0 oritech:basic_generator_block")
        cmd("setblock 1 200 0 oritech:powered_furnace_block")
        cmd("tp @s 1.5 200 2.5"); call("wait-ready", timeout=180); cmd("clear @s"); cmd("gamemode survival")
        call("interact", 1, 200, 0); settle()
        assert call("screen")["screen"] != "container"
        assert number(1, "techquest_assembled") == 0
        cmd("setblock 1 201 0 oritech:machine_core_1")
        call("interact", 1, 200, 0); settle()
        assert number(1, "techquest_assembled") == 1
        assert call("screen")["screen"] != "container", "first assembly click should be consumed"
        insert("minecraft:raw_iron", 2, 1, 2); insert("minecraft:coal", 2, 0, 1)
        step(45); saved = state()
        assert saved["burn"] == 1600 and saved["generator_progress"] == 1555, saved
        assert saved["furnace_progress"] in (44,45), saved
        assert saved["generator_energy"] + saved["furnace_energy"] + 32 * saved["furnace_progress"] == 45 * 32, saved
        call("screenshot", game.work / "working-pair.png"); call("save")
    finally: game.stop()
    try:
        game.start("reopen"); cmd("tick freeze"); reopened = state()
        assert reopened == saved, (saved, reopened)
        step(156); completed = state()
        assert "minecraft:raw_iron" not in completed["furnace_items"] and "minecraft:iron_ingot" in completed["furnace_items"], completed
        assert re.search(r"count:\s*2\b", completed["furnace_items"]), completed
        assert completed["furnace_progress"] == 0, completed
        assert completed["generator_energy"] + completed["furnace_energy"] + 2*3200 == 201*32, completed
        call("interact", 1, 200, 0); settle(); reply, visible = screen(2)
        assert visible[301]["item"] == "minecraft:iron_ingot" and visible[301]["count"] == 2, reply
        call("click-slot", 301, "shift"); settle()
        assert call("inventory")["counts"].get("minecraft:iron_ingot") == 2
        call("close"); settle()
        # Breaking the only core disables subsequent processing.
        cmd("setblock 1 201 0 minecraft:air"); step(1)
        assert number(1, "techquest_assembled") == 0
        status = call("status"); assert status["server"]["joined"] and status["server"]["decode_errors"] == 0
        call("screenshot", game.work / "collected-output.png"); call("save")
    finally: game.stop()
    report = {"schema": 1, "prototype_version": game.version, "connected_local_graphical_client": True,
              "core_required_and_assembled_by_interaction": True, "first_assembly_click_consumed": True,
              "fuel_and_input_inserted_by_menu_packets": True, "output_rejects_player_insertion": True,
              "energy_progress_or_output_injected": False, "save_reopen_exact": True,
              "two_iron_ingots_smelted_and_collected": True, "energy_conserved": True,
              "broken_core_disables_processing": True, "protocol_decode_errors": 0,
              "device_type": status["renderer"]["device_type"], "saved": saved, "completed": completed,
              "licensed_account_or_dedicated_join_tested": False, "full_mod_ported": False, "published": False,
              "screenshots_sha256": {n: hashlib.sha256((game.work/n).read_bytes()).hexdigest() for n in
                                     ("generator-menu.png", "furnace-menu.png", "working-pair.png", "collected-output.png")}}
    (game.work / "checked-result.json").write_text(json.dumps(report, indent=2)+"\n")
    print("Graphical Oritech pair assembled, powered, saved/reopened and produced two collected ingots")


if __name__ == "__main__": main()

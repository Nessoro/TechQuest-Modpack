#!/usr/bin/env python3
"""Craft/place an Assembler/generator/cores, run coils/motors and physically reopen.

Base metals/alloys/coils, two crafters, a blast furnace, wood, stone, coal, bench, pickaxe,
platform, peaceful difficulty, teleports and tick control are explicit fixtures.
Motors, machines, cores and machine energy are never given or injected. The
six initial coil fixtures are fully spent on crafting before processing makes
six new coils. This is a local graphical player, not a licensed join.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import time

from graphical_fixture import GraphicalFixture
from live_oritech_gathered_gui import GatheredChain, TABLE

GEN = (-2269, 200, 2272)
ASSEMBLER = (-2268, 200, 2272)
OFFSETS = {"north": (1, 0), "east": (0, 1), "south": (-1, 0), "west": (0, -1)}


def main():
    global GEN
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir", "work"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    game = GraphicalFixture(args.server_dir, args.work, "0.5.0", "techquest-assembler-gui", "TQAssemblerGui", module="oritech", frozen=True)
    shutil.copytree(game.server / "techquest-horizon-test/datapacks", game.work / "saves" / game.world / "datapacks")
    test = GatheredChain(game)
    cmd, call, settle = game.command, game.call, game.settle

    def number(pos, key):
        reply = cmd("data get block " + " ".join(map(str, pos)) + " " + key)
        match = re.search(r"has the following block data:\s*(-?\d+)", reply)
        assert match, reply
        return int(match[1])

    def state():
        result = {"inventory": test.counts()}
        for name, pos in (("generator", GEN), ("assembler", ASSEMBLER)):
            result[name] = {key: cmd("data get block " + " ".join(map(str, pos)) + " " + key).split("block data:")[-1].strip()
                            for key in ("energy", '"oritech.machine_progress"', "Items")}
        result["assembled"] = number(ASSEMBLER, "techquest_assembled")
        result["core_used"] = [number(pos, "techquest_core_used") for pos in cores]
        return result

    def step(n):
        cmd(f"tick step {n}")
        call("wait", n + 8)

    def open_machine(pos, count):
        approach(pos)
        test.empty_hand()
        call("interact", *pos)
        settle()
        screen, slots = test.slots()
        assert screen["screen"] == "container", screen
        assert {slot for slot in slots if 300 <= slot < 500} == set(range(300, 300 + count)), screen
        return screen, slots

    def approach(pos, core=False):
        ax, az = (-dz, dx) if core else (dx, dz)
        cmd(f"tp @s {pos[0]+.5-ax*2.5} 200 {pos[2]+.5-az*2.5}")

    def collect(pos, slot, item, count):
        before = test.counts().get(item, 0)
        screen, slots = open_machine(pos, 5)
        assert slots[slot].get("item") == item and slots[slot]["count"] == count, screen
        call("click-slot", slot, "shift")
        settle()
        assert test.counts().get(item, 0) == before + count
        call("close")

    def hold(item):
        if not any(slot.get("item") == item for slot in call("inventory")["hotbar"]):
            call("open-inventory")
            settle()
            _, slots = test.slots()
            source = next(i for i, slot in slots.items() if 9 <= i < 36 and slot.get("item") == item)
            call("click-slot", source)
            settle()
            call("click-slot", 8)
            settle()
            if call("screen").get("carried"):
                call("click-slot", source)
                settle()
            call("close")
        call("select", item)
        settle()

    supplied = {"oritech:nickel_ingot": 10, "oritech:steel_ingot": 10, "oritech:magnetic_coil": 6,
                "minecraft:copper_ingot": 5, "oritech:adamant_ingot": 1, "minecraft:crafter": 2,
                "minecraft:blast_furnace": 1, "minecraft:coal": 1, "minecraft:cobblestone": 8,
                "minecraft:oak_planks": 36, "minecraft:diamond_pickaxe": 1}
    try:
        game.start("craft-and-partial-coils")
        cmd("clear @s")
        cmd("difficulty peaceful")
        cmd("gamemode spectator")
        cmd("tp @s -2271.5 200 2275.5")
        call("wait-ready", timeout=180)
        cmd("tick freeze")
        cmd("forceload add -2288 2256 -2256 2288")
        deadline = time.monotonic() + 120
        for pos in ("-2275 199 2267", "-2264 199 2278"):
            while "Test passed" not in cmd("execute if loaded " + pos):
                assert time.monotonic() < deadline, ("platform chunk not loaded", pos)
                call("wait", 20)
        assert "Successfully filled" in cmd("fill -2275 199 2267 -2264 199 2278 minecraft:glass")
        cmd("setblock " + " ".join(map(str, TABLE)) + " minecraft:crafting_table")
        cmd("gamemode survival")
        assert "techquest_terralith" in cmd("datapack list enabled")
        for item, count in supplied.items():
            cmd(f"give @s {item} {count}")
        test.craft(["ccc", "c c", "ccc"], {"c": "minecraft:cobblestone"}, "minecraft:furnace")
        for _ in range(2):
            test.craft([" s ", "wcw", "wcw"], {"s": "oritech:nickel_ingot", "w": "oritech:steel_ingot", "c": "oritech:magnetic_coil"}, "oritech:motor")
        test.craft(["fff", "fcf", "sbs"], {"f": "oritech:nickel_ingot", "c": "minecraft:copper_ingot", "s": "oritech:magnetic_coil", "b": "minecraft:furnace"}, "oritech:basic_generator_block")
        test.craft(["fff", "mcm", "sbs"], {"f": "minecraft:copper_ingot", "m": "minecraft:crafter", "c": "oritech:adamant_ingot", "s": "oritech:motor", "b": "minecraft:blast_furnace"}, "oritech:assembler_block")
        for _ in range(3):
            test.craft(["pp", "pp"], {"p": "minecraft:oak_planks"}, "minecraft:crafting_table", inventory=True)
            test.craft(["sss", "scs", "sss"], {"s": "minecraft:oak_planks", "c": "minecraft:crafting_table"}, "oritech:machine_core_1")
        assert test.counts().get("oritech:magnetic_coil", 0) == test.counts().get("oritech:motor", 0) == 0
        call("save")
        (game.work / "crafted-checkpoint.json").write_text(json.dumps({"crafts": test.crafts, "inventory": test.counts()}, indent=2) + "\n")
        cmd("tp @s -2267.5 200 2269.5")
        call("look-at-block", ASSEMBLER[0], ASSEMBLER[1]-1, ASSEMBLER[2])
        settle()
        test.place("oritech:assembler_block", ASSEMBLER)
        placed = call("block", *ASSEMBLER)
        facing = re.search(r"facing=(north|east|south|west)", placed["state"]).group(1)
        placement_yaw = call("status")["yaw"]
        assert facing == ("north", "east", "south", "west")[math.floor(placement_yaw/90+.5) % 4], (placed, placement_yaw)
        dx, dz = OFFSETS[facing]
        x, y, z = ASSEMBLER
        cores = [(x + dx, y, z + dz), (x, y + 1, z), (x + dx, y + 1, z + dz)]
        GEN = (x-dz, y, z+dx)
        for item, pos in (("oritech:basic_generator_block", GEN),):
            approach(pos)
            test.place(item, pos)
        # Require all three cores; two valid cores must not be marked used.
        for pos in cores[:2]:
            approach(pos, core=True)
            test.place("oritech:machine_core_1", pos)
        approach(ASSEMBLER)
        test.empty_hand()
        call("interact", *ASSEMBLER)
        settle()
        assert number(ASSEMBLER, "techquest_assembled") == 0
        assert [number(pos, "techquest_core_used") for pos in cores[:2]] == [0, 0]
        approach(cores[2], core=True)
        test.place("oritech:machine_core_1", cores[2])
        approach(ASSEMBLER)
        test.empty_hand()
        call("interact", *ASSEMBLER)
        settle()
        assert number(ASSEMBLER, "techquest_assembled") == 1 and call("screen")["screen"] != "container"
        assert [number(pos, "techquest_core_used") for pos in cores] == [1, 1, 1]
        open_machine(GEN, 1)
        test.put("minecraft:coal", 1, 300)
        call("close")
        test.sprint(2000)
        assert sum(number(pos, "energy") for pos in (GEN, ASSEMBLER)) == 51200
        screen, slots = open_machine(ASSEMBLER, 5)
        source = next(i for i, slot in slots.items() if i < 36 and slot.get("item") == "oritech:nickel_ingot")
        call("click-slot", source)
        settle()
        call("click-slot", 304)
        settle()
        screen, slots = test.slots()
        assert screen["carried"]["item"] == "oritech:nickel_ingot" and not slots[304].get("item"), screen
        call("click-slot", source)
        settle()
        test.put("oritech:steel_ingot", 1, 300)
        test.put("oritech:nickel_ingot", 1, 301)
        test.put("oritech:nickel_ingot", 1, 302)
        test.put("minecraft:copper_ingot", 1, 303)
        call("screenshot", game.work / "assembler-four-inputs.png")
        call("close")
        step(13)
        assert number(ASSEMBLER, '"oritech.machine_progress"') == 13
        saved = state()
        call("screenshot", game.work / "assembler-working.png")
        call("save")
    finally:
        game.stop()
    # Keep a stopped, hashed checkpoint before the destructive core test.
    # A failed later control operation can be investigated without recrafting.
    checkpoint = game.work / "partial-coils-checkpoint"
    shutil.copytree(game.work / "saves" / game.world, checkpoint / game.world)
    shutil.copy2(game.work / "actions.json", checkpoint / "actions.json")
    (checkpoint / "checkpoint.json").write_text(json.dumps({
        "schema": 1, "saved": saved, "crafts": test.crafts, "facing": facing, "placement_yaw": placement_yaw,
        "cores": cores, "generator": GEN, "world": game.world,
        "files_sha256": {str(p.relative_to(checkpoint)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in checkpoint.rglob("*") if p.is_file()},
        "hmods_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (game.work / "horizon-mods").glob("*.hmod")},
    }, indent=2) + "\n")
    try:
        game.start("rebuild-and-motors")
        assert state() == saved
        step(1)
        first_tick_progress = number(ASSEMBLER, '"oritech.machine_progress"')
        assert first_tick_progress == 1
        # Mine a real, player-placed core and collect the actual dropped item.
        target = cores[0]
        approach(target, core=True)
        hold("minecraft:diamond_pickaxe")
        call("look-at-block", *target)
        cmd("tick unfreeze")
        broken = call("break", *target, "--timeout", 20, timeout=30)
        cmd("tick freeze")
        assert call("block", *target)["block"] == "minecraft:air", broken
        assert number(ASSEMBLER, "techquest_assembled") == 0
        paused_progress = number(ASSEMBLER, '"oritech.machine_progress"')
        assert [number(pos, "techquest_core_used") for pos in cores[1:]] == [0, 0]
        step(100)
        assert number(ASSEMBLER, '"oritech.machine_progress"') == paused_progress
        for _ in range(4):
            if test.counts().get("oritech:machine_core_1", 0) == 1:
                break
            entities = call("entities", 32, "minecraft:item")["entities"]
            drops = [row for row in entities if row.get("item", {}).get("item") == "oritech:machine_core_1"]
            assert drops, (broken, entities)
            cmd("tp @s " + " ".join(map(str, drops[0]["pos"])))
            step(40)
        assert test.counts().get("oritech:machine_core_1") == 1
        approach(target, core=True)
        test.place("oritech:machine_core_1", target)
        approach(ASSEMBLER)
        test.empty_hand()
        call("interact", *ASSEMBLER)
        settle()
        assert number(ASSEMBLER, "techquest_assembled") == 1
        assert number(ASSEMBLER, '"oritech.machine_progress"') == paused_progress
        step(1)
        resumed_progress = number(ASSEMBLER, '"oritech.machine_progress"')
        assert resumed_progress == (paused_progress + 1) % 48
        step(96)
        collect(ASSEMBLER, 304, "oritech:magnetic_coil", 6)
        open_machine(ASSEMBLER, 5)
        test.put("oritech:nickel_ingot", 1, 303)
        test.put("oritech:steel_ingot", 1, 302)
        test.put("oritech:magnetic_coil", 2, 300)
        call("screenshot", game.work / "assembler-compacted-inputs.png")
        call("close")
        step(48)
        collect(ASSEMBLER, 304, "oritech:motor", 2)
        inventory = test.counts()
        assert inventory == {"minecraft:diamond_pickaxe": 1, "oritech:magnetic_coil": 4, "oritech:motor": 2}, inventory
        assert sum(number(pos, "energy") for pos in (GEN, ASSEMBLER)) == 51200 - (2*48 + 13)*128
        final = state()
        call("screenshot", game.work / "assembler-collected-components.png")
        call("save")
    finally:
        game.stop()
    try:
        game.start("final-reopen")
        assert state() == final
        status = call("status")
        assert status["server"]["joined"] and status["server"]["decode_errors"] == 0
        call("save")
    finally:
        game.stop()
    commands = [row["args"][1] for row in game.rows if row["args"][0] == "command"]
    assert {line.split()[2] for line in commands if line.startswith("give @s ")} == set(supplied)
    assert not any(line.startswith(("data merge", "data modify", "item replace", "loot ")) for line in commands)
    report = {"schema": 1, "oritech_content_version": "0.5.0", "native_machine_version": "0.4.0",
              "crafts": test.crafts, "base_material_and_tool_fixtures": supplied, "placed_facing": facing, "placement_yaw": placement_yaw,
              "placement_faces_opposite_observed_player_yaw": True, "core_positions": cores,
              "two_manual_motors_generator_assembler_three_cores_crafted_and_player_placed": True,
              "missing_core_rejected_without_claiming_others": True, "first_assembly_click_consumed": True,
              "initial_six_coils_consumed_in_crafting_before_processing": True, "machine_energy_inventory_or_progress_not_injected": True,
              "assembler_result_slot_refuses_input": True, "six_coils_and_two_motors_generated_and_collected": True, "four_generated_coils_unused_in_final_inventory": True,
              "real_core_mined_collected_and_reassembled": broken, "progress_while_core_missing": paused_progress,
              "progress_after_warm_reassembly_tick": resumed_progress, "reopen_cold_cache_first_progress": first_tick_progress,
              "energy_conserved_including_13_lost_preload_ticks": True, "saved": saved, "final": final,
              "two_physical_reopens_exact": True, "protocol_decode_errors": 0, "synthetic_local_player": True,
              "unassisted_survival_or_licensed_join_tested": False, "published": False}
    (game.work / "checked-result.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Crafted Assembler: distributed/compacted inputs, coils/motors, mined/rebuilt core, menus and two reopens passed")


if __name__ == "__main__":
    main()

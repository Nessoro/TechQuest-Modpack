#!/usr/bin/env python3
"""Guided material-gathering starter chain in one real Terralith world.

Only an iron pickaxe is given. Teleports, peaceful difficulty, spectator travel,
carved access and a glass work platform are explicit fixtures. All recipe inputs
are mined, smelted and crafted by the survival player through ordinary packets.
This is not a from-spawn, unassisted survival or licensed multiplayer test.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import time

from graphical_fixture import GraphicalFixture
from install_isolated_server import checked_path, tree_files

DEEP = (-2272, -24, 2272)
UPPER = (-2272, 64, 2272)
TABLE = (-2272, 200, 2272)
SMELTER = (-2270, 200, 2272)
GENERATOR = (-2268, 200, 2272)
FURNACE = (-2267, 200, 2272)
CORE = (-2267, 201, 2272)


class GatheredChain:
    def __init__(self, game):
        self.g = game
        self.cmd, self.call, self.settle = game.command, game.call, game.settle
        self.mined, self.crafts, self.smelts = [], [], []

    def counts(self):
        return self.call("inventory")["counts"]

    def slots(self):
        screen = self.call("screen")
        return screen, {slot["slot"]: slot for slot in screen["slots"]}

    def travel(self, center):
        self.cmd("gamemode spectator")
        self.cmd("tp @s " + " ".join(map(str, center)))
        self.call("wait-ready", timeout=180)
        self.call("wait", 20)

    def gather(self, block, item, count, center, *, terralith=False):
        self.travel(center)
        while self.counts().get(item, 0) < count:
            search = self.call("find-block", block, 64)
            assert search["count"] > 0, (block, search)
            candidates = search["nearest"]
            if terralith:
                candidates = [entry for entry in candidates if "Test passed" in self.cmd(
                    "execute if biome " + " ".join(map(str, entry["pos"])) + " #terralith:all_terralith_biomes")]
            assert candidates, ("no eligible natural target", block)
            pos = candidates[0]["pos"]
            x, y, z = pos
            assert self.call("block", *pos)["block"].split("[")[0] == block
            before = self.counts().get(item, 0)
            self.cmd(f"fill {x} {y} {z+1} {x} {y+1} {z+2} minecraft:air")
            # Stabilize the access cells under naturally falling gravel.
            self.cmd(f"fill {x} {y+2} {z+1} {x} {y+2} {z+2} minecraft:glass")
            # Glass cannot supply any ingredient in this starter route.
            self.cmd(f"setblock {x} {y-1} {z+2} minecraft:glass")
            self.cmd(f"tp @s {x+0.5} {y} {z+2.5}")
            self.cmd("gamemode survival")
            self.call("select", "minecraft:iron_pickaxe")
            self.settle()
            self.cmd("tick unfreeze")
            self.call("wait-ready", timeout=180)
            self.call("look-at-block", *pos)
            attempts = []
            for _ in range(3):
                result = self.call("break", *pos, "--timeout", 20, timeout=30)
                attempts.append(result)
                actual = self.call("block", *pos)["block"]
                if actual.split("[")[0] != block and result.get("drops", {}).get(item, 0) > 0:
                    break
                # Redstone lights on the first hit. The control API reports
                # that state change before the survival player has mined it.
                assert actual.split("[")[0] == block, (block, actual, result)
            assert actual.split("[")[0] != block and result.get("drops", {}).get(item, 0) > 0, attempts
            self.cmd(f"tp @s {x+0.5} {y} {z+0.5}")
            self.call("wait", 40)
            # Drops can fall into a cave below the mined block. Follow the
            # real entity rather than replacing it or crediting uncollected loot.
            for _ in range(4):
                if self.counts().get(item, 0) > before:
                    break
                entities = self.call("entities", 128, "minecraft:item")["entities"]
                drops = [entity for entity in entities if entity.get("type") == "minecraft:item"
                         and entity.get("item", {}).get("item") == item]
                assert drops, ("mined item was not collected or visible", item, result)
                self.cmd("tp @s " + " ".join(map(str, drops[0]["pos"])))
                self.call("wait", 40)
            self.cmd("tick freeze")
            after = self.counts().get(item, 0)
            after_state = self.call("block", *pos)["block"]
            assert after_state.split("[")[0] != block
            assert after > before, (block, before, after, result)
            self.mined.append({"block": block, "pos": pos, "item": item,
                               "before": before, "after": after, "break": result, "break_attempts": attempts,
                               "terralith_biome_checked": terralith, "after_state": after_state})
            print("mined", item, after, "/", count, flush=True)

    def empty_hand(self):
        self.call("open-inventory")
        self.settle()
        _, slots = self.slots()
        free = next((i for i in range(9) if not slots[i].get("item")), None)
        if free is None:
            destination = next(i for i in range(9, 36) if not slots[i].get("item"))
            self.call("click-slot", 8)
            self.settle()
            self.call("click-slot", destination)
            self.settle()
            free = 8
        self.call("close")
        self.call("select", free + 1)
        self.settle()

    def place(self, item, pos):
        inventory = self.call("inventory")
        if not any(slot.get("item") == item for slot in inventory["hotbar"]):
            self.call("open-inventory")
            self.settle()
            _, slots = self.slots()
            source = next(i for i, slot in slots.items() if 9 <= i < 36 and slot.get("item") == item)
            self.call("click-slot", source)
            self.settle()
            self.call("click-slot", 8)
            self.settle()
            if self.call("screen").get("carried"):
                self.call("click-slot", source)
                self.settle()
            self.call("close")
        self.call("place", *pos, "--item", item)
        self.settle()
        assert self.call("block", *pos)["block"] == item

    def craft(self, pattern, keys, output, count=1, *, inventory=False):
        before = self.counts()
        if inventory:
            self.call("open-inventory")
        else:
            self.call("interact", *TABLE)
        self.settle()
        screen, visible = self.slots()
        stride = 2 if inventory else 3
        assert {100+i for i in range(stride*stride)} <= set(visible), screen
        required = Counter()
        for y, row in enumerate(pattern):
            for x, symbol in enumerate(row):
                if symbol == " ":
                    continue
                item = keys[symbol]
                required[item] += 1
                _, visible = self.slots()
                source = next(i for i, slot in visible.items() if i < 36 and slot.get("item") == item)
                self.call("click-slot", source)
                self.settle()
                self.call("click-slot", 100 + stride*y + x, "right")
                self.settle()
                screen, _ = self.slots()
                if screen.get("carried"):
                    self.call("click-slot", source)
                    self.settle()
        screen, visible = self.slots()
        assert visible[200].get("item") == output and visible[200]["count"] == count, screen
        self.call("click-slot", 200)
        self.settle()
        screen, visible = self.slots()
        assert screen["carried"]["item"] == output and screen["carried"]["count"] == count, screen
        destination = next(i for i, slot in sorted(visible.items()) if i < 36 and not slot.get("item"))
        self.call("click-slot", destination)
        self.settle()
        screen, visible = self.slots()
        assert not screen.get("carried") and all(not visible[100+i].get("item") for i in range(stride*stride)), screen
        expected = Counter(before)
        expected.subtract(required)
        expected[output] += count
        assert +Counter(self.counts()) == +expected, (output, expected, self.counts())
        self.crafts.append({"output": output, "count": count, "consumed": dict(required), "inventory_grid": inventory})
        self.call("close")
        self.settle()
        print("crafted", output, count, flush=True)

    def put(self, item, count, slot):
        _, visible = self.slots()
        source = next(i for i, entry in visible.items() if i < 36 and entry.get("item") == item and entry["count"] >= count)
        self.call("click-slot", source)
        self.settle()
        for _ in range(count):
            self.call("click-slot", slot, "right")
            self.settle()
        screen, _ = self.slots()
        if screen.get("carried"):
            self.call("click-slot", source)
            self.settle()
        assert not self.call("screen").get("carried")

    def sprint(self, ticks):
        def clock():
            text = self.cmd("time query gametime")
            match = re.search(r"The (?:game )?time is (\d+)", text)
            assert match, text
            return int(match[1])
        before = clock()
        assert "sprinting" in self.cmd(f"tick sprint {ticks}")
        deadline = time.monotonic() + 60
        while clock() < before + ticks:
            assert time.monotonic() < deadline, "tick sprint timed out"
        self.cmd("tick freeze")

    def smelt(self, item, count, output, fuel):
        before = self.counts()
        self.empty_hand()
        self.call("interact", *SMELTER)
        self.settle()
        screen, slots = self.slots()
        # Vanilla furnace container uses input/fuel/output in order.
        assert {300, 301, 302} <= set(slots), screen
        self.put(item, count, 300)
        self.put("minecraft:coal", fuel, 301)
        self.call("close")
        self.sprint(count*200 + 5)
        self.call("interact", *SMELTER)
        self.settle()
        screen, slots = self.slots()
        assert slots[302].get("item") == output and slots[302]["count"] == count, screen
        self.call("click-slot", 302, "shift")
        self.settle()
        self.call("close")
        after = self.counts()
        expected = Counter(before)
        expected[item] -= count
        expected["minecraft:coal"] -= fuel
        expected[output] += count
        assert +Counter(after) == +expected, (item, expected, after)
        self.smelts.append({"input": item, "count": count, "output": output, "coal_inserted": fuel})
        print("smelted", output, count, flush=True)

    def state(self):
        state = {}
        for label, pos, keys in (("generator", GENERATOR, ("energy", '"oritech.machine_progress"', "storedBurn", "Items")),
                                 ("furnace", FURNACE, ("energy", '"oritech.machine_progress"', "Items"))):
            for key in keys:
                text = self.cmd("data get block " + " ".join(map(str, pos)) + " " + key)
                value = text.split("block data:")[-1].strip()
                state[label + ":" + key] = value
        return state

    def prepare_chain(self):
        self.travel((-2271, 200, 2275))
        self.cmd("fill -2275 199 2269 -2265 199 2278 minecraft:glass")
        self.cmd("tp @s -2271.5 200 2275.5")
        self.cmd("gamemode survival")
        for _ in range(4):
            self.craft(["l"], {"l": "minecraft:acacia_log"}, "minecraft:acacia_planks", 4, inventory=True)
        for _ in range(2):
            self.craft(["pp", "pp"], {"p": "minecraft:acacia_planks"}, "minecraft:crafting_table", inventory=True)
        self.place("minecraft:crafting_table", TABLE)
        for _ in range(2):
            self.craft(["ccc", "c c", "ccc"], {"c": "minecraft:cobblestone"}, "minecraft:furnace")
        self.place("minecraft:furnace", SMELTER)
        for item, count, output, fuel in (("oritech:raw_nickel", 11, "oritech:nickel_ingot", 2),
                                         ("oritech:raw_platinum", 2, "oritech:platinum_ingot", 1),
                                         ("minecraft:raw_iron", 6, "minecraft:iron_ingot", 1),
                                         ("minecraft:raw_gold", 2, "minecraft:gold_ingot", 1),
                                         ("minecraft:raw_copper", 4, "minecraft:copper_ingot", 1)):
            self.smelt(item, count, output, fuel)
        self.call("select", "minecraft:iron_pickaxe")
        self.cmd("tick unfreeze")
        self.call("break", *SMELTER, "--timeout", 20, timeout=30)
        self.cmd("tp @s -2269.5 200 2272.5")
        self.call("wait", 40)
        self.cmd("tick freeze")
        assert self.counts().get("minecraft:furnace") == 2, self.counts()
        for _ in range(3):
            self.craft(["aa ", "bb "], {"a": "minecraft:iron_ingot", "b": "minecraft:coal"}, "oritech:steel_ingot")
        self.craft(["aa ", "bb "], {"a": "minecraft:gold_ingot", "b": "minecraft:redstone"}, "oritech:electrum_ingot")
        self.craft(["iii", "ccc", "iii"], {"i": "oritech:nickel_ingot", "c": "oritech:steel_ingot"}, "oritech:magnetic_coil", 4)
        self.craft(["fff", "fcf", "sbs"], {"f": "oritech:nickel_ingot", "c": "minecraft:copper_ingot", "s": "oritech:magnetic_coil", "b": "minecraft:furnace"}, "oritech:basic_generator_block")
        self.craft(["fff", "mcm", "sbs"], {"f": "minecraft:copper_ingot", "m": "oritech:platinum_ingot", "c": "oritech:electrum_ingot", "s": "oritech:magnetic_coil", "b": "minecraft:furnace"}, "oritech:powered_furnace_block")
        self.craft(["sss", "scs", "sss"], {"s": "minecraft:acacia_planks", "c": "minecraft:crafting_table"}, "oritech:machine_core_1")
        # Face the row from the front so the first placed machine cannot
        # obscure the floor/face needed to place the second one.
        self.cmd("tp @s -2267.5 200 2275.5")
        for item, pos in (("oritech:basic_generator_block", GENERATOR), ("oritech:powered_furnace_block", FURNACE), ("oritech:machine_core_1", CORE)):
            self.place(item, pos)
        self.empty_hand()
        self.call("interact", *FURNACE)
        self.settle()
        assert "1b" in self.cmd("data get block " + " ".join(map(str, FURNACE)) + " techquest_assembled")
        for item, count, pos in (("minecraft:raw_iron", 2, FURNACE), ("minecraft:coal", 2, GENERATOR)):
            self.empty_hand()
            self.call("interact", *pos)
            self.settle()
            self.put(item, count, 300)
            self.call("close")
        self.cmd("tick step 45")
        self.call("wait", 53)
        self.call("screenshot", self.g.work / "gathered-active-pair.png")


def audit_commands(rows):
    commands = [row["args"][1] for row in rows if row["args"][0] == "command"]
    assert [line for line in commands if line.startswith("give ")] == ["give @s minecraft:iron_pickaxe 1"]
    assert not any(line.startswith(("data merge", "data modify", "item replace", "loot ")) for line in commands)
    for line in commands:
        if line.startswith(("setblock ", "fill ")):
            assert line.split()[-1] in ("minecraft:air", "minecraft:glass"), line


def resume_gather(game, test, source):
    """Continue only a previous gather phase, preserving its world and evidence."""
    source = checked_path(source)
    assert source not in game.work.parents and game.work not in source.parents
    rows = json.loads((source / "actions.json").read_text())
    assert rows and all(row["phase"] == "gather" for row in rows), "only a raw gathering save may be resumed"
    audit_commands(rows)
    for name, path in tree_files(game.server / "horizon-mods").items():
        assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(checked_path(source / "horizon-mods" / name).read_bytes()).digest()
    world = source / "saves" / game.world
    tree_files(world)  # Refuse symlinks before copying any saved world data.
    shutil.copytree(world, game.work / "saves" / game.world)
    game.rows.extend(rows)
    counts, pending, tagged = {}, None, set()
    for row in rows:
        args, reply = row["args"], row["reply"]
        if args[0] == "command" and args[1].startswith("execute if biome ") and "#terralith:all_terralith_biomes" in args[1] and "Test passed" in " ".join(reply.get("chat", [])):
            tagged.add(tuple(map(int, args[1].split()[3:6])))
        if args[0] == "break" and reply.get("ok") and reply.get("drops"):
            item = next(iter(reply["drops"]))
            pending = {"block": reply["block_before"], "pos": reply["pos"], "item": item,
                       "before": counts.get(item, 0), "break": reply,
                       "terralith_biome_checked": tuple(reply["pos"]) in tagged}
        if args == ["inventory"]:
            counts = reply["counts"]
            if pending:
                test.mined.append({**pending, "after": counts.get(pending["item"], 0)})
                pending = None
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("server-dir", "work"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--resume-from", type=Path, help="own previous gather-only work directory; retain its action provenance")
    args = parser.parse_args()
    game = GraphicalFixture(args.server_dir, args.work, "0.2.0", "techquest-gathered-chain", "TQGathered", module="oritech", frozen=True)
    test = GatheredChain(game)
    if args.resume_from:
        resumed_counts = resume_gather(game, test, args.resume_from)
    else:
        shutil.copytree(game.server / "techquest-horizon-test/datapacks", game.work / "saves" / game.world / "datapacks")
    cmd, call = game.command, game.call
    try:
        game.start("gather")
        if args.resume_from:
            assert test.counts() == resumed_counts
        else:
            cmd("clear @s")
            cmd("give @s minecraft:iron_pickaxe 1")
        cmd("difficulty peaceful")
        assert "techquest_terralith" in cmd("datapack list enabled")
        for block, item, count, center, terra in (
            ("oritech:deepslate_nickel_ore", "oritech:raw_nickel", 11, DEEP, True),
            ("oritech:deepslate_platinum_ore", "oritech:raw_platinum", 2, DEEP, True),
            ("minecraft:deepslate_iron_ore", "minecraft:raw_iron", 8, DEEP, False),
            ("minecraft:deepslate_gold_ore", "minecraft:raw_gold", 2, DEEP, False),
            ("minecraft:deepslate_redstone_ore", "minecraft:redstone", 2, DEEP, False),
            ("minecraft:copper_ore", "minecraft:raw_copper", 4, UPPER, False),
            ("minecraft:coal_ore", "minecraft:coal", 16, UPPER, False),
            ("minecraft:stone", "minecraft:cobblestone", 16, UPPER, False),
            ("minecraft:acacia_log", "minecraft:acacia_log", 4, UPPER, False)):
            test.gather(block, item, count, center, terralith=terra)
        raw_counts = test.counts()
        call("save")
    finally:
        game.stop()
    # Keep a stopped raw-material checkpoint for diagnosing later crafting/menu
    # failures without repeating mining or discarding its recorded provenance.
    checkpoint = game.work / "raw-checkpoint"
    shutil.copytree(game.work / "saves" / game.world, checkpoint / "saves" / game.world)
    shutil.copytree(game.work / "horizon-mods", checkpoint / "horizon-mods")
    shutil.copyfile(game.work / "actions.json", checkpoint / "actions.json")
    try:
        game.start("craft")
        assert test.counts() == raw_counts
        test.prepare_chain()
        saved_counts, saved_state = test.counts(), test.state()
        assert saved_state['furnace:"oritech.machine_progress"'] in ("44", "45"), saved_state
        call("save")
    finally:
        game.stop()
    try:
        game.start("complete")
        assert test.counts() == saved_counts
        assert test.state() == saved_state
        cmd("tick step 156")
        call("wait", 164)
        test.empty_hand()
        call("interact", *FURNACE)
        game.settle()
        screen, visible = test.slots()
        assert visible[301].get("item") == "minecraft:iron_ingot" and visible[301]["count"] == 2, screen
        call("click-slot", 301, "shift")
        game.settle()
        call("close")
        assert test.counts().get("minecraft:iron_ingot") == 2
        final_counts, final_state = test.counts(), test.state()
        call("screenshot", game.work / "gathered-chain-output.png")
        call("save")
    finally:
        game.stop()
    try:
        game.start("final-reopen")
        assert test.counts() == final_counts
        assert test.state() == final_state
        for record in (test.mined[0], next(row for row in test.mined if row["item"] == "oritech:raw_platinum")):
            test.travel(record["pos"])
            assert call("block", *record["pos"])["block"] == "minecraft:air"
        status = call("status")
        assert status["server"]["joined"] and status["server"]["decode_errors"] == 0
        call("save")
    finally:
        game.stop()
    audit_commands(game.rows)
    report = {"schema": 1, "content_version": "0.2.0", "same_world_for_all_phases": True,
              "terralith_world_datapack_enabled": True, "mined": test.mined, "crafts": test.crafts, "smelts": test.smelts,
              "all_recipe_inputs_mined_by_survival_player": True, "only_given_item": "minecraft:iron_pickaxe",
              "recipe_inputs_consumed_exactly": True, "raw_inventory_survives_reopen": True,
              "active_pair_survives_exact_reopen": True, "final_items_and_pair_survive_exact_reopen": True,
              "crafted_pair_produced_two_collected_iron_ingots": True, "final_inventory": final_counts,
              "ore_features_raw_materials_ingots_machines_energy_or_outputs_injected": False,
              "fixtures": ["iron pickaxe", "teleports", "spectator travel", "carved access", "glass access floors and work platform", "peaceful difficulty", "tick control"],
              "unassisted_survival_from_spawn_tested": False, "licensed_dedicated_join_tested": False,
              "resumed_gather_save": str(args.resume_from.resolve()) if args.resume_from else None,
              "full_modpack_ported": False, "published": False}
    (game.work / "checked-result.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Gathered, smelted, crafted and operated Oritech starter chain in one world; three physical reopens passed")


if __name__ == "__main__":
    main()

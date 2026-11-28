#!/usr/bin/env python3
"""Original waterlogging outcomes through local graphical player packets.

Platform, travel, blocks, buckets/tools and scalar endpoint energy are fixtures.
Compares block states and inventory outcomes, not Java interaction-result enums.
No account, unassisted progression or multiplayer claim.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from graphical_fixture import GraphicalFixture

POS = (129, 200, 176)
NEXT = (130, 200, 176)
WIRE = "oritech:energy_pipe"
TOOL = "oritech:wrench"
coord = lambda p: " ".join(map(str, p))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("server-dir", "work", "original"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    original = json.loads(args.original.read_text())
    assert original["original_waterlogging_callbacks_executed"] and original["flow_chunks_forced"]
    game = GraphicalFixture(args.server_dir, args.work, ("0.8.0", "0.9.0"), "waterlogging-gui", "TQWaterGui", module="oritech", frozen=True)
    cmd, call, settle = game.command, game.call, game.settle
    checked = []

    def node(pos=POS):
        value = call("block", *pos)
        properties = dict(v.split("=", 1) for v in value["state"].split("[", 1)[-1].rstrip("]").split(",")) if "[" in value["state"] else {}
        result = {"block": value["block"], "properties": properties}
        if value["block"] == "oritech:energy_pipe_connection":
            raw = cmd("data get block " + coord(pos) + " energy")
            result["energy"] = int(re.search(r"block data:\s*(-?\d+)", raw)[1])
        return result

    def compare(want):
        actual = node()
        expected = {k: want[k] for k in actual}
        assert actual == expected, (actual, expected)
        return actual

    def reset(endpoint=False, wet=False):
        cmd("fill 128 200 175 131 201 177 minecraft:air")
        cmd("kill @e[type=minecraft:item]")
        cmd("clear @s")
        if endpoint:
            cmd("setblock " + coord(NEXT) + " oritech:basic_generator_block")
        cmd("setblock " + coord(POS) + f" {WIRE}[waterlogged={str(wet).lower()}]")
        if endpoint:
            cmd("data merge block " + coord(POS) + " {energy:333}")
        cmd("tp @s 129.5 200 173.5")

    def hold(item, hand="MAIN_HAND"):
        cmd("give @s " + item)
        call("select", item)
        if hand == "OFF_HAND":
            call("key", "f", "tap"); settle()

    def click():
        call("look-at-block", *POS); settle()
        call("mouse", "right", "click"); settle()

    try:
        game.start("bucket-place-remove-save")
        cmd("difficulty peaceful"); cmd("gamemode spectator")
        cmd("tp @s 129.5 200 173.5"); call("wait-ready", timeout=180)
        cmd("tick freeze"); cmd("forceload add 112 160 144 192"); call("wait", 40)
        cmd("fill 126 199 172 134 199 180 minecraft:glass")
        cmd("gamemode survival")
        placements = [r for r in original["placements"] if r["liquid_level"] in (-1, 0, 1, 8)]
        for row in placements:
            reset(row["endpoint"])
            cmd("setblock " + coord(POS) + " minecraft:air")
            if row["liquid_level"] >= 0:
                cmd("setblock " + coord(POS) + f" minecraft:water[level={row['liquid_level']}]")
            hold(WIRE)
            call("look-at-block", POS[0], POS[1]-1, POS[2]); settle()
            call("place", *POS, "--item", WIRE); settle()
            # Placement starts with an empty endpoint, unlike the independent
            # bucket callback fixture which deliberately holds 333 E.
            wanted = dict(row["after"])
            actual = compare(wanted)
            assert call("inventory")["counts"].get(WIRE, 0) == 0
            checked.append({"kind": "placement", "endpoint": row["endpoint"], "level": row["liquid_level"], "state": actual})
        for row in original["bucket_uses"]:
            reset(row["endpoint"], row["action"] == "drain_wet")
            cmd("gamemode " + ("creative" if row["creative"] else "survival"))
            hold("minecraft:water_bucket" if row["action"] == "fill_dry" else "minecraft:bucket", row["hand"])
            click()
            actual = compare(row["after"])
            counts = Counter()
            for entry in row["inventory"]:
                counts[entry["item"]] += entry["count"]
            assert call("inventory")["counts"] == dict(counts), (row, call("inventory"))
            checked.append({"kind": "bucket", "endpoint": row["endpoint"], "creative": row["creative"], "hand": row["hand"], "action": row["action"], "state": actual, "inventory": dict(counts)})
        for row in original["shift_removals"]:
            if not row["wet"]:
                continue
            reset(row["endpoint"], True)
            cmd("gamemode " + ("creative" if row["creative"] else "survival"))
            hold(TOOL)
            call("key", "shift", "down"); settle(); click()
            call("key", "shift", "up"); settle()
            actual = compare(row["after"])
            drops = [e["item"] for e in call("entities", 12, "minecraft:item")["entities"] if e.get("item", {}).get("item") == WIRE]
            assert sum(d["count"] for d in drops) == 1, drops
            assert call("inventory")["counts"].get(TOOL) == 1
            checked.append({"kind": "shift", "endpoint": row["endpoint"], "creative": row["creative"], "state": actual, "drops": drops})
        # Wet endpoint -> normal -> endpoint, observing live native lifecycle.
        reset(True, True)
        compare(original["wet_lifecycle"]["before"])
        cmd("setblock " + coord(NEXT) + " minecraft:air")
        compare(original["wet_lifecycle"]["removed_provider"])
        cmd("setblock " + coord(NEXT) + " oritech:basic_generator_block")
        compare(original["wet_lifecycle"]["replaced_provider"])
        call("screenshot", game.work/"wet-endpoint.png")
        saved = node(); inventory = call("inventory")["counts"]
        call("save")
    finally:
        game.stop()
    try:
        game.start("physical-reopen")
        cmd("tick freeze")
        assert node() == saved and call("inventory")["counts"] == inventory
        # Drain the restored real source with the original tool, preserving
        # its zero buffer after the provider replacement.
        cmd("clear @s"); cmd("gamemode survival"); hold("minecraft:bucket"); click()
        assert node()["properties"]["waterlogged"] == "false"
        assert call("inventory")["counts"] == {"minecraft:water_bucket": 1}
        assert call("status")["server"]["decode_errors"] == 0
        call("screenshot", game.work/"restored-source-drained.png")
    finally:
        game.stop()
    result = {"schema": 1, "content_version": game.version, "native_version": "0.7.0" if game.version=="0.9.0" else "0.6.0", "placement_cases": len(placements),
              "bucket_cases": len(original["bucket_uses"]), "wet_shift_cases": 4, "checks": checked,
              "wet_lifecycle_matched": True, "wet_endpoint_physical_reopen_exact": True, "restored_source_drained_by_bucket": True,
              "endpoint_fixture_energy_seeded": 333, "protocol_decode_errors": 0, "licensed_multiplayer_tested": False,
              "screenshots_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in game.work.glob("*.png")}}
    (game.work/"checked-result.json").write_text(json.dumps(result, indent=2)+"\n")
    print("Graphical waterlogging: eight placements, 24 bucket uses, four wet Shift removals, lifecycle and physical reopen passed")


if __name__ == "__main__":
    main()

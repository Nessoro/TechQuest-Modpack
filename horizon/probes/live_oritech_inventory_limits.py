#!/usr/bin/env python3
"""Compare actual Horizon inventory additions with original runtime observations.

Give commands, selected/offhand/full inventories and component overrides are
fixtures. Checks slot counts and limits, then physical own player-data reopen.
Does not claim tank gameplay, real accounts, dropped-overflow or multiplayer.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
from install_isolated_server import fresh_environment, verify


def text(row):
    return "\n".join("".join(part[0] for part in message) for message in row.get("messages", []))


def inventory(row, offhand=False):
    value = text(row)
    if "Found no elements matching" in value:
        return []
    assert "has the following entity data:" in value, value
    out = []
    for match in re.finditer(r"\{(?:[^{}]|\{[^{}]*\})*\}", value.split("entity data:", 1)[1]):
        entry = match.group()
        slot = 40 if offhand else int(re.search(r"\bSlot:\s*(-?\d+)b", entry)[1])
        ident = re.search(r'\bid:\s*"([^"]+)"', entry)[1]
        maximum = re.search(r'"minecraft:max_stack_size":\s*(\d+)', entry)
        out.append({"slot": 40 if slot == -106 else slot, "item": ident,
                    "count": int(re.search(r"\bcount:\s*(\d+)", entry)[1]),
                    "maximum": int(maximum[1]) if maximum else 16 if ident == "minecraft:ender_pearl" else 64})
    return sorted(out, key=lambda v: v["slot"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("server-dir", "work", "original"):
        parser.add_argument("--"+key, type=Path, required=True)
    args = parser.parse_args(); server = args.server_dir.resolve(); work = args.work.absolute()
    lock = verify(server)
    assert lock["modules"]["oritech"]["version"] == "0.10.0"
    assert not work.exists() and not work.is_symlink() and not any(p.is_symlink() for p in work.parents)
    assert server not in work.parents and work not in server.parents
    source = json.loads(args.original.read_text()); assert source["original_inventory_add_executed"]
    rows = source["rows"]; assert len(rows) == 192
    work.mkdir(mode=0o700); shutil.copytree(server/"horizon-mods", work/"horizon-mods")
    shutil.copy2(server/"horizon-mods.txt", work/"horizon-mods.txt"); (work/"eula.txt").write_text("eula=true\n")
    config = tomllib.loads((server/"server.toml").read_text())

    def run(phase, lines):
        script, output = work/(phase+"-operations.jsonl"), work/(phase+"-result.jsonl")
        script.write_text("".join(json.dumps({"op": "cmd", "cmd": line})+"\n" for line in lines))
        env = fresh_environment(work/("homes-"+phase))
        env.update(HORIZON_STILL="1", HORIZON_PLAYER_NAME="TQMaxNative", HORIZON_COMMAND_SCRIPT=str(script), HORIZON_COMMAND_OUTPUT=str(output))
        with (work/(phase+"-console.log")).open("x") as log:
            subprocess.run([config["engine"]["path"], "--resources", config["engine"]["resources"], "--game-dir", str(work),
                            "--world", "component-limits", "--seed", "263", "--radius", "2"], cwd=work, env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
        grouped = {}; current = None
        for line in output.read_text().splitlines():
            row = json.loads(line)
            if row["cmd"].startswith("#menu_state "):
                current = row["cmd"].split()[-1]; grouped[current] = []
            elif current:
                grouped[current].append(row)
        return grouped

    lines = ["tick freeze", "gamemode survival"]
    for row in rows:
        ident = row["item"]+(f'[minecraft:max_stack_size={row["limit_override"]}]' if row["limit_override"] else "")
        lines += ["#menu_state "+row["name"], "clear @s", "kill @e[type=minecraft:item]"]
        if row["mode"] in (1, 2):
            lines.append("item replace entity @s hotbar.0 with "+ident+" 1")
        if row["mode"] == 2:
            lines.append("item replace entity @s weapon.offhand with "+ident+" 1")
        if row["mode"] == 3:
            for i in range(36):
                slot = f"hotbar.{i}" if i < 9 else f"inventory.{i-9}"
                lines.append("item replace entity @s "+slot+" with minecraft:barrier 64")
        lines += ["data get entity @s Inventory", "data get entity @s equipment.offhand", "give @s "+ident+" "+str(row["count"]), "data get entity @s Inventory", "data get entity @s equipment.offhand"]
    lines += ["#menu_state saved", "clear @s", "kill @e[type=minecraft:item]",
              "give @s minecraft:stone[minecraft:max_stack_size=1] 2",
              "give @s minecraft:ender_pearl[minecraft:max_stack_size=99] 100", "data get entity @s Inventory", "data get entity @s equipment.offhand", "save-all flush"]
    groups = run("initial", lines); mismatches = []
    for row in rows:
        reads = [v for v in groups[row["name"]] if v["cmd"].startswith("data get entity @s ")]
        assert len(reads) == 4
        observations = [inventory(reads[i])+inventory(reads[i+1], True) for i in (0, 2)]
        assert observations[0] == row["initial"], (row["name"], observations[0], row["initial"])
        if observations[1] != row["after"]:
            mismatches.append({"case": row["name"], "expected": row["after"], "actual": observations[1]})
    (work/"matrix-result.json").write_text(json.dumps({"cases": len(rows), "mismatches": mismatches}, indent=2)+"\n")
    assert not mismatches, mismatches[:3]
    saved = next(inventory(v) for v in groups["saved"] if v["cmd"] == "data get entity @s Inventory")
    assert [v["count"] for v in saved] == [1, 1, 99, 1], saved
    reopened = run("reopen", ["tick freeze", "#menu_state reopened", "data get entity @s Inventory", "data get entity @s equipment.offhand"])
    restored = next(inventory(v) for v in reopened["reopened"] if v["cmd"] == "data get entity @s Inventory")
    assert restored == saved, (saved, restored)
    report = {"schema": 1, "content_version": "0.10.0", "native_version": "0.8.0", "matched_cases": len(rows), "mismatches": [],
              "actual_inventory_command_path_executed": True, "selected_offhand_full_inventory_controls": True,
              "observer_reads_26_3_equipment_offhand_separately_from_inventory": True,
              "physical_player_inventory_reopen_exact": True, "saved": saved,
              "item_and_world_fixtures": True, "dropped_overflow_compared": False,
              "fluid_tank_gameplay_or_multiplayer_tested": False, "published": False}
    (work/"checked-result.json").write_text(json.dumps(report, indent=2)+"\n")
    print("Inventory component limits matched", len(rows), "original cases and physical player-data reopen")


if __name__ == "__main__":
    main()

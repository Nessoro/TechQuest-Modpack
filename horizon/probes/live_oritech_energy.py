#!/usr/bin/env python3
"""Compare real Horizon ticks against the pinned original Oritech machine oracle.

Individual cases use explicit energy/progress/assembled-state fixtures; normal
GUI assembly and connected transport require the separate graphical probe.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from install_isolated_server import fresh_environment, verify


def operations(rows):
    ops = []
    def cmd(line): ops.append({"op": "cmd", "cmd": line})
    def item(ident, count, slot): return f'{{Slot:{slot}b,id:"{ident}",count:{count}}}'
    cmd("gamemode creative"); cmd("tick freeze")
    cmd("fill 124 199 172 136 199 180 minecraft:stone")
    cmd("tp @s 128.5 200 178.5"); ops.append({"op": "settle"})
    # Native container/energy tables are initialized on the first world tick.
    cmd("setblock 129 200 176 oritech:basic_generator_block")
    cmd("tick step 1"); ops.append({"op": "tick", "n": 3})
    for row in rows:
        cmd("fill 128 200 176 130 201 176 minecraft:air"); cmd("kill @e[type=minecraft:item]")
        generator = row["kind"] == "generator"
        ident = "basic_generator_block" if generator else "powered_furnace_block"
        # setItem on the original clamps oversized buckets; seed the observed
        # pre-tick inventory, not the requested constructor count.
        contents = [item(i["item"], i["count"], i["slot"]) for i in row["initial_state"]["items"]]
        if not generator:
            if row["core"]:
                cmd('setblock 129 201 176 oritech:machine_core_1{techquest_core_used:1b,controller_x:0,controller_y:-1,controller_z:0}')
        nbt = f'energy:{row["initial_energy"]},"oritech.machine_progress":{row["initial_progress"]},"oritech.redstone":{int(row["disabled"])}b'
        nbt += f',storedBurn:{row["initial_progress"] if generator else 0},techquest_assembled:{int(not generator and row["core"])}b,Items:[' + ",".join(contents) + "]"
        cmd(f"setblock 129 200 176 oritech:{ident}" + "{" + nbt + "}")
        ops.append({"op": "menu_state", "label": row["name"]})
        cmd("time query gametime")
        elapsed = 0
        for state in row["states"]:
            delta = state["ticks"] - elapsed
            cmd(f"tick step {delta}"); ops.append({"op": "tick", "n": delta + 2})
            cmd("time query gametime")
            for key in ('energy', '"oritech.machine_progress"', 'Items', 'storedBurn' if generator else 'techquest_assembled'):
                cmd("data get block 129 200 176 " + key)
            elapsed = state["ticks"]
    return ops


def text(record):
    return "".join(span[0] for message in record["messages"] for span in message)


def items(record):
    value = text(record)
    if not record["results"][-1][0]:
        # Horizon omits an empty ModBlockEntity Items list when serializing.
        assert "Found no elements matching Items" in value, value
        return []
    assert "has the following block data:" in value, value
    result = []
    for entry in re.findall(r"\{([^{}]+)\}", value):
        result.append({"slot": int(re.search(r"\bSlot:\s*(\d+)b", entry)[1]),
                       "count": int(re.search(r"\bcount:\s*(\d+)", entry)[1]),
                       "item": re.search(r'\bid:\s*"([^"]+)"', entry)[1]})
    return sorted(result, key=lambda i: i["slot"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("server-dir", "work", "original"): parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args(); server = args.server_dir.resolve(); work = args.work.absolute(); lock = verify(server)
    if lock["modules"].get("oritech", {}).get("version") not in ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0"): raise ValueError("requires reviewed Oritech energy installation")
    if work.exists() or work.is_symlink() or any(p.is_symlink() for p in work.parents) or server in work.parents or work in server.parents:
        raise ValueError("work must be new and separate")
    original = json.loads(args.original.read_text()); rows = original["rows"]
    assert original["original_server_tick_executed"] and len(rows) == 63
    work.mkdir(mode=0o700, parents=True); shutil.copytree(server / "horizon-mods", work / "horizon-mods")
    shutil.copy2(server / "horizon-mods.txt", work / "horizon-mods.txt"); (work / "eula.txt").write_text("eula=true\n")
    script = work / "operations.jsonl"; script.write_text("".join(json.dumps(op) + "\n" for op in operations(rows)))
    config = tomllib.loads((server / "server.toml").read_text()); env = fresh_environment(work / "homes")
    env.update(HORIZON_PLAYER_NAME="TQEnergy", HORIZON_COMMAND_SCRIPT=str(script), HORIZON_COMMAND_OUTPUT=str(work / "result.jsonl"))
    with (work / "console.log").open("x") as log:
        (work / "console.log").chmod(0o600)
        subprocess.run([config["engine"]["path"], "--resources", config["engine"]["resources"], "--game-dir", str(work),
                        "--world", "techquest-oritech-energy", "--seed", "263", "--radius", "2"], cwd=work, env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    output = [json.loads(line) for line in (work / "result.jsonl").read_text().splitlines()]
    grouped = {}; current = None
    for record in output:
        if record["cmd"].startswith("#menu_state case_"): current = record["cmd"].split()[-1]; grouped[current] = []
        elif current: grouped[current].append(record)
    mismatches = []; checked = 0
    for row in rows:
        records = grouped[row["name"]]
        clocks = [r["results"][-1][1] for r in records if r["cmd"] == "time query gametime"]
        assert [n - clocks[0] for n in clocks[1:]] == [s["ticks"] for s in row["states"]], (row["name"], clocks)
        data = [r for r in records if r["cmd"].startswith("data get block 129 200 176 ")]
        assert len(data) == 4 * len(row["states"])
        for i, state in enumerate(row["states"]):
            energy, progress, inventory, extra = data[4 * i:4 * i + 4]
            for r in (energy, progress, extra): assert r["results"][-1][0], r
            actual = {"energy": energy["results"][-1][1], "progress": progress["results"][-1][1], "items": items(inventory)}
            if row["kind"] == "generator": actual["stored_burn"] = extra["results"][-1][1]
            else: actual["assembled"] = bool(extra["results"][-1][1])
            if actual != state["state"]: mismatches.append({"name": row["name"], "ticks": state["ticks"], "expected": state["state"], "actual": actual})
            checked += 1
    report = {"schema": 1, "prototype_version": lock["modules"]["oritech"]["version"], "cases": len(rows), "states": checked, "mismatches": mismatches,
              "actual_game_ticks_executed": True, "synthetic_initial_assembled_state": True,
              "synthetic_local_owner": True, "real_client_join_tested": False, "full_mod_ported": False, "published": False}
    (work / "checked-result.json").write_text(json.dumps(report, indent=2) + "\n")
    assert not mismatches, mismatches[:3]
    print("Native Oritech ticks matched", checked, "original states in", len(rows), "cases")


if __name__ == "__main__": main()

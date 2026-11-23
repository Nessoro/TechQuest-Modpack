#!/usr/bin/env python3
"""Open a hashed own 0.7 powered-cable GUI save under the 0.8 waterlogged binding.

Copies the save; never opens the source in place. No items, machine energy,
progress or block state is injected. Checks selected scalar fields and item
IDs/counts, not arbitrary components, Java saves or a general world converter.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

from live_oritech_energy import text
from install_isolated_server import checked_path, fresh_environment, tree_files, verify
from live_oritech_energy_pipes_gui import GEN, FURNACE, CORE, WIRES, coord

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("server-dir", "source-work", "work"):
        parser.add_argument("--"+key, type=Path, required=True)
    args = parser.parse_args()
    server, source, work = checked_path(args.server_dir), checked_path(args.source_work), args.work.absolute()
    lock = verify(server); assert lock["modules"]["oritech"]["version"] == "0.8.0"
    assert not work.exists() and not work.is_symlink() and not any(p.is_symlink() for p in work.parents)
    assert source not in work.parents and work not in source.parents and server not in work.parents
    proof = json.loads((Path(__file__).resolve().parents[1]/"ORITECH_WRENCH_RESULT.json").read_text())
    report = source/"checked-result.json"
    assert sha(report) == proof["proof_files_sha256"][source.name+"/checked-result.json"]
    old = json.loads(report.read_text())
    assert old["oritech_content_version"] == "0.7.0" and old["two_physical_reopens_exact"]
    previous_lock = verify(source.parent/proof["installation"]["profile"])
    for ident, spec in previous_lock["modules"].items():
        assert sha(source/"horizon-mods"/(ident+".hmod")) == spec["sha256"]
    original_world = source/"saves/techquest-cables-gui"
    before_hashes = {name: sha(p) for name, p in tree_files(original_world).items()}
    work.mkdir(mode=0o700)
    shutil.copytree(original_world, work/"saves/cable-save-upgrade")
    shutil.copytree(server/"horizon-mods", work/"horizon-mods")
    shutil.copy2(server/"horizon-mods.txt", work/"horizon-mods.txt")
    (work/"eula.txt").write_text("eula=true\n")
    config = tomllib.loads((server/"server.toml").read_text())
    final = old["final"]
    expected = {(GEN, "energy"): final["generator_energy"], (GEN, '"oritech.machine_progress"'): final["generator_progress"],
                (GEN, "storedBurn"): final["burn"], (FURNACE, "energy"): final["furnace_energy"],
                (FURNACE, '"oritech.machine_progress"'): final["furnace_progress"],
                (FURNACE, "techquest_assembled"): final["assembled"], (CORE, "techquest_core_used"): final["core_used"],
                (WIRES[0], "energy"): final["source_buffer"], (WIRES[-1], "energy"): final["far_buffer"]}

    def run(phase):
        lines = ["tick freeze", "tp @s -2265.5 200 2275", "forceload add -2288 2256 -2240 2288"]
        ops = [{"op": "cmd", "cmd": line} for line in lines]+[{"op": "settle"}]
        for pos, key in expected:
            ops.append({"op": "cmd", "cmd": "data get block "+coord(pos)+" "+key})
        for pos, state in zip(WIRES, final["wires"]):
            ops.append({"op": "cmd", "cmd": "execute if block "+coord(pos)+" "+state})
        for pos in (GEN, FURNACE):
            ops.append({"op": "cmd", "cmd": "data get block "+coord(pos)+" Items"})
        ops += [{"op": "cmd", "cmd": "data get entity @s Inventory"}, {"op": "cmd", "cmd": "save-all flush"}]
        script, output = work/(phase+"-operations.jsonl"), work/(phase+"-result.jsonl")
        script.write_text("".join(json.dumps(v)+"\n" for v in ops))
        env = fresh_environment(work/("homes-"+phase))
        env.update(HORIZON_STILL="1", HORIZON_PLAYER_NAME="TQCableGui", HORIZON_COMMAND_SCRIPT=str(script), HORIZON_COMMAND_OUTPUT=str(output))
        with (work/(phase+"-console.log")).open("x") as log:
            subprocess.run([config["engine"]["path"], "--resources", config["engine"]["resources"], "--game-dir", str(work),
                            "--world", "cable-save-upgrade", "--seed", "263", "--radius", "2"], cwd=work, env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        by_cmd = {v["cmd"]: v for v in rows}
        for (pos, key), value in expected.items():
            row = by_cmd["data get block "+coord(pos)+" "+key]
            assert row["results"][-1] == [True, value], (phase, pos, key, row, value)
        for row in rows:
            if row["cmd"].startswith("execute if block "):
                assert row["results"][-1][0], row
        for pos in (GEN, FURNACE):
            assert "Found no elements matching Items" in text(by_cmd["data get block "+coord(pos)+" Items"])
        raw = text(by_cmd["data get entity @s Inventory"])
        ids = re.findall(r'\bid:\s*"([^"]+)"', raw)
        amounts = list(map(int, re.findall(r'\bcount:\s*(\d+)', raw)))
        assert len(ids) == len(amounts)
        inventory = Counter()
        for ident, amount in zip(ids, amounts):
            inventory[ident] += amount
        assert dict(inventory) == final["inventory"], (phase, inventory, final["inventory"])
        return {"energy_progress_burn_and_core_flags_preserved": True, "all_five_cable_states_exact": True,
                "machine_inventories_still_empty": True, "player_item_ids_counts_preserved": dict(inventory)}

    checks = {phase: run(phase) for phase in ("upgrade", "physical-reopen")}
    assert {name: sha(p) for name, p in tree_files(original_world).items()} == before_hashes
    result = {"schema": 1, "source_content": "0.7.0", "target_content": "0.8.0", "checks": checks,
              "source_result_sha256": sha(report), "source_world_files_sha256": before_hashes,
              "source_world_unmodified": True, "items_energy_progress_or_blocks_injected": False,
              "complete_component_fidelity_or_java_import_tested": False}
    (work/"checked-result.json").write_text(json.dumps(result, indent=2)+"\n")
    print("Own 0.7 cable world retained energy, burn, core flags, all cable states and inventory under 0.8 and physical reopen")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Test pipe hand use and menu open/close through Horizon's local packet harness.

Uses the stock integrated-server harness and a synthetic headless owner. This
does not authenticate an account, connect to the dedicated server or render GUI.
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


def operations():
    ops = []
    def cmd(line): ops.append({"op": "cmd", "cmd": line})
    def use(pos):
        ops.append({"op": "tick", "n": 2})
        ops.append({"op": "use_block", "pos": pos, "sequence": len(ops) + 1})
    def menu(label):
        ops.append({"op": "tick", "n": 2})
        ops.append({"op": "menu_state", "label": label})
    def hand(item, count=1): cmd(f"item replace entity @s weapon.mainhand with {item} {count}")
    cmd("gamemode creative")
    cmd("tp @s 128.5 200 178.5")
    ops.append({"op": "settle"})
    cmd("tick freeze")
    cmd("clear @s")
    cmd("fill 124 198 172 136 204 180 minecraft:air")
    cmd("fill 124 199 172 136 199 180 minecraft:stone")
    cmd("setblock 128 200 176 minecraft:chest")
    cmd("setblock 131 200 176 minecraft:chest")
    for x in (127, 129, 130, 133): cmd(f"setblock {x} 200 176 prettypipes:pipe")
    cmd("gamemode survival")
    hand("prettypipes:low_extraction_module", 2)
    use([129, 200, 176])
    menu("after_install_no_menu")
    cmd("clear @s prettypipes:low_extraction_module 0")
    cmd("data get block 129 200 176 modules")
    hand("prettypipes:high_extraction_module", 2)
    use([129, 200, 176])
    cmd("clear @s prettypipes:high_extraction_module 0")
    cmd("data get block 129 200 176 modules")
    hand("minecraft:air")
    use([129, 200, 176])
    menu("pipe_menu_open")
    ops.append({"op": "close_menu"})
    menu("after_close")
    cmd("data get block 129 200 176 modules")
    cmd("gamemode creative")
    hand("prettypipes:medium_extraction_module", 2)
    use([127, 200, 176])
    cmd("clear @s prettypipes:medium_extraction_module 0")
    cmd("data get block 127 200 176 modules")
    hand("minecraft:air")
    use([127, 200, 176])
    menu("creative_menu_open")
    ops.append({"op": "close_menu"})
    cmd("gamemode survival")
    hand("prettypipes:high_extraction_module", 2)
    use([130, 200, 176])
    cmd("clear @s prettypipes:high_extraction_module 0")
    cmd("data get block 130 200 176 modules")
    cmd("tp @s 132.5 200 178.5")
    hand("prettypipes:high_extraction_module", 2)
    use([133, 200, 176])
    menu("unattached_with_item")
    cmd("clear @s prettypipes:high_extraction_module 0")
    hand("minecraft:air")
    use([133, 200, 176])
    menu("unattached_empty_hand")
    return ops


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    server = args.server_dir.resolve()
    lock = verify(server)
    if lock["modules"].get("prettypipes", {}).get("version") not in ("0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0"):
        raise ValueError("requires a reviewed module-menu installation (0.3/0.4/0.5)")
    work = args.work.absolute()
    if (work.exists() or work.is_symlink() or any(p.is_symlink() for p in work.parents)
            or server in work.parents or work in server.parents):
        raise ValueError("work must be new and separate from the installed profile")
    config = tomllib.loads((server / "server.toml").read_text())
    work.mkdir(parents=True)
    shutil.copytree(server / "horizon-mods", work / "horizon-mods")
    shutil.copy2(server / "horizon-mods.txt", work / "horizon-mods.txt")
    (work / "eula.txt").write_text("eula=true\n")
    script = work / "operations.jsonl"
    script.write_text("".join(json.dumps(op) + "\n" for op in operations()))
    env = fresh_environment(work / "homes")
    env.update(HORIZON_PLAYER_NAME="TechQuestProbe", HORIZON_COMMAND_SCRIPT=str(script),
               HORIZON_COMMAND_OUTPUT=str(work / "result.jsonl"),
               HORIZON_HARNESS_CLIENT_CONFIG=str(work / "client-config.json"))
    command = [config["engine"]["path"], "--resources", config["engine"]["resources"],
               "--world", "techquest-horizon-menu", "--seed", "263", "--radius", "2",
               "--game-dir", str(work)]
    with (work / "console.log").open("x") as log:
        (work / "console.log").chmod(0o600)
        subprocess.run(command, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT,
                       timeout=300, check=True)
    rows = [json.loads(line) for line in (work / "result.jsonl").read_text().splitlines()]
    by_command = {}
    for row in rows: by_command.setdefault(row["cmd"], []).append(row)
    def result(line): return by_command[line][-1]["results"][-1]
    def menu(label): return by_command["#menu_state " + label][0]["state"]["own_slots"]
    assert menu("after_install_no_menu") == 0
    assert menu("pipe_menu_open") == 67, "empty hand did not open the pipe menu"
    assert menu("creative_menu_open") == 67
    assert menu("after_close") == 0
    assert menu("unattached_with_item") == 0 and menu("unattached_empty_hand") == 0
    assert result("clear @s prettypipes:low_extraction_module 0") == [True, 1]
    assert result("clear @s prettypipes:medium_extraction_module 0") == [True, 1]
    assert [row["results"][-1] for row in by_command["clear @s prettypipes:high_extraction_module 0"]] == [[True, 2], [True, 1], [True, 2]]
    for x, item in ((129, "low"), (127, "medium"), (130, "high")):
        for row in by_command[f"data get block {x} 200 176 modules"]:
            text = "".join(span[0] for message in row["messages"] for span in message)
            assert text.count("prettypipes:") == 1 and f"prettypipes:{item}_extraction_module" in text
            assert re.search(r"count:\s*1\b", text) and "Slot: 0b" in text
    connection = json.loads((work / "client-config.json").read_text())
    assert connection["joined"] and connection["logged_in"]
    report = {"schema": 1, "minecraft": "26.3", "connected_local_harness_client": True,
              "game_player_dispatch_tested": True, "survival_install_consumes_one": True,
              "creative_install_consumes_one": True, "duplicate_extractor_rejected": True,
              "all_three_tiers_installed_by_hand": True,
              "unattached_install_and_menu_rejected": True, "menu_open_and_close_tested": True,
              "module_persists_after_close": True, "wire_container_slots": 67,
              "menu_click_packet_dispatch_tested": False, "graphical_gui_rendered": False,
              "licensed_account_or_dedicated_join_tested": False, "published": False}
    (work / "checked-result.json").write_text(json.dumps(report, indent=2) + "\n")
    verify(server)
    print(json.dumps(report))


if __name__ == "__main__":
    main()

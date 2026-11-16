#!/usr/bin/env python3
"""Audit carried YUNG loot and open every table in a fresh graphical local world.

The chest fixtures use the installed tables, not generated structures. An
unknown-table empty control and save/reopen check guard stale menu observations.
No account login, dedicated join or source-version RNG parity is claimed.
Requires an X11 display and graphics driver, as live_pretty_pipes_gui.py does.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from install_isolated_server import fresh_environment, verify

IDS = ("betterdungeons", "betterstrongholds", "bettermineshafts", "betterfortresses")


def audit(server):
    tables, kinds, legacy = {}, Counter(), Counter()

    def visit(value):
        if isinstance(value, list):
            for entry in value:
                visit(entry)
        elif isinstance(value, dict):
            if isinstance(value.get("type"), str):
                kinds[value["type"]] += 1
            for key in ("condition", "function"):
                if isinstance(value.get(key), str):
                    legacy[key] += 1
            for entry in value.values():
                visit(entry)

    for mod in IDS:
        with zipfile.ZipFile(server / "horizon-mods" / (mod + ".hmod")) as archive:
            for name in sorted(archive.namelist()):
                prefix = f"data/{mod}/loot_table/"
                if name.startswith(prefix) and name.endswith(".json"):
                    raw = archive.read(name)
                    visit(json.loads(raw))
                    ident = mod + ":" + name[len(prefix):-5]
                    tables[ident] = {"sha256": hashlib.sha256(raw).hexdigest(),
                                     "position": [3 * (len(tables) % 9), 200,
                                                  3 * (len(tables) // 9)]}
    if len(tables) != 27 or legacy:
        raise ValueError("unexpected reviewed table count or legacy loot discriminators")
    return tables, dict(kinds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    server, work = args.server_dir.resolve(), args.work.absolute()
    verify(server)
    if (work.exists() or work.is_symlink() or any(p.is_symlink() for p in work.parents)
            or server in work.parents or work in server.parents):
        raise ValueError("work must be new and separate from the installed profile")
    if not os.environ.get("DISPLAY"):
        raise ValueError("requires an X11 display")
    tables, kinds = audit(server)
    config = tomllib.loads((server / "server.toml").read_text())
    engine = Path(config["engine"]["path"])
    ctl = engine.with_name("horizon-ctl")
    work.mkdir(mode=0o700, parents=True)
    shutil.copytree(server / "horizon-mods", work / "horizon-mods")
    shutil.copy2(server / "horizon-mods.txt", work / "horizon-mods.txt")
    (work / "eula.txt").write_text("eula=true\n")
    (work / "options.txt").write_text(
        "renderDistance:2\nsimulationDistance:2\nmaxFps:30\nguiScale:2\n"
        "pauseOnLostFocus:false\nfancyGraphics:false\n")
    rows, observations = [], {}
    socket = work / "control.sock"

    for phase in ("prepare", "reopen"):
        env = fresh_environment(work / ("homes-" + phase))
        runtime = work / ("run-" + phase)
        runtime.mkdir(mode=0o700)
        env.update(HORIZON_PLAYER_NAME="TQLootProbe", XDG_RUNTIME_DIR=str(runtime),
                   XDG_CACHE_HOME=str(work / "cache"), LP_NUM_THREADS="2",
                   MESA_SHADER_CACHE_DIR=str(work / "cache/mesa"), WINIT_UNIX_BACKEND="x11")

        def call(*words, timeout=60):
            result = subprocess.run(
                [str(ctl), "--socket", str(socket), "--timeout", str(timeout),
                 *map(str, words)], cwd=work, env=env, capture_output=True,
                text=True, timeout=timeout + 5)
            reply = json.loads(result.stdout)
            rows.append({"phase": phase, "args": list(map(str, words)), "reply": reply})
            if result.returncode or "error" in reply:
                raise RuntimeError(f"control {words}: {reply}")
            return reply

        def command(line):
            reply = call("command", line)
            call("wait", 4)
            return "\n".join(reply.get("chat", []))

        game = None
        with (work / (phase + "-console.log")).open("x") as log:
            (work / (phase + "-console.log")).chmod(0o600)
            try:
                game = subprocess.Popen(
                    [str(engine), "--resources", config["engine"]["resources"],
                     "--game-dir", str(work), "--radius", "2", "--control-socket", str(socket)],
                    cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 180
                while not socket.exists():
                    if game.poll() is not None:
                        raise RuntimeError(f"graphical engine exited {game.returncode}")
                    if time.monotonic() > deadline:
                        raise TimeoutError("graphical control socket not ready")
                    time.sleep(.2)
                call("open", "techquest-yung-loot", 263, "creative")
                call("wait-ready", timeout=180)
                call("resume")
                if phase == "prepare":
                    # Stream the test area, then construct non-adjacent chests.
                    command("tp @s 12.5 200 3.5")
                    call("wait-ready", timeout=180)
                    assert "Successfully filled" in command(
                        "fill -2 199 -2 26 199 11 minecraft:stone")
                    for table, entry in tables.items():
                        pos = " ".join(map(str, entry["position"]))
                        assert "Changed the block" in command(
                            f'setblock {pos} minecraft:chest{{LootTable:"{table}",LootTableSeed:263L}}')
                for table, entry in tables.items():
                    x, y, z = entry["position"]
                    command(f"tp @s {x + .5} {y} {z + 2.5}")
                    call("wait-ready", timeout=180)
                    pos = f"{x} {y} {z}"
                    before = command(f"data get block {pos}")
                    if phase == "prepare":
                        assert f'LootTable: "{table}"' in before, (table, before)
                    else:
                        assert "LootTable:" not in before, (table, before)
                    call("interact", x, y, z)
                    call("wait", 5)
                    screen = call("screen")
                    assert screen["screen"] == "container", (table, screen)
                    assert screen["container"] == [x, y, z], (table, screen)
                    menu = call("menu")
                    items = [s for s in menu["slots"] if 300 <= s["slot"] < 327]
                    assert items, (table, "empty loot")
                    assert all(s["stack"]["count"] > 0 for s in items)
                    if phase == "prepare":
                        observations[table] = {**entry, "menu_slots": items,
                                               "item_count": sum(s["stack"]["count"] for s in items)}
                    else:
                        assert items == observations[table]["menu_slots"], (table, "rerolled")
                    if table == "betterdungeons:skeleton_dungeon/chests/common":
                        call("screenshot", work / (phase + "-skeleton-loot.png"))
                    call("close")
                    call("wait", 4)
                    assert "LootTable:" not in command(f"data get block {pos}"), table
                if phase == "prepare":
                    command('setblock 3 200 9 minecraft:chest{LootTable:"techquest:missing_control",LootTableSeed:263L}')
                command("tp @s 3.5 200 11.5")
                call("interact", 3, 200, 9)
                call("wait", 5)
                control = call("screen")
                assert control["screen"] == "container" and control["container"] == [3, 200, 9]
                assert not [s for s in call("menu")["slots"] if 300 <= s["slot"] < 327]
                call("close")
                state = call("status")
                assert state["server"]["joined"] and state["server"]["decode_errors"] == 0
                call("save")
                call("quit")
                game.wait(timeout=60)
                assert game.returncode == 0
                print(f"{phase}: all 27 tables opened, unknown-table empty control passed", flush=True)
            finally:
                if game is not None and game.poll() is None:
                    try:
                        call("quit", timeout=30)
                        game.wait(timeout=30)
                    except Exception:
                        game.terminate()
                        game.wait(timeout=10)
                (work / "actions.json").write_text(json.dumps(rows, indent=2) + "\n")
    result = {"schema": 1, "minecraft": "26.3", "source_tables_audited": 27,
              "legacy_condition_function_discriminators": 0, "typed_nodes": kinds,
              "graphical_client_opened_tables": 27, "saved_reopened_tables": 27,
              "exact_menu_contents_preserved": True, "lazy_loot_consumed_on_open": True,
              "unknown_table_empty_control_each_phase": True,
              "protocol_decode_errors": 0, "runtime": "local integrated graphical client",
              "device_type": state["renderer"]["device_type"], "fixtures_injected": True,
              "original_version_rng_parity_tested": False, "generated_structure_loot_tested": False,
              "licensed_account_or_dedicated_join_tested": False,
              "full_mods_ported": False, "published": False, "tables": observations}
    (work / "checked-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("YUNG loot opening and save/reopen passed")


if __name__ == "__main__":
    main()

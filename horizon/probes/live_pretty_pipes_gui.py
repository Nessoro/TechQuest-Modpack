#!/usr/bin/env python3
"""Render and click the pipe menu using a fresh local graphical Horizon client.

Run inside an existing X11 display (for example xvfb-run). A graphics driver is
required; software Vulkan works. Only the sealed installation's content and
engine are used. This does not log into an account or join its dedicated server.
Screenshots, worlds and logs remain in --work, outside the repository.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from install_isolated_server import fresh_environment, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    server, work = args.server_dir.resolve(), args.work.absolute()
    lock = verify(server)
    if lock["modules"].get("prettypipes", {}).get("version") != "0.3.0":
        raise ValueError("requires the reviewed 0.3 module-menu installation")
    if (work.exists() or work.is_symlink() or any(p.is_symlink() for p in work.parents)
            or server in work.parents or work in server.parents):
        raise ValueError("work must be new and separate from the installed profile")
    if not os.environ.get("DISPLAY"):
        raise ValueError("run inside an X11 display, for example xvfb-run")
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
    env = fresh_environment(work / "homes")
    runtime = work / "run"
    runtime.mkdir(mode=0o700)
    env.update(HORIZON_PLAYER_NAME="TQGuiProbe", XDG_RUNTIME_DIR=str(runtime),
               XDG_CACHE_HOME=str(work / "cache"),
               MESA_SHADER_CACHE_DIR=str(work / "cache/mesa"),
               LP_NUM_THREADS="2", WINIT_UNIX_BACKEND="x11")
    socket = work / "control.sock"
    rows = []
    game = None

    def call(*words, timeout=60):
        result = subprocess.run(
            [str(ctl), "--socket", str(socket), "--timeout", str(timeout),
             *map(str, words)], cwd=work, env=env, capture_output=True,
            text=True, timeout=timeout + 5)
        reply = json.loads(result.stdout)
        rows.append({"args": list(map(str, words)), "reply": reply})
        if result.returncode or "error" in reply:
            raise RuntimeError(f"control {words}: {reply}")
        return reply

    def settle():
        call("wait", 5)

    def command(line):
        reply = call("command", line)
        settle()
        return "\n".join(reply.get("chat", []))

    def screen():
        reply = call("screen")
        assert reply["screen"] == "container", reply
        slots = {s["slot"]: s for s in reply["slots"]}
        assert {s for s in slots if 300 <= s < 500} == {300, 301, 302}
        return reply, slots

    def count():
        return call("inventory")["counts"].get("prettypipes:low_extraction_module", 0)

    with (work / "console.log").open("x") as log:
        (work / "console.log").chmod(0o600)
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
            call("open", "techquest-horizon-gui", 263, "creative")
            call("wait-ready", timeout=180)
            call("resume")
            command("fill -3 199 -3 5 199 5 minecraft:stone")
            command("setblock 0 200 0 minecraft:chest")
            command("setblock 1 200 0 prettypipes:pipe")
            command("give @s prettypipes:low_extraction_module 2")
            # Build and stream the floor before moving the player above it.
            command("tp @s 0.5 200 3.5")
            call("wait-ready", timeout=180)
            command("gamemode survival")
            call("select", "prettypipes:low_extraction_module")
            settle()
            assert count() == 2
            call("interact", 1, 200, 0)
            settle()
            assert count() == 1
            assert 'id: "prettypipes:low_extraction_module"' in command(
                "data get block 1 200 0 modules")
            # Preserve the second module in slot 0, and open with empty slot 1.
            call("select", 2)
            settle()
            call("interact", 1, 200, 0)
            settle()
            _, slots = screen()
            assert slots[300]["item"] == "prettypipes:low_extraction_module"
            call("screenshot", work / "pipe-menu.png")
            # NativeScreen's first module center in GUI pixels, at fixed scale 2.
            state = call("status")
            width, height = state["renderer"]["size"]
            call("click-at", (width // 2 - 176) // 2 + 70,
                 (height // 2 - 203) // 2 + 57)
            settle()
            reply, slots = screen()
            assert reply["carried"]["item"] == "prettypipes:low_extraction_module"
            assert all(slots[s].get("item") is None for s in (300, 301, 302))
            assert "Items: []" in command("data get block 1 200 0 modules")
            call("click-slot", 9)
            settle()
            assert count() == 2
            call("click-slot", 9, "shift")
            settle()
            _, slots = screen()
            assert slots[300]["item"] == "prettypipes:low_extraction_module"
            assert count() == 1
            # Try to put the second extractor into an incompatible second slot.
            call("click-slot", 0)
            settle()
            call("click-slot", 301)
            settle()
            reply, slots = screen()
            assert reply["carried"]["item"] == "prettypipes:low_extraction_module"
            assert slots[301].get("item") is None
            call("click-slot", 0)
            settle()
            call("click-slot", 300, "shift")
            settle()
            assert count() == 2
            _, slots = screen()
            assert all(slots[s].get("item") is None for s in (300, 301, 302))
            call("screenshot", work / "module-removed.png")
            call("close")
            settle()
            assert "Items: []" in command("data get block 1 200 0 modules")
            call("interact", 1, 200, 0)
            settle()
            _, slots = screen()
            assert all(slots[s].get("item") is None for s in (300, 301, 302))
            assert count() == 2
            state = call("status")
            assert state["server"]["joined"] and state["server"]["decode_errors"] == 0
            call("close")
            call("save")
            call("quit")
            game.wait(timeout=60)
            assert game.returncode == 0
            report = {
                "schema": 1, "minecraft": "26.3", "graphical_gui_rendered": True,
                "connected_local_graphical_client": True,
                "menu_click_packet_dispatch_tested": True,
                "coordinate_mouse_pickup_tested": True, "survival_hand_install_tested": True,
                "visible_module_slots": 3, "queue_slots_hidden": 64,
                "cursor_pickup_and_inventory_putdown": True,
                "shift_install_and_remove": True, "duplicate_extractor_rejected": True,
                "module_absent_after_close_reopen": True, "no_item_loss_or_duplication": True,
                "protocol_decode_errors": 0, "renderer": state["renderer"]["backend"],
                "device_type": state["renderer"]["device_type"],
                "driver": state["renderer"]["driver"], "engine_exit_code": game.returncode,
                "licensed_account_or_dedicated_join_tested": False,
                "full_pretty_pipes_ported": False, "published": False,
                "screenshots_sha256": {
                    name: hashlib.sha256((work / name).read_bytes()).hexdigest()
                    for name in ("pipe-menu.png", "module-removed.png")}}
            (work / "checked-result.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
        finally:
            if game is not None and game.poll() is None:
                try:
                    call("quit", timeout=30)
                    game.wait(timeout=30)
                except Exception:
                    game.terminate()
                    game.wait(timeout=10)
            (work / "actions.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()

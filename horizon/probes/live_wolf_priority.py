#!/usr/bin/env python3
"""Observe 1.21.1's loaded wolf registry priority in a new isolated server.

Copies the nine local source variant definitions. Synthetic c tags all match
plains, then remove each winner and reload, exposing the live selection order.
No player connects. No resources, world or raw logs belong in the repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from install_isolated_server import checked_path, fresh_environment

NAMES = ("pale", "spotted", "snowy", "black", "ashen", "rusty", "woods", "chestnut", "striped")


def probe(server_jar, source_outside, java, server_dir, output, port, accept_eula):
    if not accept_eula:
        raise ValueError("Minecraft EULA consent is required for this isolated reference server")
    server_dir, output = checked_path(server_dir), checked_path(output)
    if server_dir.exists() or output.exists():
        raise ValueError("server directory and report must be new")
    if not 1024 <= port <= 65535:
        raise ValueError("use a test port between 1024 and 65535")
    if hashlib.sha1(server_jar.read_bytes()).hexdigest() != "59353fb40c36d304f2035d51e7d6e6baa98dc05c":
        raise ValueError("expected official bundled server.jar 1.21.1")
    for target in (server_dir, output):
        if source_outside.resolve() in target.parents:
            raise ValueError("reference outputs must be outside source data")
        for parent in target.parents:
            if (parent / "level.dat").exists() or (parent / "horizon-resources.json").exists():
                raise ValueError("reference outputs must be outside worlds and prepared resources")
    payloads = {}
    for name in NAMES:
        path = checked_path(source_outside / f"data/minecraft/wolf_variant/{name}.json")
        raw = path.read_bytes()
        if json.loads(raw)["biomes"] != "#c:has_wolf_variant/" + name:
            raise ValueError("review a changed original selector")
        payloads[name] = raw
    server_dir.mkdir(parents=True)
    env = fresh_environment(server_dir / ".homes")
    pack = server_dir / "wolf-order-world/datapacks/source_wolf_selectors"
    pack.mkdir(parents=True)
    (pack / "pack.mcmeta").write_text(json.dumps({"pack": {
        "pack_format": 48, "description": "Local source selector order probe"}}))
    for name, raw in payloads.items():
        path = pack / f"data/minecraft/wolf_variant/{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    remaining = set(NAMES)
    def write_tags():
        for name in NAMES:
            path = pack / f"data/c/tags/worldgen/biome/has_wolf_variant/{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"replace": True, "values": ["minecraft:plains"] if name in remaining else []}))
    write_tags()
    (server_dir / "eula.txt").write_text("eula=true\n")
    (server_dir / "server.properties").write_text(
        f"server-ip=127.0.0.1\nserver-port={port}\nonline-mode=true\nwhite-list=true\n"
        "level-name=wolf-order-world\nlevel-seed=263\nview-distance=2\nsimulation-distance=2\npause-when-empty-seconds=0\n")
    process = subprocess.Popen([str(java.resolve()), "-Xmx2G", "-jar", str(server_jar.resolve()), "nogui"],
        cwd=server_dir, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines, condition = [], threading.Condition()
    def reader():
        with (server_dir / "driver-output.log").open("w") as log:
            for line in process.stdout:
                log.write(line)
                log.flush()
                with condition:
                    lines.append(line.rstrip())
                    condition.notify_all()
    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    def wait(predicate, start=0, timeout=180):
        deadline = time.monotonic() + timeout
        with condition:
            while time.monotonic() < deadline:
                for line in lines[start:]:
                    if predicate(line):
                        return line
                if process.poll() is not None:
                    raise RuntimeError("original server ended before the expected response")
                condition.wait(.5)
        raise TimeoutError("original server response timeout")
    def send(line):
        process.stdin.write(line + "\n")
        process.stdin.flush()
    def command(line):
        start = len(lines)
        marker = "ORDER_" + uuid.uuid4().hex
        send(line)
        send("say " + marker)
        wait(lambda value: marker in value, start, 45)
        return lines[start:]
    report = {"schema": 1, "source_minecraft": "1.21.1", "online_mode": True,
        "whitelist": True, "port": port, "bind": "127.0.0.1", "biome": "minecraft:plains",
        "memberships_are_synthetic": True, "uses_original_nine_terralith_variant_definitions": True,
        "source_variant_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()},
        "live_priority": []}
    try:
        wait(lambda line: "Done (" in line)
        command("forceload add 128 128")
        for _ in range(80):
            if any("ORDER_READY" in line for line in command("execute if loaded 128 220 128 run say ORDER_READY")):
                break
            time.sleep(.25)
        else:
            raise AssertionError("chunk unavailable")
        command("fillbiome 128 216 128 131 224 131 minecraft:plains")
        command("fill 124 219 124 132 219 132 minecraft:stone")
        def selected():
            command("kill @e[type=minecraft:wolf]")
            # No NBT: vanilla SummonCommand must actually call finalizeSpawn.
            command("summon minecraft:wolf 128 220 128")
            response = command("data get entity @e[type=minecraft:wolf,x=128,y=220,z=128,sort=nearest,limit=1] variant")
            for line in response:
                match = re.search(r'following entity data: "minecraft:([a-z_]+)"', line)
                if match:
                    return match[1]
            raise AssertionError("wolf variant response missing")
        for _ in range(9):
            winner = selected()
            if winner not in remaining:
                raise AssertionError("selection outside remaining memberships")
            report["live_priority"].append(winner)
            print("Observed:", winner, flush=True)
            remaining.remove(winner)
            write_tags()
            offset = len(lines)
            send("reload")
            wait(lambda line: "Loaded " in line and "advancements" in line, offset)
            time.sleep(.5)
        report["empty_membership_fallback"] = selected()
        assert report["empty_membership_fallback"] == "pale"
        command("save-all flush")
        report["probe_completed"] = True
    finally:
        if process.poll() is None:
            send("stop")
            try:
                process.wait(60)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(15)
        thread.join(2)
        report["exit_code"] = process.returncode
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("server-jar", "source-outside", "java", "server-dir", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--port", type=int, default=25602)
    parser.add_argument("--accept-eula", action="store_true")
    probe(**vars(parser.parse_args()))

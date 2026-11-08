#!/usr/bin/env python3
"""CI-only real client boot to TitleScreen, with a temporary observation mod.

Uses original official-launcher version metadata and the official NeoForge installer.
An offline development identity is used solely for the title screen. CI clicks the
hash-pinned Explosion Overhaul tutorial's Skip Guide / Vanilla-like choices in a
disposable profile. No login, world, server, EULA acceptance or player-pack change.
"""
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def download(info, target, algorithm="sha1"):
    expected = info[algorithm]
    if target.is_file() and hashlib.new(algorithm, target.read_bytes()).hexdigest() == expected:
        return
    url = info["url"]
    if not url.startswith("https://"):
        raise ValueError("HTTPS required: " + url)
    target.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read(256 * 1024 * 1024 + 1)
            if len(data) > 256 * 1024 * 1024 or ("size" in info and len(data) != info["size"]):
                raise ValueError("Official download size mismatch: " + url)
            if hashlib.new(algorithm, data).hexdigest() != expected:
                raise ValueError("Official download checksum mismatch: " + url)
            target.write_bytes(data)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def allowed(rules):
    value = not rules
    for rule in rules:
        system = rule.get("os", {})
        match = system.get("name", "linux") == "linux"
        if "arch" in system:
            match = match and re.fullmatch(system["arch"], "amd64") is not None
        if "version" in system:
            match = match and re.fullmatch(system["version"], os.uname().release) is not None
        match = match and all(not wanted for wanted in rule.get("features", {}).values())
        if match:
            value = rule["action"] == "allow"
    return value


def arguments(items, variables):
    result = []
    for item in items:
        if isinstance(item, dict):
            if not allowed(item.get("rules", [])):
                continue
            item = item["value"]
        for part in item if isinstance(item, list) else [item]:
            value = re.sub(r"\$\{([^}]+)\}", lambda m: variables[m[1]], part)
            result.append(value)
    return result


def observe(profile, parent, launcher, game, report):
    libraries = launcher / "libraries"
    selected = {}
    for item in parent["libraries"] + profile["libraries"]:
        parts = item["name"].split(":")
        key = tuple(parts[:2] + parts[3:])
        selected[key] = item
    downloads, classpath, natives = [], [], []
    for item in selected.values():
        if not allowed(item.get("rules", [])):
            continue
        entries = item.get("downloads", {})
        if "artifact" in entries:
            info = entries["artifact"]
            target = libraries / info["path"]
            downloads.append((info, target))
            classpath.append(target)
        classifier = item.get("natives", {}).get("linux")
        if classifier:
            info = entries["classifiers"][classifier.replace("${arch}", "64")]
            target = libraries / info["path"]
            downloads.append((info, target))
            natives.append(target)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda pair: download(*pair), downloads))
    native_dir = launcher / "natives"
    native_dir.mkdir()
    # Modern Mojang profiles also encode native artifacts as ordinary libraries.
    natives.extend(p for p in classpath if "natives-linux" in p.name)
    for path in natives:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith(".so"):
                    (native_dir / Path(name).name).write_bytes(archive.read(name))
    # forgeclient locates the installer-generated patched Minecraft under libraries.
    # The original obfuscated client is an installer input, not a second runtime module.
    assets = launcher / "assets"
    index_file = assets / "indexes" / (parent["assetIndex"]["id"] + ".json")
    download(parent["assetIndex"], index_file)
    objects = json.loads(index_file.read_text())["objects"]
    tasks = {}
    for item in objects.values():
        digest = item["hash"]
        tasks[digest] = ({"url": "https://resources.download.minecraft.net/" + digest[:2] + "/" + digest,
                          "sha1": digest, "size": item["size"]}, assets / "objects" / digest[:2] / digest)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda pair: download(*pair), tasks.values()))
    # Compile against installed official libraries; reflection avoids game remapping assumptions.
    compile_cp = os.pathsep.join(str(p) for p in libraries.rglob("*.jar"))
    classes = launcher / "probe-classes"
    subprocess.run(["javac", "-proc:none", "--release", "21", "-cp", compile_cp,
                    "-d", str(classes), str(ROOT / "tests/runtime-client-probe/TechQuestRuntimeProbe.java")],
                   check=True, timeout=120)
    with zipfile.ZipFile(game / "mods/techquest-runtime-probe.jar", "w") as archive:
        archive.writestr("META-INF/neoforge.mods.toml", 'modLoader="javafml"\nloaderVersion="[4,)"\nlicense="MIT"\n'
                         '[[mods]]\nmodId="techquest_runtime_probe"\nversion="1.0.0"\ndisplayName="TechQuest CI Observer"\n')
        for path in classes.rglob("*.class"):
            archive.write(path, path.relative_to(classes).as_posix())
    variables = {
        "natives_directory": str(native_dir), "launcher_name": "TechQuest-CI-observer",
        "launcher_version": "1", "classpath": os.pathsep.join(map(str, classpath)),
        "library_directory": str(libraries), "classpath_separator": os.pathsep,
        "auth_player_name": "TechQuestCI", "version_name": profile["id"], "game_directory": str(game),
        "assets_root": str(assets), "assets_index_name": parent["assetIndex"]["id"],
        "auth_uuid": "00000000000000000000000000000000", "auth_access_token": "0",
        "clientid": "", "auth_xuid": "", "user_type": "legacy", "version_type": "CI",
        "resolution_width": "960", "resolution_height": "600",
    }
    jvm = arguments(parent["arguments"]["jvm"] + profile["arguments"]["jvm"], variables)
    game_args = arguments(parent["arguments"]["game"] + profile["arguments"]["game"], variables)
    cfg = json.loads((ROOT / "modlist.json").read_text())
    wanted_keys = cfg["performance_profile"]["key_defaults"]
    command = ["java", "-Xms1G", "-Xmx5G", "-Dtechquest.probe.dir=" + str(report),
               "-Dtechquest.probe.bindings=" + ",".join(wanted_keys), *jvm,
               profile["mainClass"], *game_args, "--width", "960", "--height", "600"]
    with (report / "console.log").open("w") as log:
        process = subprocess.Popen(command, cwd=game, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 600
            setup_since = None
            while process.poll() is None and not (report / "ready.json").exists() and time.monotonic() < deadline:
                state_file = report / "screen-state.txt"
                state = state_file.read_text() if state_file.exists() else ""
                for kind, screen_name in (("guide", "GuideSlidesScreen"), ("mode", "FirstTimeScreen")):
                    snapshot = report / (kind + "-before.png")
                    if "com.vinlanx.explosionoverhaul.client." + screen_name + ":overlay=false" in state and not snapshot.exists():
                        subprocess.run(["import", "-window", "root", str(snapshot)], check=True, timeout=20)
                if "physics.settings.QuickSetupScreen:overlay=false" in state:
                    setup_since = setup_since or time.monotonic()
                    if time.monotonic() - setup_since > 15:
                        break  # Capture the actual unwanted wizard instead of waiting ten minutes.
                else:
                    setup_since = None
                time.sleep(1)
            subprocess.run(["import", "-window", "root", str(report / "screen.png")], check=True, timeout=20)
            if not (report / "ready.json").exists():
                raise RuntimeError("Real client did not reach TitleScreen without an overlay; inspect screenshot/logs")
            ready = json.loads((report / "ready.json").read_text())
            if ready.get("screen") != "TitleScreen" or ready.get("overlay") is not False:
                raise RuntimeError("Invalid client readiness observation")
            observed = ready["options"]
            expected = cfg["performance_profile"]["video_defaults"]
            if (observed["renderDistance"] != expected["renderDistance"]
                    or observed["simulationDistance"] != expected["simulationDistance"]
                    or observed["maxFps"] != expected["maxFps"] or observed["graphics"].lower() != "fast"):
                raise RuntimeError("Generated performance settings were not applied by the real client")
            if ready["bindings"] != wanted_keys:
                raise RuntimeError("Generated key bindings were not applied by the real client: " + str(ready["bindings"]))
            if any(value != "NONE" for value in ready["modifiers"].values()):
                raise RuntimeError("A default key modifier survived the generated plain-key assignment")
            expected_physics = json.loads((ROOT / "compat/physicsmod/physics_client_config.json").read_text())
            observed_physics = ready["physics"]
            for name in ("maxPhysicsObjects", "blockPhysicsRange", "cpuThreads", "oceanPhysics", "liquidPhysics", "windPhysics"):
                if observed_physics[name] != expected_physics[name]:
                    raise RuntimeError("Physics preset was not applied by the real client: " + name)
            if observed_physics["showSetup"]:
                raise RuntimeError("Physics setup wizard was not marked complete")
            (report / "stop").touch()
            if process.wait(timeout=45) != 0:
                raise RuntimeError("Client exited with failure after reaching the menu")
            print("PASS: real Minecraft client reached TitleScreen without an overlay; screenshot captured.")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if (game / "logs").exists():
                shutil.copytree(game / "logs", report / "game-logs", dirs_exist_ok=True)
            if (game / "crash-reports").exists():
                shutil.copytree(game / "crash-reports", report / "crash-reports", dirs_exist_ok=True)


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get("DISPLAY"):
        raise SystemExit("Only an isolated Linux GitHub Actions runner with Xvfb is supported")
    report = ROOT / "output/runtime-client"
    report.mkdir(parents=True, exist_ok=False)
    shutil.copy2(ROOT / "output/versions-lock.json", report / "versions-lock.json")
    with zipfile.ZipFile(next((ROOT / "output").glob("*.mrpack"))) as archive:
        (report / "download-index.json").write_bytes(archive.read("modrinth.index.json"))
    (report / "scope.json").write_text(json.dumps({"scope": "real client menu only, plus CI observation mod",
        "world_tested": False, "server_tested": False, "performance_benchmark": False,
        "account_login_tested": False, "ci_ui_choices": ["accessibility welcome skipped", "Explosion Overhaul Skip Guide / Vanilla-like"], "commit": os.environ.get("GITHUB_SHA")}, indent=2))
    with tempfile.TemporaryDirectory(prefix="techquest-runtime-") as tmp:
        launcher = Path(tmp) / "launcher"
        version = launcher / "versions/1.21.1"
        version.mkdir(parents=True)
        with urllib.request.urlopen("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json", timeout=60) as response:
            versions = json.load(response)
        entry = next(v for v in versions["versions"] if v["id"] == "1.21.1")
        download(entry, version / "1.21.1.json")
        parent = json.loads((version / "1.21.1.json").read_text())
        download(parent["downloads"]["client"], version / "1.21.1.jar")
        with zipfile.ZipFile(version / "1.21.1.jar") as archive:
            data_version = json.loads(archive.read("version.json"))["world_version"]
        defaults = (ROOT / "output/client/options.txt").read_text()
        if ("version:" + str(data_version)) not in defaults.splitlines():
            raise ValueError("Generated options DataVersion does not match the verified official client")
        (report / "minecraft-data-version.json").write_text(json.dumps({"game": "1.21.1", "data_version": data_version}))
        (launcher / "launcher_profiles.json").write_text('{"profiles":{}}')
        plan = json.loads((ROOT / "windows-installer/assets/neoforge-21.1.264-bootstrap.json").read_text())
        installer = Path(tmp) / "installer.jar"
        download(plan["installer"], installer, "sha512")
        with (report / "installer.log").open("w") as log:
            subprocess.run(["java", "-jar", str(installer), "--installClient", str(launcher)],
                           cwd=tmp, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
        profile = json.loads((launcher / "versions/neoforge-21.1.264/neoforge-21.1.264.json").read_text())
        game = Path(tmp) / "game"
        shutil.copytree(ROOT / "output/client", game)
        # CI fixture preference only: skip Minecraft's first-run accessibility welcome.
        # Ordinary player options remain unchanged and no license prompt is accepted.
        with (game / "options.txt").open("a") as options:
            options.write("onboardAccessibility:false\n")
        observe(profile, parent, launcher, game, report)


if __name__ == "__main__":
    main()

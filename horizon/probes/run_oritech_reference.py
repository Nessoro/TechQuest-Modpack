#!/usr/bin/env python3
"""Compile/run the original Oritech oracle in a new loopback NeoForge world.

Requires existing pinned original binary inputs and a NeoForge installation.
Does not download/decompile dependencies or import account data. EULA consent
is needed for preparation; a restart reuses that isolated world's consent.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from install_isolated_server import fresh_environment
from stage_terralith_content import read_checked

PROJECTS = {"4sYI62kA": "oritech", "lhGA9TYQ": "architectury", "8BmcQJ2H": "geckolib"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("runtime", "work"): parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--accept-eula", action="store_true"); parser.add_argument("--reopen", action="store_true")
    parser.add_argument("--oracle", choices=("energy", "content", "pulverizer", "foundry", "assembler"), default="energy")
    parser.add_argument("--cases", type=Path)
    args = parser.parse_args(); runtime = args.runtime.resolve(); work = args.work.absolute()
    if args.oracle == "content" and (args.cases is None or args.reopen):
        raise ValueError("content oracle needs --cases and does not use --reopen")
    if (work.is_symlink() or any(p.is_symlink() for p in work.parents)
            or runtime == work or runtime in work.parents and work.parent != runtime):
        raise ValueError("reference must be a separate direct runtime child or separate workspace directory")
    probe = Path(__file__).with_name({"energy": "OritechEnergyProbe.java", "content": "OritechContentProbe.java", "pulverizer": "OritechPulverizerProbe.java", "foundry": "OritechFoundryProbe.java", "assembler": "OritechAssemblerProbe.java"}[args.oracle])
    sha = lambda p: hashlib.sha256(read_checked(p)).hexdigest()
    server = work / "server"; jar = work / "probe/techquest-reference-probe.jar"
    if not args.reopen:
        if work.exists() or not args.accept_eula: raise ValueError("use a new --work and explicit --accept-eula")
        for p in work.parents:
            if (p / "level.dat").exists() or (p / "horizon-resources.json").exists(): raise ValueError("reference must be outside worlds/resources")
        pins = json.loads(read_checked(ROOT / "source/techquest-post-pr48-candidate.json"))["modrinth_lock"]
        binaries = []
        for project in PROJECTS:
            pin = pins[project]; binary = runtime / "oritech-reference-input" / pin["filename"]
            if hashlib.sha512(read_checked(binary)).hexdigest() != pin["sha512"]: raise ValueError("binary pin mismatch: " + project)
            binaries.append(binary)
        libs = runtime / "neoforge-reference/server/libraries"
        named = libs / "net/minecraft/server/1.21.1-20240808.144430/server-1.21.1-20240808.144430-srg.jar"
        if not named.is_file() or not (libs / "net/neoforged/neoforge/21.1.264/unix_args.txt").is_file(): raise ValueError("requires mapped Minecraft 1.21.1 / NeoForge 21.1.264")
        classes = work / "probe/classes"; classes.mkdir(parents=True, mode=0o700)
        cp = [named] + [p for p in libs.rglob("*.jar") if p != named and not any(s in p.name for s in ("-slim", "-unpacked"))] + binaries
        subprocess.run([str(runtime / "jdk25/bin/javac"), "--release", "21", "-proc:none", "-cp", os.pathsep.join(map(str, cp)), "-d", str(classes), str(probe)], check=True)
        with zipfile.ZipFile(jar, "x", zipfile.ZIP_DEFLATED) as z:
            for path in classes.rglob("*.class"): z.write(path, path.relative_to(classes))
            z.writestr("META-INF/neoforge.mods.toml", 'modLoader="javafml"\nloaderVersion="[4,)"\nlicense="MIT"\n[[mods]]\nmodId="techquest_reference_probe"\nversion="0.1"\ndisplayName="TechQuest developer reference probe"\n')
        server.mkdir(); (server / "libraries").symlink_to(libs, target_is_directory=True); (server / "mods").mkdir()
        for p in [*binaries, jar]: shutil.copy2(p, server / "mods" / p.name)
        (server / "eula.txt").write_text("eula=true\n")
        for name in ("ops.json", "whitelist.json"): (server / name).write_text("[]\n")
        (server / "server.properties").write_text("server-ip=127.0.0.1\nserver-port=25638\nlevel-name=techquest-oritech-reference\nlevel-seed=263\nonline-mode=true\nwhite-list=true\nenable-rcon=false\nenable-query=false\nview-distance=4\nsimulation-distance=4\n")
        metadata = {"oracle": args.oracle, "probe_source_sha256": sha(probe), "probe_jar_sha256": sha(jar), "oritech": "1.2.13", "minecraft": "1.21.1", "neoforge": "21.1.264"}
        if args.cases is not None: metadata["cases_sha256"] = sha(args.cases)
        (work / "inputs.json").write_text(json.dumps(metadata, indent=2) + "\n")
    else:
        metadata = json.loads(read_checked(work / "inputs.json"))
        if sha(probe) != metadata["probe_source_sha256"] or sha(server / "mods/techquest-reference-probe.jar") != metadata["probe_jar_sha256"]:
            raise ValueError("oracle changed since initial save")
        properties = (server / "server.properties").read_text().splitlines()
        if not {"server-ip=127.0.0.1", "online-mode=true", "white-list=true", "enable-rcon=false", "enable-query=false"} <= set(properties):
            raise ValueError("reference server isolation settings changed")
        if (server / "eula.txt").read_text().strip() != "eula=true": raise ValueError("missing isolated EULA consent")
    phase = "reopen" if args.reopen else "initial"
    env = fresh_environment(Path(tempfile.mkdtemp(prefix=phase + "-homes-", dir=work)))
    launch = [str(runtime / "jdk25/bin/java"), "-Xmx3G", "-Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts", "-Dtechquest.reference.result=" + str(work / (phase + "-result.json"))]
    if args.reopen: launch.append("-Dtechquest.reference.reopen=true")
    if args.cases is not None: launch.append("-Dtechquest.reference.cases=" + str(args.cases.resolve()))
    proxy = urllib.parse.urlsplit(env.get("HTTPS_PROXY", ""))
    if proxy.hostname:
        for protocol in ("http", "https"): launch += [f"-D{protocol}.proxyHost={proxy.hostname}", f"-D{protocol}.proxyPort={proxy.port or 80}"]
    launch += ["@libraries/net/neoforged/neoforge/21.1.264/unix_args.txt", "nogui"]
    with (work / (phase + "-console.log")).open("x") as log:
        (work / (phase + "-console.log")).chmod(0o600)
        subprocess.run(launch, cwd=server, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
    result = json.loads((work / (phase + "-result.json")).read_text())
    if args.reopen and args.oracle == "energy":
        initial = json.loads((work / "initial-result.json").read_text())
        assert result["before_generator"] == initial["saved_generator"] and result["before_furnace"] == initial["saved_furnace"]
        assert result["after_furnace"]["items"] == [{"slot": 1, "item": "minecraft:iron_ingot", "count": 2}]
    if args.reopen and args.oracle in ("pulverizer", "foundry", "assembler"):
        initial = json.loads((work / "initial-result.json").read_text())
        assert result["before"] == initial["saved"]
    print("Original Oritech", args.oracle, phase, "passed")


if __name__ == "__main__": main()

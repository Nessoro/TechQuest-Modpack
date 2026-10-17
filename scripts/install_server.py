#!/usr/bin/env python3
"""Install the TechQuest Modrinth pack onto a dedicated NeoForge server.

Downloads server-side mod files only from the URLs in .mrpack, checks hashes,
and installs official NeoForge. Does not agree to the Minecraft EULA.
IndustrialCraft 2: Nostalgia is NOT redistributed; add its JAR manually.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack as packbuilder

NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"

def check_index(index):
    if index.get("game") != "minecraft":
        raise packbuilder.BuildError("Not a Minecraft Modrinth pack")
    deps = index.get("dependencies", {})
    if deps.get("minecraft") != "1.21.1":
        raise packbuilder.BuildError("Expected Minecraft 1.21.1")
    version = deps.get("neoforge", "")
    if not re.fullmatch(r"21\\.1\\.[0-9]+", version):
        raise packbuilder.BuildError("Expected a NeoForge 21.1.x version")
    return version

def server_records(index):
    seen = set()
    for item in index.get("files", []):
        if item.get("env", {}).get("server") == "unsupported":
            continue
        path = item.get("path", "")
        if not path.startswith("mods/"):
            raise packbuilder.BuildError("Unexpected file path in .mrpack: " + path)
        name = packbuilder.safe_filename(path.removeprefix("mods/"))
        if not name.lower().endswith(".jar") or name in seen:
            raise packbuilder.BuildError("Duplicate or invalid JAR name: " + name)
        seen.add(name)
        url_list = item.get("downloads", [])
        if not url_list or not url_list[0].startswith("https://"):
            raise packbuilder.BuildError("Missing HTTPS download for: " + name)
        hashes = item.get("hashes", {})
        if not any(hashes.get(k) for k in ("sha512", "sha1")):
            raise packbuilder.BuildError("Missing integrity hash for: " + name)
        yield {"file": {"filename": name, "url": url_list[0], "hashes": hashes}}

def prepare_properties(target):
    props = target / "server.properties"
    if not props.exists():
        props.write_text(
            "motd=TechQuest Industrial Frontier\\n"
            "max-players=8\\n"
            "online-mode=true\\n"
            "white-list=true\\n"
            "enforce-whitelist=true\\n"
            "enable-rcon=false\\n"
            "view-distance=8\\n"
            "simulation-distance=6\\n"
            "allow-flight=true\\n", encoding="utf-8")

def install_neoforge(target, version):
    if not shutil.which("java"):
        raise packbuilder.BuildError("Java not found. Install Java 21 before running.")
    probe = subprocess.run(["java", "-version"], text=True,
                           capture_output=True, check=True, timeout=15)
    if not re.search(r'version "[1]?21[.+"-]', probe.stderr + probe.stdout):
        raise packbuilder.BuildError("Java 21 required: " + (probe.stderr or probe.stdout).splitlines()[0])
    name = f"neoforge-{version}-installer.jar"
    root_url = f"{NEOFORGE_MAVEN}/{version}/{name}"
    installer = target / name
    if not installer.is_file():
        body = packbuilder.get_url(root_url)
        expected = packbuilder.get_url(root_url + ".sha512").decode("ascii").strip().split()[0]
        if hashlib.sha512(body).hexdigest().lower() != expected.lower():
            raise packbuilder.BuildError("NeoForge installer checksum mismatch")
        installer.write_bytes(body)
    print("Installing official NeoForge", version, flush=True)
    subprocess.run(["java", "-jar", name, "--installServer"], cwd=target,
                   check=True, timeout=900)

def main():
    ap = argparse.ArgumentParser(description="Install TechQuest server from .mrpack")
    ap.add_argument("--pack", required=True, type=Path, help="Path to Modrinth .mrpack")
    ap.add_argument("--target", required=True, type=Path, help="New server folder")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-neoforge", action="store_true",
                    help="Download mods but skip the official NeoForge installer")
    args = ap.parse_args()
    with zipfile.ZipFile(args.pack) as z:
        index = json.loads(z.read("modrinth.index.json"))
    ver = check_index(index)
    files = list(server_records(index))
    print(f"TechQuest: {len(files)} server-side JAR files; NeoForge {ver}")
    if args.dry_run:
        for x in files:
            print(" -", x["file"]["filename"])
        return 0
    target = args.target.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    mods = target / "mods"
    mods.mkdir(exist_ok=True)
    for i, info in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {info['file']['filename']}", flush=True)
        packbuilder.download_checked(info, mods)
    prepare_properties(target)
    if not args.skip_neoforge:
        install_neoforge(target, ver)
    (target / "TECHQUEST_README.txt").write_text(
        "TechQuest 0.1.0-alpha (UNTESTED).\\n"
        "Industrial Craft 2: Nostalgia is REQUIRED but not redistributed.\\n"
        "Download it separately from its author and put JAR in mods/.\\n"
        "Check all mod versions before playing. Back up the world.\\n"
        "Read Minecraft EULA. If you accept, set eula=true in eula.txt.\\n"
        "To start on Linux: ./run.sh nogui. On Windows: run.bat nogui.\\n"
        "Use whitelist and online-mode. Do not open this untested server to public.\\n",
        encoding="utf-8")
    print("Server files prepared at", target)
    print("NEXT: add IndustrialCraft 2: Nostalgia and accept EULA yourself.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (packbuilder.BuildError, OSError, ValueError, KeyError, zipfile.BadZipFile,
            subprocess.SubprocessError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise SystemExit(2)

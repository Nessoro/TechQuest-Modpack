#!/usr/bin/env python3
"""Install the TechQuest Modrinth pack onto a dedicated NeoForge server.

Downloads server-side mod files only from the URLs in .mrpack, checks hashes,
and installs official NeoForge. Does not agree to the Minecraft EULA.
IndustrialCraft 2: Nostalgia is referenced through a pinned URL in the .mrpack.
"""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack as packbuilder
from scripts.mods_transaction import activate_staged_mods

NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"

def check_index(index):
    if index.get("game") != "minecraft":
        raise packbuilder.BuildError("Not a Minecraft Modrinth pack")
    deps = index.get("dependencies", {})
    if deps.get("minecraft") != "1.21.1":
        raise packbuilder.BuildError("Expected Minecraft 1.21.1")
    version = deps.get("neoforge", "")
    if version != "21.1.264":
        raise packbuilder.BuildError("Expected NeoForge 21.1.264")
    return version

def server_records(index):
    seen = set()
    for item in index.get("files", []):
        path = item.get("path", "")
        if packbuilder.is_removed_mod_jar(path.removeprefix("mods/")):
            raise packbuilder.BuildError("Removed mod in server manifest: " + path)
        if item.get("env", {}).get("server") == "unsupported":
            continue
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
            "motd=TechQuest Industrial Frontier\n"
            "max-players=8\n"
            "online-mode=true\n"
            "white-list=true\n"
            "enforce-whitelist=true\n"
            "enable-rcon=false\n"
            "view-distance=6\n"
            "simulation-distance=5\n"
            "allow-flight=true\n", encoding="utf-8")

def install_compatibility(pack_path, mods):
    """Install TechQuest Compatibility JAR and preserve the Superb Warfare server workaround."""
    with zipfile.ZipFile(pack_path) as archive:
        name = packbuilder.COMPAT_JAR_NAME
        entry = "overrides/mods/" + name
        if entry not in archive.namelist():
            raise packbuilder.BuildError("Missing TechQuest Compatibility JAR: " + name)
        (mods / name).write_bytes(archive.read(entry))
    for path in mods.glob("superbwarfare-*.jar"):
        packbuilder.patch_superb_server_jar(path)


def install_guide_overrides(pack_path, target):
    """Install the book definition and its server datapack, preserving local edits."""
    with zipfile.ZipFile(pack_path) as archive:
        for entry in archive.infolist():
            if not entry.filename.startswith("overrides/") or entry.is_dir():
                continue
            relative = entry.filename[len("overrides/"):]
            if not (relative.startswith("patchouli_books/techquest_guide/") or
                    relative in ("config/openloader/packs/techquest_starter_guide.zip",
                                "config/openloader/packs/techquest_micropatch_033.zip")):
                continue
            if ".." in Path(relative).parts or any(c in relative for c in ("\\", "\x00", ":")):
                raise packbuilder.BuildError("Unsafe guide override path: " + relative)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                destination.write_bytes(archive.read(entry))

def install_neoforge(target, version):
    if not shutil.which("java"):
        raise packbuilder.BuildError("Java not found. Install Java 21 before running.")
    probe = subprocess.run(["java", "-version"], text=True,
                           capture_output=True, check=True, timeout=15)
    found_version = re.search(r'version "([0-9]+)', probe.stderr + probe.stdout)
    if not found_version or found_version.group(1) != "21":
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

def install_pack(pack, target, dry_run=False, skip_neoforge=False):
    with zipfile.ZipFile(pack) as archive:
        index = json.loads(archive.read("modrinth.index.json"))
        entry = "overrides/mods/" + packbuilder.COMPAT_JAR_NAME
        if entry not in archive.namelist():
            raise packbuilder.BuildError("Missing TechQuest Compatibility in .mrpack")
        if any(packbuilder.is_removed_mod_jar(name.removeprefix("overrides/mods/"))
               for name in archive.namelist() if name.startswith("overrides/mods/")):
            raise packbuilder.BuildError("Removed mod in .mrpack overrides")
    ver = check_index(index)
    files = list(server_records(index))
    print(f"TechQuest: {len(files)} server-side JAR files; NeoForge {ver}")
    if dry_run:
        for x in files:
            print(" -", x["file"]["filename"])
        return 0
    target = Path(target).expanduser().resolve()
    mods = target / "mods"
    if mods.is_dir() and any(mods.iterdir()) and not (target / "TECHQUEST_README.txt").is_file():
        raise packbuilder.BuildError("Existing server mods are not a managed TechQuest installation")
    target.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".techquest-download-", dir=target))
    try:
        for i, info in enumerate(files, 1):
            print(f"[{i}/{len(files)}] {info['file']['filename']}", flush=True)
            packbuilder.download_checked(info, staging)
        # Patch only the staged Superb Warfare server JAR, never the live one.
        install_compatibility(pack, staging)
        if not skip_neoforge:
            install_neoforge(target, ver)

        def finish():
            install_guide_overrides(pack, target)
            with zipfile.ZipFile(pack) as archive:
                for name in ("TECHQUEST_OPTIONAL_LOCAL_MODS.json",
                             "TECHQUEST_TACZ_OFFICIAL_GUNPACKS.json"):
                    entry = "overrides/" + name
                    dest = target / name
                    if entry in archive.namelist() and not dest.exists():
                        dest.write_bytes(archive.read(entry))
            prepare_properties(target)
            (target / "TECHQUEST_README.txt").write_text(
                "TechQuest 0.3.3-micro3: server JARs installed with hash checks.\n"
                "TechQuest Compatibility retained; RPG Core and PMMO excluded.\n"
                "Superb Warfare client mixin patched only in the server copy.\n"
                "Existing worlds, config, properties and eula.txt are preserved.\n"
                "Read Minecraft EULA; set eula=true only after explicit acceptance.\n"
                "Start with ./run.sh nogui (Linux) or run.bat nogui (Windows).\n",
                encoding="utf-8")
        activate_staged_mods(target, staging, finish)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print("Server files prepared at", target)
    print("NEXT: review and accept Minecraft EULA yourself before starting.")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Install TechQuest server from .mrpack")
    ap.add_argument("--pack", required=True, type=Path, help="Path to Modrinth .mrpack")
    ap.add_argument("--target", required=True, type=Path, help="Managed or new server folder")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-neoforge", action="store_true",
                    help="Download mods but skip the official NeoForge installer")
    args = ap.parse_args()
    return install_pack(args.pack, args.target, args.dry_run, args.skip_neoforge)

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (packbuilder.BuildError, OSError, ValueError, KeyError, zipfile.BadZipFile,
            subprocess.SubprocessError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise SystemExit(2)

#!/usr/bin/env python3
"""Install verified TechQuest client mod JARs for the official Minecraft Launcher.

Works with BOTH Full and Lite .mrpack packages. Minecraft Java and official
NeoForge 21.1.259 must be installed separately using the official installers.
The destination should be a NEW dedicated game directory, not a shared .minecraft.
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack

def client_records(index):
    if index.get("game") != "minecraft":
        raise build_pack.BuildError("Not a Minecraft .mrpack")
    deps = index.get("dependencies", {})
    if deps.get("minecraft") != "1.21.1" or deps.get("neoforge") != "21.1.259":
        raise build_pack.BuildError("Expected Minecraft 1.21.1 / NeoForge 21.1.259")
    seen = set()
    result = []
    for entry in index.get("files", []):
        if entry.get("env", {}).get("client") == "unsupported":
            continue
        path = entry.get("path", "")
        if not path.startswith("mods/"):
            raise build_pack.BuildError("Unexpected entry in package: " + path)
        filename = build_pack.safe_filename(path[5:])
        if filename in seen or not filename.lower().endswith(".jar"):
            raise build_pack.BuildError("Duplicate/invalid mod JAR name: " + filename)
        seen.add(filename)
        urls = entry.get("downloads", [])
        if not urls or not urls[0].startswith("https://"):
            raise build_pack.BuildError("Missing HTTPS mod download: " + filename)
        hashes = entry.get("hashes", {})
        if not hashes.get("sha512") and not hashes.get("sha1"):
            raise build_pack.BuildError("No checksum for " + filename)
        result.append({"file": {"filename": filename,
                                "url": urls[0], "hashes": hashes}})
    if not result:
        raise build_pack.BuildError("Modrinth package contains no client JARs")
    return result

def install(pack: Path, game_dir: Path, dry_run=False):
    with zipfile.ZipFile(pack) as archive:
        index = json.loads(archive.read("modrinth.index.json"))
    records = client_records(index)
    destination = game_dir.expanduser().resolve()
    mods = destination / "mods"
    if mods.is_dir() and any(mods.glob("*.jar")):
        raise build_pack.BuildError(
            "Existing mods found. Use a NEW dedicated game directory to prevent conflicts: " +
            str(mods))
    if dry_run:
        print("Will download", len(records), "client JARs to", mods)
        for item in records:
            print("  ", item["file"]["filename"])
        return len(records)
    mods.mkdir(parents=True, exist_ok=True)
    for i, item in enumerate(records, 1):
        print(f"[{i}/{len(records)}] {item['file']['filename']}", flush=True)
        build_pack.download_checked(item, mods)
    (destination / "TECHQUEST_LAUNCHER_README.txt").write_text(
        "Client mods installed with SHA-1/SHA-512 verification.\n"
        "Install Minecraft Java 1.21.1 and NeoForge 21.1.259 in the OFFICIAL launcher.\n"
        "Create/edit a NeoForge installation; set Game Directory to this folder.\n"
        "Use Java 21. Allocate ~4-6 GiB for Lite if system RAM allows, 8 GiB for Full.\n"
        "Do NOT run the vanilla Minecraft profile: it cannot load NeoForge mods.\n"
        "Test a new world first; TechQuest remains an experimental modpack.\n",
        encoding="utf-8")
    print("Success. Set official Launcher -> Installations -> NeoForge -> Game Directory:")
    print(destination)
    return len(records)

def main():
    p = argparse.ArgumentParser(description="Install TechQuest Full/Lite mods for official Launcher")
    p.add_argument("--pack", required=True, type=Path, help=".mrpack from the GitHub artifact")
    p.add_argument("--game-dir", required=True, type=Path, help="New empty Minecraft game directory")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    install(args.pack, args.game_dir, args.dry_run)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (build_pack.BuildError, OSError, KeyError, ValueError,
            json.JSONDecodeError, zipfile.BadZipFile) as e:
        print("INSTALL FAILED:", e, file=sys.stderr)
        sys.exit(2)

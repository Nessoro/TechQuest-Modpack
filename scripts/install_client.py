#!/usr/bin/env python3
"""Install verified TechQuest client mod JARs for the official Minecraft Launcher.

Works with the single unified optimized .mrpack. Minecraft Java and official
NeoForge 21.1.264 must be installed separately using the official installers.
The destination should be a NEW dedicated game directory, not a shared .minecraft.
"""
import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack
from scripts.mods_transaction import activate_staged_mods

def client_records(index):
    if index.get("game") != "minecraft":
        raise build_pack.BuildError("Not a Minecraft .mrpack")
    deps = index.get("dependencies", {})
    if deps.get("minecraft") != "1.21.1" or deps.get("neoforge") != "21.1.264":
        raise build_pack.BuildError("Expected Minecraft 1.21.1 / NeoForge 21.1.264")
    seen = set()
    result = []
    for entry in index.get("files", []):
        path = entry.get("path", "")
        if build_pack.is_removed_mod_jar(path.removeprefix("mods/")):
            raise build_pack.BuildError("Removed mod in client manifest: " + path)
        if entry.get("env", {}).get("client") == "unsupported":
            continue
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

def install_guide_overrides(archive, game_dir):
    """Extract first-party guide data only, never arbitrary archive paths."""
    allowed_prefix = "patchouli_books/techquest_guide/"
    allowed_datapacks = {
        "config/openloader/packs/techquest_starter_guide.zip",
        "config/openloader/packs/techquest_micropatch_033.zip",
    }
    for info in archive.infolist():
        if not info.filename.startswith("overrides/"):
            continue
        relative = info.filename[len("overrides/"):]
        if relative.endswith("/"):
            continue
        if not (relative.startswith(allowed_prefix)
                or relative in (*allowed_datapacks, "mods/techquest-compat-1.0.0.jar",
                                "options.txt", "TECHQUEST_OPTIMIZED.txt",
                                "config/physicsmod/physics_client_config.json",
                                "config/physicsmod/physics_server_config.json",
                                "config/betterzoom-client.toml",
                                "config/incoming-client.toml",
                                "config/explosionoverhaul/explosionoverhaul-client.toml",
                                "config/jade/plugins.json",
                                "config/healthindicatortxf.json5",
                                "defaultconfigs/openpartiesandclaims-server.toml",
                                "TECHQUEST_INGAME_GUIDE.txt",
                                "TECHQUEST_OPTIONAL_LOCAL_MODS.json",
                                 "TECHQUEST_TACZ_OFFICIAL_GUNPACKS.json")):
            continue
        parts = Path(relative).parts
        if ".." in parts or any(x in relative for x in ("\\", "\x00", ":")):
            raise build_pack.BuildError("Unsafe guide override path: " + relative)
        target = game_dir.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(archive.read(info.filename))


def install(pack: Path, game_dir: Path, dry_run=False):
    with zipfile.ZipFile(pack) as archive:
        index = json.loads(archive.read("modrinth.index.json"))
    records = client_records(index)
    destination = game_dir.expanduser().resolve()
    mods = destination / "mods"
    has_old_mods = mods.is_dir() and any(mods.iterdir())
    managed = any((destination / marker).is_file() for marker in
                  ("TECHQUEST_LAUNCHER_README.txt", "TechQuest_НАСТРОЙКА.txt",
                   "TECHQUEST_OPTIMIZED.txt"))
    if has_old_mods and not managed:
        raise build_pack.BuildError(
            "Existing mods are not a managed TechQuest profile: " + str(mods))
    if dry_run:
        print("Will download", len(records), "client JARs to", mods)
        for item in records:
            print("  ", item["file"]["filename"])
        return len(records)
    with zipfile.ZipFile(pack) as archive:
        compat_entry = "overrides/mods/" + build_pack.COMPAT_JAR_NAME
        if compat_entry not in archive.namelist():
            raise build_pack.BuildError("Missing TechQuest Compatibility in .mrpack")
        if any(build_pack.is_removed_mod_jar(name.removeprefix("overrides/mods/"))
               for name in archive.namelist() if name.startswith("overrides/mods/")):
            raise build_pack.BuildError("Removed mod in .mrpack overrides")
        compat_data = archive.read(compat_entry)
    destination.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".techquest-download-", dir=destination))
    try:
        for i, item in enumerate(records, 1):
            print(f"[{i}/{len(records)}] {item['file']['filename']}", flush=True)
            build_pack.download_checked(item, staging)
        (staging / build_pack.COMPAT_JAR_NAME).write_bytes(compat_data)

        def finish():
            with zipfile.ZipFile(pack) as archive:
                install_guide_overrides(archive, destination)
            (destination / "TECHQUEST_LAUNCHER_README.txt").write_text(
                "TechQuest 0.3.3-micro3: client mods installed with SHA verification.\n"
                "TechQuest Compatibility (Create-IC2 and Better Zoom Mixin) installed.\n"
                "Use Minecraft Java 1.21.1, official NeoForge 21.1.264 and Java 21.\n"
                "Official Launcher -> Installations -> NeoForge -> Game Directory: " +
                str(destination) + "\nPreserve worlds and player settings.\n",
                encoding="utf-8")
        activate_staged_mods(destination, staging, finish)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    print("Success. Official Launcher -> NeoForge -> Game Directory:", destination)
    return len(records)

def main():
    p = argparse.ArgumentParser(description="Install unified optimized TechQuest mods for official Launcher")
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

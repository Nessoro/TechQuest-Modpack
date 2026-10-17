#!/usr/bin/env python3
"""Add the user-downloaded IndustrialCraft 2: Nostalgia JAR to a local .mrpack.

The public GitHub build contains metadata and an installer, not third-party
binaries. This creates a separate PERSONAL copy that includes IndustrialCraft.
"""
import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack

META_FILES = ("META-INF/neoforge.mods.toml", "META-INF/mods.toml")

def validate_ic2(jar: Path, expected_name: str):
    if not jar.is_file():
        raise build_pack.BuildError("IndustrialCraft file not found: " + str(jar))
    if jar.name != expected_name:
        raise build_pack.BuildError(
            f"Unexpected file {jar.name}; expected {expected_name}")
    if not (1024 < jar.stat().st_size < 80 * 1024 * 1024):
        raise build_pack.BuildError("Unreasonable IC2 file size")
    if not zipfile.is_zipfile(jar):
        raise build_pack.BuildError("IndustrialCraft JAR is not a valid ZIP")
    with zipfile.ZipFile(jar) as archive:
        for name in META_FILES:
            try:
                info = archive.getinfo(name)
                if info.file_size > 1024 * 1024:
                    raise build_pack.BuildError("Metadata larger than expected")
                content = archive.read(name).decode("utf-8")
                if re.search(r"""modId\s*=\s*["']ic2["']""", content, re.I):
                    return
            except KeyError:
                continue
    raise build_pack.BuildError("Selected JAR does not declare the 'ic2' mod ID")

def embed_ic2(pack_path: Path, jar: Path, output: Path, expected_name: str):
    if pack_path.resolve() == output.resolve():
        raise build_pack.BuildError("Do not overwrite the original MRPACK")
    validate_ic2(jar, expected_name)
    if not zipfile.is_zipfile(pack_path):
        raise build_pack.BuildError("Input package is not a ZIP")
    item = "overrides/mods/" + expected_name
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pack_path) as src, zipfile.ZipFile(output, "w") as dest:
        if "modrinth.index.json" not in src.namelist():
            raise build_pack.BuildError("Not a Modrinth pack")
        if item in src.namelist():
            raise build_pack.BuildError("IndustrialCraft is already in this pack")
        index = json.loads(src.read("modrinth.index.json"))
        if index.get("dependencies", {}).get("minecraft") != "1.21.1":
            raise build_pack.BuildError("Expected a Minecraft 1.21.1 modpack")
        for info in src.infolist():
            dest.writestr(info, src.read(info))
        dest.write(jar, item, compress_type=zipfile.ZIP_DEFLATED)
    return item

def main():
    p = argparse.ArgumentParser(description="Include original IndustrialCraft 2 JAR in local TechQuest")
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--jar", type=Path, required=True)
    p.add_argument("--output", type=Path,
                   default=ROOT / "output" / "TechQuest_1.21.1_WITH_IC2_LOCAL.mrpack")
    p.add_argument("--server-mods", type=Path, help="Also copy IC2 into server/mods")
    args = p.parse_args()
    cfg = build_pack.load_cfg()
    ic2 = next((x for x in cfg.get("manual_mods", [])
               if "Industrial Craft" in x.get("name", "")), None)
    if not ic2:
        raise build_pack.BuildError("IndustrialCraft is absent from modlist.json")
    expected = build_pack.safe_filename(ic2["file_name"])
    embedded = embed_ic2(args.pack, args.jar, args.output, expected)
    print(f"Created client MRPACK: {args.output} ({embedded})")
    if args.server_mods is not None:
        folder = args.server_mods
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / expected
        if dest.exists():
            raise build_pack.BuildError(f"File already exists at {dest}; review version manually")
        shutil.copy2(args.jar, dest)
        print("Copied IC2 to server:", dest)
    print("This package contains a third-party mod. Review its license before sharing.")
    print("This does NOT confirm the modpack launches in Minecraft.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (build_pack.BuildError, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print("ERROR:", exc, file=sys.stderr)
        raise SystemExit(2)

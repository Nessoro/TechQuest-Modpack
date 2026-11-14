#!/usr/bin/env python3
"""Fail the build if micro3 changes mod selection or reintroduces removed JARs.

Audit current generated client/server directories and Modrinth package against
their own locked index. Runtime behavior still requires a real Minecraft test.
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

import build_pack

PACK = "TechQuest_1.21.1_0.3.3_ALPHA.mrpack"


def audit(output=Path("output")):
    output = Path(output)
    pack_path = output / PACK
    compat = build_pack.COMPAT_JAR_NAME
    expected_bytes = build_pack.compatibility_jar()
    with zipfile.ZipFile(pack_path) as archive:
        names = archive.namelist()
        index = json.loads(archive.read("modrinth.index.json"))
        if index.get("game") != "minecraft" or index.get("dependencies") != {
            "minecraft": "1.21.1", "neoforge": "21.1.264"}:
            raise ValueError("Wrong micro3 Minecraft/NeoForge dependencies")
        if "overrides/mods/" + compat not in names:
            raise ValueError("Missing Compatibility .mrpack override")
        if archive.read("overrides/mods/" + compat) != expected_bytes:
            raise ValueError("Compatibility .mrpack payload mismatch")
        if any(build_pack.is_removed_mod_jar(name.removeprefix("overrides/mods/"))
               for name in names if name.startswith("overrides/mods/")):
            raise ValueError("Removed RPG Core or PMMO in .mrpack overrides")
        rows = index["files"]
    seen = set()
    per_side = {"client": set(), "server": set()}
    for row in rows:
        path = row.get("path", "")
        if not path.startswith("mods/"):
            raise ValueError("Unexpected Modrinth path: " + path)
        filename = build_pack.safe_filename(path[5:])
        if build_pack.is_removed_mod_jar(filename):
            raise ValueError("Removed RPG Core or PMMO in Modrinth index: " + filename)
        if filename.lower() in seen or filename == compat:
            raise ValueError("Duplicate or first-party JAR in index: " + filename)
        seen.add(filename.lower())
        for side in per_side:
            if row.get("env", {}).get(side) != "unsupported":
                per_side[side].add(filename)
    files_by_side = {}
    compat_hash = hashlib.sha256(expected_bytes).hexdigest()
    for side, expected in per_side.items():
        directory = output / side / "mods"
        actual = {p.name for p in directory.glob("*.jar")}
        if any(build_pack.is_removed_mod_jar(name) for name in actual):
            raise ValueError("Removed RPG Core or PMMO in " + side)
        if actual != expected | {compat}:
            raise ValueError(f"{side} manifest mismatch: missing={sorted((expected | {compat}) - actual)}, extra={sorted(actual - expected - {compat})}")
        if (directory / compat).read_bytes() != expected_bytes:
            raise ValueError(side + " Compatibility differs from generated JAR")
        files_by_side[side] = sorted(actual)
    with zipfile.ZipFile(directory / compat) as jar:
        if jar.testzip() is not None:
            raise ValueError("Corrupt Compatibility JAR")
        required = ("techquest-compat.mixins.json",
                    "techquest/compat/mixin/BetterZoomEarlyTickMixin.class",
                    "data/create/recipe/smelting/ingot_tin_compat_ic2.json",
                    "data/create/recipe/blasting/ingot_tin_compat_ic2.json")
        for name in required:
            if name not in jar.namelist():
                raise ValueError("Missing Compatibility resource: " + name)
        mixins = json.loads(jar.read("techquest-compat.mixins.json"))
        if "BetterZoomEarlyTickMixin" not in mixins.get("client", []):
            raise ValueError("Better Zoom workaround no longer configured")
    result = {
        "status": "PACKAGING_ONLY_NOT_RUNTIME_VERIFIED",
        "compat_sha256": compat_hash,
        "modrinth_files": len(rows),
        "client_mods": files_by_side["client"],
        "server_mods": files_by_side["server"],
        "disallowed_jars_present": False,
    }
    destination = output / "micro3-package-audit.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"micro3: client {len(files_by_side['client'])}, server {len(files_by_side['server'])}; Compatibility SHA256 {compat_hash}")
    print("RPG Core and PMMO absent; indexed mod files match both generated profiles.")
    print("NOT a Minecraft client or dedicated-server runtime test.")
    return result


if __name__ == "__main__":
    try:
        audit(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output"))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, build_pack.BuildError) as exc:
        print("MICRO3 PACKAGE AUDIT FAILED:", exc, file=sys.stderr)
        sys.exit(1)

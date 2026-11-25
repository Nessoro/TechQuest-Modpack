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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack



def audit(output=Path("output")):
    output = Path(output)
    version = build_pack.load_cfg()["version"]
    pack_path = output / ("TechQuest_" + version + ".mrpack")
    compat = build_pack.COMPAT_JAR_NAME
    hybrid = build_pack.HYBRID_JAR_NAME
    first_party = {compat, hybrid}
    first_party_lower = {name.lower() for name in first_party}
    expected_bytes = build_pack.compatibility_jar()
    expected_hybrid = build_pack.compiled_hybrid_jar()
    with zipfile.ZipFile(pack_path) as archive:
        names = archive.namelist()
        index = json.loads(archive.read("modrinth.index.json"))
        if index.get("versionId") != version:
            raise ValueError("Wrong package patch version")
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
        # Require exactly the compiled first-party payloads in the overrides.
        jar_overrides = [name for name in names if name.lower().startswith(
                         ("overrides/mods/", "client-overrides/mods/", "server-overrides/mods/"))
                         and name.lower().endswith(".jar")]
        if sorted(jar_overrides) != sorted("overrides/mods/" + name for name in first_party):
            raise ValueError("Unexpected, missing or duplicate first-party .mrpack JAR overrides: "
                             + repr(jar_overrides))
        if build_pack.hybrid_from_pack(archive, required=True) != expected_hybrid:
            raise ValueError("Hybrid Warfare .mrpack payload differs from compiled JAR")
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
        if (filename.lower() in seen or filename.lower() in first_party_lower or
                filename.lower().startswith("techquest-hybrid-warfare")):
            raise ValueError("Duplicate or first-party JAR in index: " + filename)
        seen.add(filename.lower())
        for side in per_side:
            if row.get("env", {}).get(side) != "unsupported":
                per_side[side].add(filename)
    files_by_side = {}
    compat_hash = hashlib.sha256(expected_bytes).hexdigest()
    hybrid_hash = hashlib.sha256(expected_hybrid).hexdigest()
    for side, expected in per_side.items():
        directory = output / side / "mods"
        actual = {p.name for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".jar"}
        if any(build_pack.is_removed_mod_jar(name) for name in actual):
            raise ValueError("Removed RPG Core or PMMO in " + side)
        expected = expected | first_party
        if actual != expected:
            raise ValueError(f"{side} manifest mismatch: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")
        if (directory / compat).read_bytes() != expected_bytes:
            raise ValueError(side + " Compatibility differs from generated JAR")
        if (directory / hybrid).read_bytes() != expected_hybrid:
            raise ValueError(side + " Hybrid Warfare differs from compiled JAR")
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
        "hybrid_sha256": hybrid_hash,
        "modrinth_files": len(rows),
        "client_mods": files_by_side["client"],
        "server_mods": files_by_side["server"],
        "disallowed_jars_present": False,
    }
    destination = output / "micro3-package-audit.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"micro3: client {len(files_by_side['client'])}, server {len(files_by_side['server'])}; Compatibility SHA256 {compat_hash}")
    print("Hybrid Warfare SHA256:", hybrid_hash)
    print("RPG Core and PMMO absent; indexed mods and both first-party JARs match both profiles.")
    print("NOT a Minecraft client or dedicated-server runtime test.")
    return result


if __name__ == "__main__":
    try:
        audit(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output"))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, build_pack.BuildError) as exc:
        print("MICRO3 PACKAGE AUDIT FAILED:", exc, file=sys.stderr)
        sys.exit(1)

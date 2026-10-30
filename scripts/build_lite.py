#!/usr/bin/env python3
"""Derive a graphics-focused TechQuest Lite .mrpack from the Full package.

Lite preserves all shared gameplay mods and the official server package.
Client-only optimization files are downloaded by the importing launcher.
No mod JAR binaries are included in the generated archive.
"""
import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack

README = """TECHQUEST LITE — Minecraft 1.21.1 / NeoForge 21.1.259

Lite preserves every gameplay mod from TechQuest Full, including BuildCraft,
IndustrialCraft 2, Create, Mekanism, Superb Warfare and Explosion Overhaul.
It removes the optional Iris shader loader, and adds client-only optimizers.
There is no separate Lite server: use the SAME TechQuest Full server.

RECOMMENDED VIDEO SETTINGS FOR LOW-END PCs
- Graphics: Fast
- Render distance: 6 chunks (try 4 on weak iGPUs)
- Simulation distance: 5 chunks (singleplayer); server controls this online
- Entity distance: 50–75%
- Particles: Minimal
- Clouds: Off, shaders: Off
- Biome blend: 0x0
- Mipmap levels: 0–2
- FPS limit: 60 (or 30 to improve stability)
- Fullscreen resolution: 1280x720 for older GPUs
- Allocate 4–6 GiB RAM where system memory permits;
  do not allocate more than half of installed system RAM.
- Close Chrome, video apps, and overlays before launch.
- If RAM is 8 GiB or less, a pack this large may remain unplayable;
  client-side optimizers cannot guarantee sufficient memory or FPS.

These settings are recommendations, not forcibly applied to a saved profile.
Test first in a NEW world. A NeoForge version match is not proof of runtime compatibility.
"""

def derive_index(index, full_lock, extra_records, exclude_projects):
    out = dict(index)
    all_files = list(index["files"])
    full_names = {Path(f["path"]).name for f in all_files}
    prior_requests = {m["requested"] for m in full_lock.get("mods", [])}
    if not all_files or index.get("game") != "minecraft":
        raise build_pack.BuildError("Base pack has no Minecraft files")
    if index.get("dependencies", {}).get("minecraft") != "1.21.1":
        raise build_pack.BuildError("Base pack Minecraft version mismatch")
    # Exclusion is strictly limited to the explicitly declared shader loader.
    if set(exclude_projects) != {"iris"}:
        raise build_pack.BuildError("Lite profile may only exclude the Iris shader loader")
    selected = [f for f in all_files
                if not Path(f["path"]).name.lower().startswith("iris-")]
    removed = len(all_files) - len(selected)
    if removed != 1:
        raise build_pack.BuildError(f"Expected one Iris shader JAR to remove; got {removed}")
    included = []
    for rec in extra_records:
        if rec["requested"] in prior_requests:
            continue
        if rec["environment"].get("client") == "unsupported":
            raise build_pack.BuildError("Lite optimizer is not client-compatible: " + rec["title"])
        if rec["environment"].get("server") != "unsupported":
            raise build_pack.BuildError(
                "Refusing a non-client-only optimizer in Lite: " + rec["title"])
        name = build_pack.safe_filename(rec["filename"])
        if name in full_names:
            continue
        selected.append({
            "path": "mods/" + name,
            "hashes": {key: value for key, value in rec["file"]["hashes"].items()
                       if key in ("sha1", "sha512")},
            "env": {"client": "required", "server": "unsupported"},
            "downloads": [rec["file"]["url"]],
            "fileSize": rec["file"]["size"],
        })
        included.append({"project": rec["requested"], "version": rec["version"],
                         "filename": name})
        full_names.add(name)
    if not included:
        raise build_pack.BuildError("No extra client optimizers found")
    out["name"] = "TechQuest: Industrial Frontier — Lite"
    out["versionId"] = str(index["versionId"]) + "-lite"
    out["summary"] = "Same multiplayer gameplay as Full; client optimizations and no Iris."
    out["files"] = selected
    return out, included

def build_lite(base, lock_path, destination, cfg):
    preset = cfg["lite_profile"]
    if base.resolve() == destination.resolve():
        raise build_pack.BuildError("Lite cannot overwrite Full")
    with zipfile.ZipFile(base) as zin:
        full_index = json.loads(zin.read("modrinth.index.json"))
    full_lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lite_cfg = dict(cfg)
    lite_cfg["mods"] = preset["extra_client_mods"]
    print("Resolving client-only Lite optimizers...")
    extras, skipped = build_pack.resolve_manifest(lite_cfg)
    if skipped:
        raise build_pack.BuildError("A Lite optimizer was skipped: " + str(skipped))
    lite_index, included = derive_index(
        full_index, full_lock, extras, preset["exclude_projects"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(base) as zin, zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zout:
        for member in zin.infolist():
            if member.filename == "modrinth.index.json":
                continue
            if member.filename == "overrides/TECHQUEST_LITE_SETTINGS.txt":
                continue
            zout.writestr(member, zin.read(member))
        zout.writestr("modrinth.index.json", json.dumps(lite_index, ensure_ascii=False, indent=2))
        zout.writestr("overrides/TECHQUEST_LITE_SETTINGS.txt", README)
    report = {
        "base_pack": base.name, "lite_pack": destination.name,
        "removed_client_mods": ["Iris"],
        "optimizers": included, "full_count": len(full_index["files"]),
        "lite_count": len(lite_index["files"]),
        "server_unchanged": True,
        "warning": "No Minecraft runtime test has been performed.",
    }
    build_pack.write_json(destination.parent / "Lite_BUILD_STATUS.json", report)
    print("Created", destination, "with", len(included), "client-only additions")
    return report

def main():
    parser = argparse.ArgumentParser(description="Create optimized TechQuest Lite client package")
    parser.add_argument("--base", type=Path,
                        default=ROOT / "output" / "TechQuest_1.21.1_0.1.0.mrpack")
    parser.add_argument("--lock", type=Path, default=ROOT / "output" / "versions-lock.json")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "output" / "TechQuest_1.21.1_LITE_0.1.0.mrpack")
    args = parser.parse_args()
    build_lite(args.base, args.lock, args.output, build_pack.load_cfg())
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (build_pack.BuildError, OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print("LITE BUILD FAILED:", exc, file=sys.stderr)
        sys.exit(2)

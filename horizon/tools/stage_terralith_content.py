#!/usr/bin/env python3
"""Synchronize Terralith content definitions with the locally adapted datapack.

World generation uses datapack overrides; live features also need the upgraded
definitions in the content root. Builds a separate SDK-checked hmod, never
installs it or changes source mods, worlds or namespace ownership.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import tomllib


def read_checked(path: Path) -> bytes:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("symlink in content input")
    return path.read_bytes()


def stage(work: Path, datapack: Path, output: Path, sdk: Path) -> dict:
    if output.exists() or output.is_symlink():
        raise ValueError("output must be new")
    if any((p / "level.dat").exists() for p in output.resolve().parents):
        raise ValueError("stage outside existing worlds")
    if any((p / "horizon-resources.json").exists() for p in output.resolve().parents):
        raise ValueError("stage outside prepared game resources")
    if any(origin.resolve() in output.resolve().parents for origin in (work, datapack)):
        raise ValueError("output must be separate from both source trees")
    source = work.resolve() / "mods/terralith/carry"
    manifest = read_checked(source / "horizon-mod.toml")
    meta = tomllib.loads(manifest.decode())
    if (meta.get("id"), meta.get("version"), meta.get("api")) != ("terralith", "2.6.2", "0.2"):
        raise ValueError("review a different source manifest before staging")
    if meta.get("side") != "both" or "registries" not in meta.get("capabilities", []):
        raise ValueError("server registries capability required")
    trial = json.loads(read_checked(datapack / "techquest-worldgen-trial.json"))
    if (trial.get("terralith"), trial.get("minecraft"), trial.get("schema")) != ("2.6.2", "26.3", 1):
        raise ValueError("expected the reviewed 26.3 Terralith trial")
    payloads = {"horizon-mod.toml": manifest}
    for kind in ("assets", "data"):
        for path in sorted((source / kind).rglob("*")):
            if path.is_symlink():
                raise ValueError("symlink in content tree")
            if path.is_file():
                payloads[path.relative_to(source).as_posix()] = read_checked(path)
    # Only this module's namespace; vanilla dimension/biome overrides remain
    # world-specific datapack files, rather than becoming global mod ownership.
    overlays = []
    for path in sorted((datapack / "data/terralith").rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink in adapted content")
        if path.is_file():
            relative = path.relative_to(datapack).as_posix()
            payloads[relative] = read_checked(path)
            overlays.append(relative)
    if not overlays:
        raise ValueError("missing adapted Terralith content")
    migrations = []
    for old, new in (("configured_feature", "feature"), ("configured_carver", "carver")):
        prefix = f"data/terralith/worldgen/{old}/"
        for relative in list(payloads):
            if relative.startswith(prefix):
                replacement = relative.replace(prefix, f"data/terralith/worldgen/{new}/", 1)
                if replacement not in payloads or replacement not in overlays:
                    raise ValueError("missing upgraded replacement: " + relative)
                del payloads[relative]
                migrations.append({"from": relative, "to": replacement})
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".terralith-content-", dir=output.parent) as temporary:
        root = Path(temporary) / "content"
        for relative, data in payloads.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        subprocess.run([str(sdk.resolve()), "build"], cwd=root, check=True,
                       capture_output=True, text=True, timeout=180)
        package = root / "target/horizon-mod/terralith.hmod"
        checked = subprocess.run([str(sdk.resolve()), "check", str(package), "--json"],
                                 cwd=root, check=True, capture_output=True, text=True, timeout=180)
        verdict = json.loads(checked.stdout)
        facts = verdict.get("report", {})
        package_hash = hashlib.sha256(package.read_bytes()).hexdigest()
        if (not verdict.get("ok") or (facts.get("id"), facts.get("version"), facts.get("api"),
                                     facts.get("side")) != ("terralith", "2.6.2", "0.2", "both")
                or facts.get("sha256") != package_hash):
            raise ValueError("SDK rejected the derived module identity")
        report = {"schema": 1, "id": "terralith", "source_version": "2.6.2",
                  "minecraft": "26.3", "sdk_validated": True,
                  "source_files_modified": False, "world_datapack_still_required": True,
                  "namespace_ownership_changed": False, "adapted_files": overlays,
                  "registry_path_migrations": migrations,
                  "sha256": package_hash,
                  "server_boot_tested": False, "gameplay_ported": False}
        (root / "techquest-content-trial.json").write_text(json.dumps(report, indent=2) + "\n")
        root.rename(output)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("work", "datapack", "output", "sdk"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    report = stage(args.work, args.datapack, args.output, args.sdk)
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("adapted_files", "registry_path_migrations")}, indent=2))


if __name__ == "__main__":
    main()

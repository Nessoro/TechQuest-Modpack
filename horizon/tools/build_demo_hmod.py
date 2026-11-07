#!/usr/bin/env python3
"""Offline structural .hmod ZIP builder; official Horizon check still required."""
from __future__ import annotations
import argparse
import json
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "first_party" / "expedition_marker"
OUT = ROOT / "out" / "techquest_expedition_marker.hmod"

def list_content(root: Path) -> list[tuple[str, bytes]]:
    meta = tomllib.loads((root / "horizon-mod.toml").read_text(encoding="utf-8"))
    if (meta.get("id"), meta.get("api"), meta.get("side")) != (
        "techquest_expedition_marker", "0.2", "both"
    ):
        raise ValueError("Horizon metadata mismatch")
    if meta.get("capabilities") != ["registries"]:
        raise ValueError("Wrong capabilities")
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if p.is_symlink():
            raise ValueError("Symlink is not allowed")
        rel = p.relative_to(root).as_posix()
        if rel == "horizon-mod.toml":
            payload = p.read_bytes()
        elif (rel.startswith("assets/") or rel.startswith("data/")) and rel.endswith(".json"):
            payload = p.read_bytes()
            json.loads(payload)
        else:
            continue
        files.append((rel, payload))
    paths = {x[0] for x in files}
    must = {
        "horizon-mod.toml",
        "data/techquest_expedition_marker/horizon/block/expedition_marker.json",
        "data/techquest_expedition_marker/recipe/expedition_marker.json",
        "assets/techquest_expedition_marker/blockstates/expedition_marker.json",
    }
    if not must.issubset(paths):
        raise ValueError("Missing essential Horizon files")
    return files

def package(root: Path = MOD, output: Path = OUT) -> Path:
    files = list_content(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for name, body in files:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, body)
    return output

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=OUT)
    args = p.parse_args()
    path = package(output=args.output)
    print("Structural package created:", path)
    print("NOT Horizon-validated. Run cargo horizon-mod build/check on the source.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

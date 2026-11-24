#!/usr/bin/env python3
"""Locate exactly one source mrpack and reject mismatched version/game/loader."""
import argparse
import json
import re
import zipfile
from pathlib import Path


def find_pack(root: Path, snapshot: Path) -> Path:
    cfg = json.loads(snapshot.read_text(encoding="utf-8"))
    version = cfg["version"]
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){3}", version):
        raise ValueError("Expected four-part TechQuest version")
    packs = sorted(root.rglob("*.mrpack"))
    if len(packs) != 1 or packs[0].name != f"TechQuest_{version}.mrpack":
        raise ValueError("Expected exactly one correctly named source mrpack")
    pack = packs[0]
    if pack.is_symlink():
        raise ValueError("Symlink source pack not allowed")
    with zipfile.ZipFile(pack) as archive:
        if archive.namelist().count("modrinth.index.json") != 1:
            raise ValueError("Expected exactly one Modrinth index")
        index = json.loads(archive.read("modrinth.index.json"))
        deps = index.get("dependencies", {})
        if (index.get("versionId") != version or index.get("game") != "minecraft"
                or deps.get("minecraft") != cfg["minecraft"]
                or deps.get(cfg["loader"]) != cfg["loader_version"]):
            raise ValueError("Source mrpack version or dependencies differ from snapshot")
    return pack.resolve()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    print(find_pack(args.root, args.snapshot))

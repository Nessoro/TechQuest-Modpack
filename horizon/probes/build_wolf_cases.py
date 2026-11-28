#!/usr/bin/env python3
"""Build source wolf tag memberships from a verified 1.21.1 bundle and local carry.

Uses original data only; native selector output is never used as the expectation.
Overlapping source memberships use the measured original live datapack
registry order, rather than the differing bootstrap order of the mask oracle.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

NAMES = ("pale", "spotted", "snowy", "black", "ashen", "rusty", "woods", "chestnut", "striped")
OUTER_SHA1 = "59353fb40c36d304f2035d51e7d6e6baa98dc05c"
INNER_SHA256 = "c301de10f575027d13eac18c7f34409d60648cf56a35d566aa1f530ff617840a"


def build(work: Path, server_jar: Path, live_priority: Path):
    live = json.loads(live_priority.read_text())
    priority = live["live_priority"]
    if (live.get("exit_code") != 0 or live.get("empty_membership_fallback") != "pale"
            or set(priority) != set(NAMES) or len(priority) != 9):
        raise ValueError("a completed original live priority probe is required")
    raw = server_jar.read_bytes()
    if hashlib.sha1(raw).hexdigest() != OUTER_SHA1:
        raise ValueError("expected official 1.21.1 server bundle")
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        inner = outer.read("META-INF/versions/1.21.1/server-1.21.1.jar")
    if hashlib.sha256(inner).hexdigest() != INNER_SHA256:
        raise ValueError("original inner server checksum differs")
    tags, biomes, hashes = {}, set(), {}
    def collect(name, raw, source):
        parts = Path(name).parts
        if len(parts) < 5 or parts[0] != "data" or not name.endswith(".json"):
            return
        if parts[2:5] == ("tags", "worldgen", "biome"):
            key = parts[1] + ":" + "/".join(parts[5:])[:-5]
            value = json.loads(raw)
            if value.get("replace", False):
                tags[key] = []
            tags.setdefault(key, []).extend(value["values"])
            hashes[source + "/" + name] = hashlib.sha256(raw).hexdigest()
        elif parts[2:4] == ("worldgen", "biome"):
            biomes.add(parts[1] + ":" + "/".join(parts[4:])[:-5])
    with zipfile.ZipFile(io.BytesIO(inner)) as original:
        for name in original.namelist():
            if name.startswith("data/") and name.endswith(".json"):
                collect(name, original.read(name), "vanilla")
    root = work / "mods/terralith"
    for section in ("carry", "outside"):
        for path in sorted((root / section / "data").rglob("*.json")):
            if path.is_symlink():
                raise ValueError("symlink in source")
            collect(path.relative_to(root / section).as_posix(), path.read_bytes(), section)
    def members(tag, pending=()):
        if tag in pending:
            raise ValueError("cycle in original biome tags")
        result = set()
        for entry in tags[tag]:
            required = True
            if isinstance(entry, dict):
                required, entry = entry.get("required", True), entry["id"]
            nested = entry.startswith("#")
            key = entry[1:] if nested else entry
            if ":" not in key:
                key = "minecraft:" + key
            if nested:
                if key not in tags and not required:
                    continue
                result.update(members(key, (*pending, tag)))
            else:
                if key not in biomes:
                    if required:
                        raise ValueError("unknown required original biome: " + key)
                    continue
                result.add(key)
        return result
    wolf_tags = {"c:has_wolf_variant/" + n: members("c:has_wolf_variant/" + n) for n in NAMES}
    cases, overlaps = [], []
    for biome in sorted(biomes):
        memberships = [tag for tag, values in wolf_tags.items() if biome in values]
        if len(memberships) > 1:
            overlaps.append(biome)
        variant = min((t.rsplit("/", 1)[1] for t in memberships), key=priority.index) if memberships else "pale"
        cases.append({"biome": biome, "tags": memberships,
                      "expected": "minecraft:" + variant})
    return {"schema": 1, "source_minecraft": "1.21.1", "server_inner_sha256": INNER_SHA256,
            "source_tag_sha256": hashes, "live_priority": priority,
            "overlapping_wolf_memberships": overlaps, "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--server-jar", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--live-priority", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("output must be new")
    args.output.write_text(json.dumps(build(args.work, args.server_jar, args.live_priority), indent=2) + "\n")

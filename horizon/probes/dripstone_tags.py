#!/usr/bin/env python3
"""Compare original vanilla + Terralith tag membership with effective Horizon tags."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("legacy-server-jar", "work", "content-root", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("output must be new")
    spec = importlib.util.spec_from_file_location(
        "adapter", Path(__file__).parents[1] / "tools/prepare_terralith_worldgen.py")
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    _, provenance = adapter.load_legacy_features(args.legacy_server_jar)
    with zipfile.ZipFile(args.legacy_server_jar) as bundle:
        inner = bundle.read("META-INF/versions/1.21.1/server-1.21.1.jar")
    names = ("dripstone_replaceable_blocks", "base_stone_overworld")
    old, current, source_hashes = {}, {}, {}
    with zipfile.ZipFile(io.BytesIO(inner)) as game:
        for name in names:
            relative = f"data/minecraft/tags/block/{name}.json"
            original = json.loads(game.read(relative))
            source = args.work / "mods/terralith/carry" / relative
            overrides = list((args.work / "mods").glob("**/" + relative))
            if {p.resolve() for p in overrides} != {source.resolve()}:
                raise ValueError("review other source tag overrides")
            extra = json.loads(source.read_text())
            if extra.get("replace") is not False or set(extra) != {"replace", "values"}:
                raise ValueError("expected the reviewed additive Terralith tag")
            old[name] = original["values"] + extra["values"]
            current[name] = json.loads((args.content_root / relative).read_text())["values"]
            source_hashes[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
    def resolve(tags, key, seen=()):
        if key in seen:
            raise ValueError("tag cycle")
        result = set()
        for value in tags[key]:
            if value.startswith("#minecraft:"):
                result.update(resolve(tags, value.removeprefix("#minecraft:"), (*seen, key)))
            elif value.startswith("minecraft:"):
                result.add(value)
            else:
                raise ValueError("unreviewed tag entry")
        return result
    expected = resolve(old, names[0])
    actual = resolve(current, names[0])
    if expected != actual:
        raise AssertionError({"missing": sorted(expected-actual), "extra": sorted(actual-expected)})
    report = {"schema": 1, "legacy_server_sha1": provenance["server_sha1"],
              "source_tag_sha256": source_hashes, "original_modded_members": len(expected),
              "effective_members": len(actual), "membership_equal": True,
              "includes_terralith_additions": True, "block_state_parity_claimed": False}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

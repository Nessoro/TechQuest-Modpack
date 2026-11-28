#!/usr/bin/env python3
"""Build developer-only noise-provider vectors, with synthetic block palettes."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

TYPES = {"noise_provider": "noise", "dual_noise_provider": "dual_noise",
         "noise_threshold_provider": "noise_threshold"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("work", "port-tool", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite probe vectors")
    found = {}
    def walk(value):
        if isinstance(value, dict):
            kind = str(value.get("type", "")).removeprefix("minecraft:")
            if kind in TYPES:
                found.setdefault(kind, value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    root = args.work / "mods/terralith/carry/data/terralith/worldgen/configured_feature"
    for path in sorted(root.rglob("*.json")):
        walk(json.loads(path.read_bytes()))
    if set(found) != set(TYPES):
        raise ValueError("three reviewed provider types required")
    converted = {}
    with tempfile.TemporaryDirectory(prefix="noise-probe-") as temporary:
        base = Path(temporary)
        raw = base / "input"
        raw.mkdir()
        (raw / "pack.mcmeta").write_text('{"pack":{"pack_format":48,"description":"probe"}}')
        for kind, provider in found.items():
            for field in ("noise", "slow_noise"):
                if field in provider:
                    path = raw / f"data/test/worldgen/noise/{kind}_{field}.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(provider[field]))
        subprocess.run([str(args.port_tool.resolve()), "upgrade-datapack", str(raw), str(base / "out")],
                       check=True, capture_output=True, text=True)
        for kind, provider in found.items():
            for field in ("noise", "slow_noise"):
                if field in provider:
                    converted[kind, field] = json.loads(
                        (base / f"out/data/test/worldgen/noise/{kind}_{field}.json").read_bytes())
    cases = []
    for kind, provider in found.items():
        for seed in (0, 263):
            legacy = {k: v for k, v in provider.items()
                      if k not in ("type", "states", "default_state", "low_states", "high_states")}
            legacy["seed"] = seed
            if kind == "noise_threshold_provider":
                legacy.update(default_state="minecraft:grass_block", low_states=["minecraft:stone"],
                              high_states=["minecraft:dirt", "minecraft:clay"])
            else:
                legacy["states"] = ["minecraft:stone", "minecraft:dirt", "minecraft:clay"]
            native = {**legacy, "type": "minecraft:" + TYPES[kind]}
            for field in ("noise", "slow_noise"):
                if field in legacy:
                    native[field] = converted[kind, field]
            for i in range(64):
                cases.append({"kind": kind, "legacy": legacy, "native": native,
                              "position": [(i * 37) % 511 - 255, (i * 17) % 257 - 64,
                                           (i * 67) % 1023 - 511], "random_seed": i * 1234567 + 89})
    args.output.write_text(json.dumps(cases) + "\n")
    print(f"Wrote {len(cases)} synthetic-palette probe cases")


if __name__ == "__main__":
    main()

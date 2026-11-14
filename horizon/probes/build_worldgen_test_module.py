#!/usr/bin/env python3
"""Make local command-test aliases for inline world-generation features.

The test-only seventh hmod contains derived local data, never game assets in
the repository. Outer placed-feature modifiers are intentionally not tested
by these configured-feature aliases. The six production modules stay intact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("datapack", "sdk", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--kind", choices=("roots", "legacy-patches"), default="roots")
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("output must be new")
    if args.datapack.resolve() in args.output.resolve().parents:
        raise ValueError("output must be separate from the source datapack")
    if any((p / "level.dat").exists() or (p / "horizon-resources.json").exists()
           for p in args.output.resolve().parents):
        raise ValueError("stage outside existing worlds and prepared resources")
    trial = json.loads((args.datapack / "techquest-worldgen-trial.json").read_text())
    if (trial.get("minecraft"), trial.get("terralith")) != ("26.3", "2.6.2"):
        raise ValueError("expected the reviewed Terralith trial")
    if args.kind == "roots":
        if trial.get("normalized_root_systems") != 2:
            raise ValueError("expected the reviewed two-root trial")
        module = "techquest_root_probe"
        aliases = {key: ("terralith", "cave/stone/" + key)
                   for key in ("granite_roots", "diorite_clearing")}
    else:
        if trial.get("inlined_legacy_feature_references") != 5:
            raise ValueError("expected the reviewed five inlined references")
        module = "techquest_legacy_probe"
        aliases = {"grass": ("minecraft", "patch_grass_forest"),
                   "brown": ("minecraft", "brown_mushroom_swamp"),
                   "red": ("minecraft", "red_mushroom_swamp"),
                   "pumpkin": ("terralith", "skylands/patch_pumpkin")}
    payloads = {}
    for key, (namespace, name) in aliases.items():
        source = args.datapack / f"data/{namespace}/worldgen/placed_feature/{name}.json"
        feature = json.loads(source.read_text())["feature"]
        if args.kind == "roots" and (feature.get("type") != "minecraft:root_system"
                or feature.get("level_test_distance") != 0
                or feature.get("max_level_deviation") != 0):
            raise ValueError("unexpected root configuration")
        if args.kind == "legacy-patches" and feature.get("type") != "minecraft:overlay":
            raise ValueError("expected a composed legacy patch")
        payloads[key] = feature
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".worldgen-command-probe-", dir=args.output.parent) as tmp:
        content = Path(tmp) / "content"
        content.mkdir()
        name = "TechQuest root command probe" if args.kind == "roots" else "TechQuest legacy patch command probe"
        description = ("Local test aliases for two inline Terralith features." if args.kind == "roots"
                       else "Local test aliases for four inline legacy patches.")
        (content / "horizon-mod.toml").write_text(
            f'id="{module}"\nname="{name}"\nversion="0.1.0"\n'
            f'description="{description}"\n'
            'api="0.2"\nside="both"\ncapabilities=["registries"]\n')
        for key, feature in payloads.items():
            path = content / f"data/{module}/worldgen/feature/{key}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(feature, indent=2) + "\n")
        subprocess.run([str(args.sdk.resolve()), "build"], cwd=content,
                       check=True, capture_output=True, text=True, timeout=180)
        package = content / f"target/horizon-mod/{module}.hmod"
        verdict = json.loads(subprocess.run([str(args.sdk.resolve()), "check", str(package), "--json"],
            cwd=content, check=True, capture_output=True, text=True, timeout=180).stdout)
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        if (not verdict.get("ok") or verdict.get("report", {}).get("id") != module
                or verdict["report"].get("sha256") != digest):
            raise ValueError("SDK rejected the test module")
        report = {"schema": 1, "test_only": True, "id": module, "kind": args.kind,
                  "sdk_validated": True, "sha256": digest,
                  "source_files_modified": False, "outer_placed_modifiers_tested": False,
                  "aliases": list(payloads), "server_boot_tested": False}
        (content / "techquest-worldgen-command-probe.json").write_text(json.dumps(report, indent=2) + "\n")
        content.rename(args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

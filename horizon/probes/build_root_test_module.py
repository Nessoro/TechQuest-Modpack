#!/usr/bin/env python3
"""Make local command-test aliases for two inline Terralith root systems.

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
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("output must be new")
    if args.datapack.resolve() in args.output.resolve().parents:
        raise ValueError("output must be separate from the source datapack")
    if any((p / "level.dat").exists() or (p / "horizon-resources.json").exists()
           for p in args.output.resolve().parents):
        raise ValueError("stage outside existing worlds and prepared resources")
    trial = json.loads((args.datapack / "techquest-worldgen-trial.json").read_text())
    if (trial.get("minecraft"), trial.get("terralith"), trial.get("normalized_root_systems")) != (
            "26.3", "2.6.2", 2):
        raise ValueError("expected the reviewed two-root trial")
    payloads = {}
    for key in ("granite_roots", "diorite_clearing"):
        source = args.datapack / f"data/terralith/worldgen/placed_feature/cave/stone/{key}.json"
        feature = json.loads(source.read_text())["feature"]
        if (feature.get("type") != "minecraft:root_system"
                or feature.get("level_test_distance") != 0
                or feature.get("max_level_deviation") != 0):
            raise ValueError("unexpected root configuration")
        payloads[key] = feature
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".root-command-probe-", dir=args.output.parent) as tmp:
        content = Path(tmp) / "content"
        content.mkdir()
        (content / "horizon-mod.toml").write_text(
            'id="techquest_root_probe"\nname="TechQuest root command probe"\nversion="0.1.0"\n'
            'description="Local test aliases for two inline Terralith features."\n'
            'api="0.2"\nside="both"\ncapabilities=["registries"]\n')
        for key, feature in payloads.items():
            path = content / f"data/techquest_root_probe/worldgen/feature/{key}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(feature, indent=2) + "\n")
        subprocess.run([str(args.sdk.resolve()), "build"], cwd=content,
                       check=True, capture_output=True, text=True, timeout=180)
        package = content / "target/horizon-mod/techquest_root_probe.hmod"
        verdict = json.loads(subprocess.run([str(args.sdk.resolve()), "check", str(package), "--json"],
            cwd=content, check=True, capture_output=True, text=True, timeout=180).stdout)
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        if (not verdict.get("ok") or verdict.get("report", {}).get("id") != "techquest_root_probe"
                or verdict["report"].get("sha256") != digest):
            raise ValueError("SDK rejected the test module")
        report = {"schema": 1, "test_only": True, "id": "techquest_root_probe",
                  "sdk_validated": True, "sha256": digest,
                  "source_files_modified": False, "outer_placed_modifiers_tested": False,
                  "aliases": list(payloads), "server_boot_tested": False}
        (content / "techquest-root-command-probe.json").write_text(json.dumps(report, indent=2) + "\n")
        content.rename(args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

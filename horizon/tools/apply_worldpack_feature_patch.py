#!/usr/bin/env python3
"""Apply the reviewed Rust world-pack feature correction after the base fix.

Only generated Mixins stages at the exact pinned hashes are accepted. Input
validation precedes writes; a completed application is a read-only no-op.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from apply_biome_modifier_patch import PATCH as BASE_PATCH, apply as apply_base

PATCH = Path(__file__).resolve().parents[1] / "first_party/biome_world_packs"


def apply(workspace):
    if workspace.is_symlink() or any(p.is_symlink() for p in workspace.absolute().parents):
        raise ValueError("stage path contains a symlink")
    marker = workspace / ".horizon-mixins-stage.json"
    if not marker.is_file() or (workspace / ".git").exists():
        raise ValueError("only a generated Mixins stage may be patched")
    inputs = json.loads(marker.read_text())["inputs"]
    spec = json.loads((PATCH / "horizon-core-patch.json").read_text())
    base = json.loads((BASE_PATCH / "horizon-core-patch.json").read_text())
    sha = lambda b: hashlib.sha256(b).hexdigest()
    patch = PATCH / spec["patch_file"]
    module = PATCH / spec["module_file"]
    if sha(patch.read_bytes()) != spec["patch_sha256"] or sha(module.read_bytes()) != spec["module_sha256"]:
        raise ValueError("reviewed world-pack correction changed")
    targets = [workspace / source["path"] for source in spec["sources"]]
    module_target = workspace / spec["module_target"]
    for target in [*targets, module_target]:
        if target.is_symlink() or any(p.is_symlink() for p in target.parents):
            raise ValueError("source path contains a symlink")
    for source in spec["sources"]:
        expected_input = base["source_sha256"] if source["path"] == base["source_file"] else source["source_sha256"]
        if inputs.get(source["path"]) != expected_input:
            raise ValueError("stage input does not match reviewed pin")
    if module_target.exists() and sha(module_target.read_bytes()) != spec["module_sha256"]:
        raise ValueError("existing module differs from reviewed source")
    if all(sha(target.read_bytes()) == source["patched_sha256"] for target, source in zip(targets, spec["sources"])) and module_target.is_file():
        return {**spec, "changed": False}
    for target, source in zip(targets, spec["sources"]):
        allowed = {source["source_sha256"]}
        if source["path"] == base["source_file"]: allowed.add(base["source_sha256"])
        if sha(target.read_bytes()) not in allowed:
            raise ValueError("source differs from reviewed world-pack pin")
    apply_base(workspace)
    subprocess.run(["git", "apply", "--check", str(patch.resolve())], cwd=workspace, check=True, capture_output=True, text=True)
    subprocess.run(["git", "apply", str(patch.resolve())], cwd=workspace, check=True, capture_output=True, text=True)
    if not module_target.exists():
        with module_target.open("xb") as f: f.write(module.read_bytes())
    for target, source in zip(targets, spec["sources"]):
        if sha(target.read_bytes()) != source["patched_sha256"]:
            raise ValueError("applied source differs from reviewed result")
    return {**spec, "changed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    print(json.dumps(apply(parser.parse_args().workspace), indent=2))


if __name__ == "__main__": main()

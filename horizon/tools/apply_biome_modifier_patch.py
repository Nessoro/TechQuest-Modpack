#!/usr/bin/env python3
"""Apply the reviewed MIT core correction to a generated pinned Mixins stage.

Does not modify the upstream checkout or prepared resources. Pin and exact diff
are checked before an atomic write. Reapplying the exact patch is a read-only
no-op; a different source revision is refused.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import tempfile

PATCH = Path(__file__).resolve().parents[1] / "first_party/biome_modifiers"


def apply(workspace):
    if workspace.is_symlink() or any(p.is_symlink() for p in workspace.absolute().parents):
        raise ValueError("stage path contains a symlink")
    marker = workspace / ".horizon-mixins-stage.json"
    spec = json.loads((PATCH / "horizon-core-patch.json").read_text())
    sha = lambda b: hashlib.sha256(b).hexdigest()
    if not marker.is_file() or (workspace / ".git").exists():
        raise ValueError("only a generated Mixins stage may be patched")
    if json.loads(marker.read_text())["inputs"].get(spec["source_file"]) != spec["source_sha256"]:
        raise ValueError("stage input does not match the reviewed source pin")
    target = workspace / spec["source_file"]
    if target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise ValueError("source path contains a symlink")
    raw = target.read_bytes(); before = sha(raw)
    patch = (PATCH / "merged-biomes.patch").read_bytes()
    if sha(patch) != spec["patch_sha256"]:
        raise ValueError("reviewed patch changed")
    if before == spec["patched_sha256"]:
        return {**spec, "changed": False}
    if before != spec["source_sha256"]:
        raise ValueError("source file differs from reviewed pin")
    source = raw.decode()
    modified = source.replace('const WORLDGEN_BUNDLES: [(&str, &str); 7] = [', 'const WORLDGEN_BUNDLES: [(&str, &str); 8] = [\n    ("biome", "worldgen/biomes.json"),', 1)
    modified = modified.replace("let mut doc = read_json(&base.join(BIOMES))?;", "let mut doc = read_json(&out_path(overlay, BIOMES))?;", 1)
    modified = modified.replace("let known = Known::new(base, &plan, &tags)?;", "let mut known = Known::new(base, &plan, &tags)?;\n    if let Some(entries) = worldgen.get(BIOMES) {\n        let biome_ids = entries.iter().map(|(id, _)| id.clone());\n        known.biomes.extend(biome_ids);\n    }", 1)
    modified = modified.replace('/// mods hold. Biomes, noise and density functions change the terrain and\n/// are not read from mods.', '/// mods hold. Biomes join the registry before tag filtering and modifiers;\n/// noise and density functions are still supplied through world datapacks.', 1)
    diff = "".join(difflib.unified_diff(source.splitlines(True), modified.splitlines(True), fromfile="a/"+spec["source_file"], tofile="b/"+spec["source_file"]))
    if sha(modified.encode()) != spec["patched_sha256"] or diff.encode() != patch:
        raise ValueError("computed correction differs from reviewed patch")
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as f:
        temporary = Path(f.name); f.write(modified.encode())
    try:
        temporary.chmod(target.stat().st_mode & 0o777); os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {**spec, "changed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--workspace", type=Path, required=True)
    print(json.dumps(apply(parser.parse_args().workspace), indent=2))


if __name__ == "__main__": main()

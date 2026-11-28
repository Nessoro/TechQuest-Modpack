#!/usr/bin/env python3
"""Extract modifier cases from pinned public JSON; output only to new scratch paths."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from stage_terralith_content import read_checked
from stage_yung_dungeons import SOURCE_SHA1


def cases(jar, module):
    original_bytes, module_bytes = read_checked(jar), read_checked(module)
    if hashlib.sha1(original_bytes).hexdigest() != SOURCE_SHA1:
        raise ValueError("expected the pinned original Better Dungeons JAR")
    rows = []
    with zipfile.ZipFile(io.BytesIO(original_bytes)) as original, zipfile.ZipFile(io.BytesIO(module_bytes)) as carried:
        def visit(value, target, path, name):
            if isinstance(value, list):
                for i, v in enumerate(value):
                    visit(v, target[i], path + [i], name)
            elif isinstance(value, dict):
                functions = value.get("functions", [])
                if value.get("type") == "minecraft:item" and any(
                    (f.get("function") == "minecraft:enchant_randomly"
                     and isinstance(f.get("options"), list)
                     and any(":" not in s for s in f["options"]))
                    or (f.get("function") == "minecraft:set_components"
                        and "potion_contents" in f.get("components", {})) for f in functions):
                    rows.append({"name": f"case_{len(rows)}", "source_file": name,
                                 "source_path": path, "source_entry": value,
                                 "native_table": {"type": "minecraft:chest", "pools": [
                                     {"rolls": 1, "entries": [target]}]}})
                    return
                for k, v in value.items():
                    translated = {"functions": "modifier", "function": "type", "conditions": "condition"}.get(k, k)
                    if k not in ("functions", "conditions"):
                        visit(v, target[translated], path + [k], name)
        for name in sorted(original.namelist()):
            if name.startswith("data/betterdungeons/loot_table/") and name.endswith(".json"):
                visit(json.loads(original.read(name)), json.loads(carried.read(name)), [], name)
    if len(rows) != 23:
        raise ValueError("expected 23 source modifier entries")
    return {"schema": 1, "source_jar_sha1": SOURCE_SHA1,
            "module_sha256": hashlib.sha256(module_bytes).hexdigest(),
            "seeds": [1, 263, 987654321], "cases": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("jar", "module", "output"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or any(p.is_symlink() for p in args.output.parents):
        raise ValueError("output must be a new regular scratch path")
    result = cases(args.jar, args.module)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"extracted {len(result['cases'])} cases, three seeds each")

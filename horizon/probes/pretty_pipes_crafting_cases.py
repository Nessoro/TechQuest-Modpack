#!/usr/bin/env python3
"""Generate developer crafting inputs from the pinned original public JSON."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from stage_pretty_pipes import SOURCE, RECIPE_NAMES, glass_members
from stage_terralith_content import read_checked


def generate(jar, neoforge_jar):
    raw = read_checked(jar)
    checksum = hashlib.sha512(raw).hexdigest()
    if checksum != json.loads(read_checked(SOURCE))["modrinth_lock"]["XExdLWCQ"]["sha512"]:
        raise ValueError("expected pinned original Pretty Pipes JAR")
    glass, _ = glass_members(read_checked(neoforge_jar))
    cases = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name in RECIPE_NAMES:
            recipe = json.loads(archive.read(f"data/prettypipes/recipe/{name}.json"))
            for variant in glass if name == "pipe" else [None]:
                grid = []
                for row in recipe["pattern"]:
                    for symbol in row:
                        ingredient = recipe["key"].get(symbol)
                        grid.append(None if ingredient is None else ingredient.get("item", variant))
                if len(grid) != 9:
                    raise ValueError("unexpected original grid size")
                title = name + (":" + variant if variant else "")
                case = {"name": title, "recipe": "prettypipes:" + name,
                        "item": recipe["result"]["id"], "count": recipe["result"].get("count", 1),
                        "valid": True, "grid": grid}
                cases.append(case)
                slot = next(i for i, item in enumerate(grid) if item is not None)
                for mutation, value in (("missing", None), ("wrong", "minecraft:dirt")):
                    bad = grid.copy()
                    bad[slot] = value
                    cases.append({**case, "name": title + ":" + mutation, "grid": bad, "valid": False})
    return {"schema": 1, "source_jar_sha512": checksum, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("jar", "neoforge-jar", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.jar, args.neoforge_jar)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print("Generated", len(result["cases"]), "original crafting inputs")


if __name__ == "__main__":
    main()

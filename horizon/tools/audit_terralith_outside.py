#!/usr/bin/env python3
"""Classify every Terralith file excluded from the local worldgen adaptation.

Read-only: records hashes and concrete outstanding behavior, never copies source
data into the repository or marks an unimplemented behavior as ported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from prepare_terralith_worldgen import selected
from server_preflight import UPSTREAM

RECIPES = ("dispenser", "dropper", "lever", "observer", "piston")
WOLVES = ("ashen", "black", "chestnut", "pale", "rusty", "snowy", "spotted", "striped", "woods")
EVIDENCE = ("crates/horizon-client/src/mobs/tame.rs",
            "crates/horizon-client/src/advancements.rs",
            "crates/horizon-client/src/game/machines/crafter.rs")


def read(path: Path) -> bytes:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("symlink in audit input")
    return path.read_bytes()


def audit(work: Path, resources: Path, upstream: Path) -> dict:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=upstream, check=True,
                          capture_output=True, text=True).stdout.strip()
    if head != UPSTREAM:
        raise ValueError("review evidence against the new upstream first")
    subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", *EVIDENCE], cwd=upstream,
                   check=True, capture_output=True)
    outside = work / "mods/terralith/outside"
    carry = work / "mods/terralith/carry"
    remaining = {p.relative_to(outside).as_posix(): p for p in (outside / "data").rglob("*")
                 if p.is_file() and not selected(p.relative_to(outside))}
    expected = {f"data/minecraft/advancement/recipes/redstone/{name}.json" for name in RECIPES}
    expected |= {f"data/minecraft/wolf_variant/{name}.json" for name in WOLVES}
    expected.add("data/minecraft/dimension/funny_cave_meme.txt")
    if remaining.keys() != expected:
        raise ValueError("outside inventory changed; classify all additions/removals before continuing")
    files = []
    for name, path in sorted(remaining.items()):
        raw = read(path)
        record = {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}
        if "/advancement/" in name:
            old, new = json.loads(raw), json.loads(read(resources / name))
            recipe = "minecraft:" + path.stem
            custom = "terralith:" + path.stem + "_alt"
            if (old["rewards"]["recipes"] != [recipe, custom]
                    or new["rewards"]["recipes"] != [recipe]
                    or old["criteria"]["has_the_recipe"]["conditions"] != {"recipe": recipe}
                    or new["criteria"]["has_the_recipe"]["conditions"] != {"recipes": recipe}):
                raise ValueError("review a changed recipe advancement")
            custom_file = carry / f"data/terralith/recipe/{path.stem}_alt.json"
            record.update(classification="recipe_unlock_pending", custom_recipe=custom,
                          carried_recipe_sha256=hashlib.sha256(read(custom_file)).hexdigest(),
                          migration_needed="recipe_unlocked.conditions.recipe -> recipes; preserve both rewards",
                          behavior_missing="automatic unlock of the alternate recipe from this advancement",
                          runtime_verified=False)
        elif "/wolf_variant/" in name:
            old, new = json.loads(raw), json.loads(read(resources / name))
            if set(old) != {"angry_texture", "tame_texture", "wild_texture", "biomes"}:
                raise ValueError("review changed wolf definition")
            assets = {key: old[key + "_texture"] for key in ("angry", "tame", "wild")}
            tag = "c:has_wolf_variant/" + path.stem
            if old["biomes"] != "#" + tag or new["assets"] != assets:
                raise ValueError("review changed wolf assets/selector")
            tag_file = carry / f"data/c/tags/worldgen/biome/has_wolf_variant/{path.stem}.json"
            record.update(classification="native_wolf_selector_pending", biome_tag=tag,
                          carried_tag_sha256=hashlib.sha256(read(tag_file)).hexdigest(),
                          adult_textures_match_current_vanilla=True,
                          migration_needed="assets/spawn_conditions plus native data-driven variant selection",
                          behavior_missing="Terralith's c:has_wolf_variant biome selection",
                          runtime_verified=False)
        else:
            record.update(classification="non_runtime_author_notes", runtime_required=False,
                          reason=".txt climate-point snippets; not a dimension registry .json file")
        files.append(record)
    return {"schema": 1, "minecraft": "26.3", "terralith": "2.6.2", "upstream_commit": UPSTREAM,
            "outside_files_reviewed": len(files), "unclassified": [],
            "recipe_unlock_pending": 5, "native_wolf_selector_pending": 9, "non_runtime_author_notes": 1,
            "evidence_sha256": {name: hashlib.sha256(read(upstream / name)).hexdigest() for name in EVIDENCE},
            "native_wolf_selector": "wolf_variant_for has fixed vanilla biome/tag branches; c tags are not consulted",
            "recipe_unlock_selector": "native advancement index and matcher read conditions.recipes",
            "files": files, "source_files_modified": False, "complete_terralith_port": False,
            "client_tested": False, "multiplayer_tested": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("work", "resources", "upstream"):
        parser.add_argument("--" + name, required=True, type=Path)
    print(json.dumps(audit(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()

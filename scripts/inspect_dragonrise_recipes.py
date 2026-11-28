#!/usr/bin/env python3
"""Read-only evidence collector for DragonRise crafting integration.

Static resource paths and translation keys are evidence, not registry entries.
An optional runtime registry report provides actual registered IDs, but does
not by itself establish creative-tab membership or survival obtainability.
No game code is loaded; no recipes are generated.
"""
import argparse
import hashlib
import json
import re
import tomllib
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DR_FILENAME = "dragonrise_reforge-1.5.1-release.jar"
SBW_FILENAME = "superbwarfare-0.8.9.2-mc1.21.1-c22d98c2.jar"
MAX_JSON = 16 * 1024 * 1024
ID = re.compile(r"[a-z0-9_.-]+:[a-z0-9/._-]+")


def digest(path, algorithm):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def read_json(jar, name):
    if jar.getinfo(name).file_size > MAX_JSON:
        raise ValueError("JSON resource too large: " + name)
    return json.loads(jar.read(name).decode("utf-8-sig"))


def scan_jar(path, expected_name, expected_sha512=None):
    if path.name != expected_name:
        raise ValueError("Expected original filename: " + expected_name)
    sha512 = digest(path, "sha512")
    if expected_sha512 and sha512 != expected_sha512:
        raise ValueError("SHA-512 mismatch: " + path.name)
    with zipfile.ZipFile(path) as jar:
        names = sorted(x.filename for x in jar.infolist() if not x.is_dir())
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive paths: " + path.name)
        metadata = "META-INF/neoforge.mods.toml"
        if metadata not in names:
            raise ValueError("Missing NeoForge metadata: " + path.name)
        if jar.getinfo(metadata).file_size > MAX_JSON:
            raise ValueError("Oversized mod metadata")
        mod_info = tomllib.loads(jar.read(metadata).decode("utf-8"))
        mod_ids = sorted({m["modId"] for m in mod_info.get("mods", [])})
        if not mod_ids:
            raise ValueError("No mod IDs in metadata: " + path.name)
        if not any(n.endswith(".class") for n in names):
            raise ValueError("No compiled classes: " + path.name)
        recipes, tags, languages, data_paths, classes, asset_paths = [], [], [], [], [], []
        for name in names:
            parts = name.split("/")
            if name.endswith(".class"):
                classes.append(name)
            if len(parts) < 4 or not name.endswith(".json"):
                continue
            root, ns, folder = parts[:3]
            if root == "assets":
                asset_paths.append(name)
                if folder == "lang":
                    lang = read_json(jar, name)
                    if not isinstance(lang, dict):
                        raise ValueError("Invalid localization: " + name)
                    # Preserve translation keys only: these do not establish IDs.
                    languages.append({"path": name, "keys": sorted(lang)})
            if root != "data":
                continue
            data_paths.append(name)
            if folder in ("recipe", "recipes"):
                obj = read_json(jar, name)
                if not isinstance(obj, dict):
                    raise ValueError("Invalid recipe object: " + name)
                recipes.append({
                    "path": name,
                    "recipe_id_candidate": ns + ":" + "/".join(parts[3:])[:-5],
                    "serializer": obj.get("type"),
                    "fields": {k: type(v).__name__ for k, v in sorted(obj.items())},
                    "result_fields": {
                        k: obj[k] for k in ("result", "output", "results")
                        if k in obj
                    },
                })
            elif folder == "tags":
                obj = read_json(jar, name)
                if not isinstance(obj, dict):
                    raise ValueError("Invalid tag object: " + name)
                tags.append({"path": name, "values": obj.get("values", [])})
        return {
            "filename": path.name,
            "sha256": digest(path, "sha256"),
            "sha512": sha512,
            "independent_sha512_verified": bool(expected_sha512),
            "mod_ids_from_metadata": mod_ids,
            "declared_versions": {m["modId"]: m.get("version") for m in mod_info.get("mods", [])},
            "dependencies": mod_info.get("dependencies", {}),
            "recipes": recipes,
            "serializer_counts": dict(Counter(str(r["serializer"]) for r in recipes)),
            "tags": tags,
            "localization": languages,
            "data_json_paths": data_paths,
            "asset_json_paths": asset_paths,
            "class_paths": classes,
            "nested_jar_paths": [n for n in names if n.endswith(".jar")],
        }


def registry_ids(report, registry):
    entry = report.get(registry)
    if not isinstance(entry, dict) or not isinstance(entry.get("entries"), dict):
        raise ValueError("Missing registry entries: " + registry)
    ids = sorted(entry["entries"])
    if any(not ID.fullmatch(i) for i in ids):
        raise ValueError("Invalid registry ID in " + registry)
    return ids


def runtime_evidence(path, mod_ids):
    report = json.loads(path.read_text(encoding="utf-8"))
    namespaces = set(mod_ids)
    registries = {}
    for reg in ("minecraft:item", "minecraft:block", "minecraft:entity_type", "minecraft:creative_mode_tab", "minecraft:recipe_serializer"):
        # Some reports do not include every registry. Record unknown explicitly.
        registries[reg] = (
            [i for i in registry_ids(report, reg) if i.split(":", 1)[0] in namespaces]
            if reg in report else None
        )
    if registries["minecraft:item"] is None or registries["minecraft:block"] is None:
        raise ValueError("Runtime report must include item and block registries")
    if not registries["minecraft:item"]:
        raise ValueError("No DragonRise namespace items in runtime report")
    items = [{"registry_id": i, "display_name": None, "category": None,
              "original_recipe": None, "proposed_crafting_method": None,
              "progression_tier": None, "implementation_status": "unreviewed",
              "player_facing": None}
             for i in registries["minecraft:item"]]
    return {"registry_report_sha256": digest(path, "sha256"),
            "namespace_filter": sorted(namespaces), "registries": registries,
            "registered_item_inventory": items}


def audit(dr_path, sbw_path, registry_path=None):
    cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
    locked = cfg["modrinth_lock"]["Cd3DYqzn"]
    if locked["filename"] != SBW_FILENAME or locked["version"] != "0.8.9.2":
        raise ValueError("Superb Warfare lock changed; re-review audit target")
    dr = scan_jar(dr_path, DR_FILENAME)
    sbw = scan_jar(sbw_path, SBW_FILENAME, locked["sha512"])
    return {
        "schema_version": 1,
        "status": "incomplete_review_required",
        "dragonrise": dr, "superb_warfare": sbw,
        "runtime_evidence": runtime_evidence(registry_path, dr["mod_ids_from_metadata"]) if registry_path else None,
        "coverage": {"player_facing_total": None, "original_recipes": None,
                     "new_techquest_recipes": None, "missing_recipes": None,
                     "justified_exclusions": None, "percentage": None},
        "limitations": [
            "DragonRise hash is a local fingerprint, not independent authenticity verification.",
            "Static resources do not prove item registration, creative tabs, or obtainability.",
            "Namespace filtering does not detect registrations made under another namespace.",
            "Nested JARs are listed, not recursively audited.",
            "Recipe field names and declared serializers are not proof of runtime codec compatibility.",
            "Coverage remains unknown until registry, tabs, crafting paths and exclusions are reviewed."
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dragonrise", type=Path, required=True)
    parser.add_argument("--superb-warfare", type=Path, required=True)
    parser.add_argument("--registries", type=Path, help="Optional runtime registries.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.dragonrise, args.superb_warfare, args.registries)
    if args.output.resolve() in {args.dragonrise.resolve(), args.superb_warfare.resolve()} or args.output.suffix != ".json":
        parser.error("Output must be a separate JSON file")
    if args.registries and args.output.resolve() == args.registries.resolve():
        parser.error("Output must not overwrite runtime registry evidence")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Static evidence written:", args.output)
    print("Crafting coverage: UNKNOWN (not a release acceptance result)")


if __name__ == "__main__":
    main()

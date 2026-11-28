#!/usr/bin/env python3
"""Opt-in disposable server test, launched only after explicit EULA acceptance."""
import argparse
from collections import Counter
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "compat/dragonrise_inventory.json"
PREFIX = ROOT / "compat/techquest-compat/data/techquest/recipe"
JAR = "dragonrise_reforge-1.5.1-release.jar"


def expected_recipes():
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    rows = {}
    for row in inv["entries"]:
        rid = row.get("recipe_id")
        if not rid:
            continue
        recipe = json.loads((PREFIX / (rid.split(":", 1)[1] + ".json")).read_text(encoding="utf-8"))
        if "inputs" in recipe:
            ingredients = Counter()
            for value in recipe["inputs"]:
                match = re.fullmatch(r"(?:(\d+) )?([a-z0-9_.-]+:[a-z0-9_./-]+)", value)
                if match is None:
                    raise ValueError("Invalid assembly ingredient: " + value)
                ingredients[match[2]] += int(match[1] or 1)
        elif "key" in recipe:
            ingredients = Counter(recipe["key"][symbol]["item"] for line in recipe["pattern"] for symbol in line if symbol != " ")
        else:
            ingredients = Counter(v["item"] for v in recipe["ingredients"])
        if rid in rows:
            raise ValueError("Duplicate recipe: " + rid)
        rows[rid] = {"kind": row["kind"], "target": row["registry_id"], "serializer": recipe["type"], "ingredients": dict(sorted(ingredients.items())), "count": recipe["result"].get("count", 1)}
    if not rows:
        raise ValueError("Empty recipe inventory")
    return rows


def validate_report(report, present, expected):
    if report["dragonrise_present"] != present or report["expected"] != len(expected):
        raise ValueError("Unexpected observer configuration")
    if report["errors"]:
        raise ValueError("Observer errors: " + str(report["errors"]))
    if report["loaded"] != (len(expected) if present else 0):
        raise ValueError("Incorrect loaded count")
    if set(report["observations"]) != (set(expected) if present else set()):
        raise ValueError("Observed recipe IDs differ from inventory")
    if not report["original_sbw_recipe_ids"]:
        raise ValueError("Missing original SBW recipes")


def boot(server, reports, label, present, expected):
    dest = reports / (label + ".json")
    log = reports / (label + ".log")
    dest.unlink(missing_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(["bash", "run.sh", "nogui"], cwd=server,
            stdin=subprocess.PIPE, stdout=stream, stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                if dest.exists():
                    try:
                        report = json.loads(dest.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        time.sleep(1)
                        continue
                    validate_report(report, present, expected)
                    break
                if process.poll() is not None:
                    raise RuntimeError("Server exited before observer: " + label)
                time.sleep(2)
            else:
                raise TimeoutError("Server observer timed out: " + label)
        finally:
            if process.poll() is None:
                try:
                    process.stdin.write("stop\n")
                    process.stdin.flush()
                    process.wait(timeout=120)
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
                    process.wait(timeout=30)
    if process.returncode != 0:
        raise RuntimeError("Server did not stop cleanly: " + label)
    if re.search(r"(?:Parsing error loading recipe|Couldn't parse recipe).*techquest:dragonrise/", log.read_text(encoding="utf-8", errors="replace")):
        raise RuntimeError("DragonRise recipe decoding errors: " + label)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--dragonrise", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--accept-minecraft-eula", action="store_true", required=True)
    args = parser.parse_args()
    server, reports = args.server.resolve(), args.reports.resolve()
    reports.mkdir(parents=True, exist_ok=True)
    expected = expected_recipes()
    expected_path = reports / "expected.json"
    expected_path.write_text(json.dumps(expected, indent=2), encoding="utf-8")
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if args.dragonrise.name != JAR or hashlib.sha256(args.dragonrise.read_bytes()).hexdigest() != inv["source"]["dragonrise_sha256"]:
        raise ValueError("DragonRise differs from audited original")
    if (server / "mods" / JAR).exists() or (server / "world").exists():
        raise ValueError("Expected fresh disposable server")
    (server / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    jvm = server / "user_jvm_args.txt"
    original = jvm.read_text(encoding="utf-8")
    results = {}
    for label, present in (("absent", False), ("present_existing_world", True), ("present_restart", True)):
        if present and not (server / "mods" / JAR).exists():
            shutil.copyfile(args.dragonrise, server / "mods" / JAR)
        jvm.write_text(original + "\n-Xms2G\n-Xmx5G\n"
            + "-Dtechquest.dragonrise.expected=" + str(expected_path) + "\n"
            + "-Dtechquest.dragonrise.report=" + str(reports / (label + ".json")) + "\n"
            + "-Dtechquest.dragonrise.present=" + str(present).lower() + "\n", encoding="utf-8")
        results[label] = boot(server, reports, label, present, expected)
    before = set(results["absent"]["original_sbw_recipe_ids"])
    for label in ("present_existing_world", "present_restart"):
        if not before <= set(results[label]["original_sbw_recipe_ids"]):
            raise ValueError("Original SBW recipes disappeared: " + label)
    print("All real server recipe loading phases passed; crafting and JEI remain unverified.")


if __name__ == "__main__":
    main()

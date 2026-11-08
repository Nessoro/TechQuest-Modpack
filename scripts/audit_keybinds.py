#!/usr/bin/env python3
"""Static constructor audit, not a substitute for live key/context testing."""
import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack


def default_key(row):
    code = row.get("code")
    if code is None:
        return None
    if code == -1:
        return "key.keyboard.unknown"
    if row.get("input") == "MOUSE":
        return {0: "key.mouse.left", 1: "key.mouse.right", 2: "key.mouse.middle"}.get(code)
    if row.get("input") not in (None, "KEYSYM"):
        return None
    if 65 <= code <= 90:
        return "key.keyboard." + chr(code).lower()
    if 48 <= code <= 57:
        return "key.keyboard." + chr(code)
    if 290 <= code <= 314:
        return "key.keyboard.f" + str(code - 289)
    names = {32: "space", 256: "escape", 257: "enter", 258: "tab", 259: "backspace",
             260: "insert", 261: "delete", 266: "page.up", 267: "page.down", 268: "home",
             269: "end", 280: "caps.lock", 340: "left.shift", 341: "left.control",
             342: "left.alt", 344: "right.shift", 345: "right.control", 346: "right.alt"}
    return "key.keyboard." + names[code] if code in names else None


def analyze(rows, overrides):
    bindings = []
    groups = defaultdict(dict)
    for original in rows:
        row = dict(original)
        row["default_key"] = default_key(row)
        row["default_modifier"] = row.get("modifier") or "NONE"
        if row["id"] in overrides:
            key, _, modifier = overrides[row["id"]].partition(":")
            row["effective_key"] = key
            row["modifier"] = modifier or "NONE"
        else:
            row["effective_key"] = row["default_key"]
        # Keep unresolved descriptions/codes visible; never pretend they are unbound.
        row["resolved"] = row["id"] is not None and row["effective_key"] is not None
        bindings.append(row)
        key = row["effective_key"]
        if row["resolved"] and key != "key.keyboard.unknown":
            group = (key, row.get("modifier") or "NONE")
            groups[group].setdefault(row["id"], row)
    collisions = [{"key": key, "modifier": modifier, "bindings": list(items.values()),
                   "requires_runtime_context_review": True}
                  for (key, modifier), items in sorted(groups.items()) if len(items) > 1]
    return {"scope": "Static KeyMapping constructors only. Custom hotkey systems, runtime registrations, "
                     "modifier interactions and actual device input require game tests.",
            "runtime_verified": False, "constructors": len(rows),
            "resolved": sum(b["resolved"] for b in bindings), "bindings": bindings,
            "possible_collisions": collisions}


def verify_zoom(report):
    found = {b["id"]: b for b in report["bindings"] if b["id"]}
    expected = {"key.betterzoom.zoom": "key.keyboard.z", "key.tacz.refit.desc": "key.keyboard.f8",
                "gui.xaero_enlarge_map": "key.keyboard.f9",
                "key.sophisticatedbackpacks.toggle_upgrade_1": "key.keyboard.f10"}
    for name, key in expected.items():
        if name not in found or found[name]["effective_key"] != key:
            raise ValueError("Zoom key plan does not match actual JAR bindings: " + name)
    for name, key in expected.items():
        users = {b["id"] for b in report["bindings"] if b["resolved"] and b["effective_key"] == key}
        if users != {name}:
            raise ValueError("Other observed bindings use reserved key " + key + ": " + str(users))
    for code, name in ((90, "key.betterzoom.zoom"), (297, "key.tacz.refit.desc"),
                       (298, "gui.xaero_enlarge_map"), (299, "key.sophisticatedbackpacks.toggle_upgrade_1")):
        if any(b["id"] is None and b["code"] == code for b in report["bindings"]):
            raise ValueError("Unresolved constructor may conflict with " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mods", type=Path, default=ROOT / "output/client/mods")
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    plan = json.loads((ROOT / "windows-installer/assets/neoforge-21.1.264-bootstrap.json").read_text())
    asm = next(f for f in plan["libraries"] if f["path"] == "org/ow2/asm/asm/9.10.1/asm-9.10.1.jar")
    tools = args.out / "audit-tools"
    tools.mkdir(parents=True, exist_ok=True)
    library = tools / "asm-9.10.1.jar"
    if not library.exists() or __import__("hashlib").sha1(library.read_bytes()).hexdigest() != asm["sha1"]:
        data = build_pack.get_url(asm["url"])
        build_pack.verify(data, {"sha1": asm["sha1"]})
        library.write_bytes(data)
    result = subprocess.run(["java", "--class-path", str(library), str(ROOT / "scripts/KeymapAudit.java"),
                             str(args.mods)], capture_output=True, text=True, check=True, timeout=180)
    report = analyze(json.loads(result.stdout), build_pack.load_cfg().get("performance_profile", {}).get("key_defaults", {}))
    verify_zoom(report)
    build_pack.write_json(args.out / "keybindings-audit.json", report)
    lines = ["# Static keybinding audit", "", report["scope"], "",
             f"Constructors: {report['constructors']}; resolved: {report['resolved']}; game not run.", "",
             "| Key | Modifier | Potential overlaps (context review needed) |", "| --- | --- | --- |"]
    for group in report["possible_collisions"]:
        lines.append("| " + group["key"] + " | " + group["modifier"] + " | " +
                     ", ".join(b["id"] for b in group["bindings"]) + " |")
    (args.out / "keybindings-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Static bindings: {report['constructors']}, resolved: {report['resolved']}; Z plan verified; runtime not verified")


if __name__ == "__main__":
    main()

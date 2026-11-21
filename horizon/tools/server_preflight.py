#!/usr/bin/env python3
"""Read-only prerequisites for an isolated Horizon test; never starts the game.

No downloads, account login, EULA file creation, copying or world conversion.
A passing result is not proof of resource completeness, ownership or gameplay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path

UPSTREAM = "c78187dffffb60f31517eadcb87413386e8ce729"
MODULES = ("betterdungeons", "betterstrongholds", "bettermineshafts",
           "betterfortresses", "terralith", "techquest_yungs_shared")
BINARIES = ("horizon-engine", "horizon-prepare", "horizon-server", "horizon-ctl")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def object_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def inspect(resources: Path, tools: Path, work: Path, server_dir: Path,
            accept_eula: bool = False) -> dict:
    problems = []
    if not accept_eula:
        problems.append("explicit Minecraft EULA consent is required for the server test")
    # This tool does not write even when every check passes.
    if server_dir.is_symlink() or (server_dir.exists() and
                                  (not server_dir.is_dir() or any(server_dir.iterdir()))):
        problems.append("server directory must be new or empty, and not a symlink")
    for label, source in (("resources", resources), ("tools", tools), ("work", work)):
        target, origin = server_dir.resolve(), source.resolve()
        if target == origin or origin in target.parents or target in origin.parents:
            problems.append(f"server directory must be separate from {label}")
    try:
        manifest = object_json(resources / "horizon-resources.json")
        if manifest.get("minecraft") != "26.3" or manifest.get("schema") != 7:
            problems.append("resources must be Minecraft 26.3, Horizon resource schema 7")
        if object_json(resources / "horizon-prepare.json").get("output_version") != 3:
            problems.append("resources require pinned preparer output version 3")
        for name, key in (("facts.json", "facts_sha256"),
                          ("block-tags.json", "block_tags_sha256")):
            expected = manifest.get(key)
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
                problems.append(f"resource manifest is missing valid {key}")
            elif digest(resources / name) != expected.lower():
                problems.append(f"resource checksum differs: {name}")
        for name in ("facts.json", "block-tags.json", "registries.json", "commands.json"):
            if not (resources / name).is_file() or not (resources / name).stat().st_size:
                problems.append(f"missing or empty resource: {name}")
        for name in ("assets/minecraft/font", "assets/minecraft/textures"):
            folder = resources / name
            if not folder.is_dir() or not any(p.is_file() for p in folder.rglob("*")):
                problems.append(f"missing or empty resource folder: {name}")
    except (OSError, ValueError) as exc:
        problems.append(f"prepared resources unavailable or invalid ({type(exc).__name__})")
    try:
        build = object_json(tools / "build-result.json")
        if (build.get("upstream_commit") != UPSTREAM or build.get("minecraft") != "26.3"
                or build.get("platform") != "linux-x86_64" or build.get("default_features") is not False):
            problems.append("native tools must match the pinned Linux headless build")
        hashes = build.get("sha256")
        if not isinstance(hashes, dict):
            raise ValueError("missing binary checksums")
        for name in BINARIES:
            if digest(tools / name) != hashes.get(name):
                problems.append(f"native tool checksum differs: {name}")
    except (OSError, ValueError) as exc:
        problems.append(f"native tools unavailable or invalid ({type(exc).__name__})")
    owners = {}
    for mod_id in MODULES:
        try:
            manifest = tomllib.loads((work / "mods" / mod_id / "carry/horizon-mod.toml")
                                     .read_text(encoding="utf-8"))
            if manifest.get("id") != mod_id or str(manifest.get("api")) != "0.2":
                raise ValueError("module identity/API differs")
            if manifest.get("side") != "both" or "registries" not in manifest.get("capabilities", []):
                raise ValueError("server registries capability required")
            namespaces = manifest.get("namespaces", [mod_id])
            if not isinstance(namespaces, list) or not all(isinstance(n, str) for n in namespaces):
                raise ValueError("invalid namespaces")
            for namespace in namespaces:
                if namespace in owners and owners[namespace] != mod_id:
                    problems.append(f"namespace has multiple owners: {namespace}")
                owners[namespace] = mod_id
        except (OSError, ValueError) as exc:
            problems.append(f"missing or invalid carried module: {mod_id} ({type(exc).__name__})")
    return {
        "schema": 1, "upstream_commit": UPSTREAM, "minecraft": "26.3",
        "eula_consent_provided": accept_eula, "preflight_passed": not problems,
        "problems": problems, "required_modules": list(MODULES),
        "read_only": True, "resources_fully_validated": False,
        "ownership_verified": False, "server_boot_tested": False,
        "combined_mod_load_tested": False, "world_save_reopen_tested": False,
        "multiplayer_tested": False, "gameplay_ported": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resources", type=Path, required=True)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--accept-eula", action="store_true",
                        help="Explicit consent for this isolated test, never inferred from resources")
    args = parser.parse_args()
    report = inspect(args.resources, args.tools, args.work, args.server_dir, args.accept_eula)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["preflight_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

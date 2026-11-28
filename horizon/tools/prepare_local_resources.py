#!/usr/bin/env python3
"""Prepare Horizon 26.3 from the owner's installed official-launcher files.

Linux x86-64 developer tool, not an installer. No download, account login,
server startup, EULA write, or upload is performed by this wrapper.
The official preparer writes resources and its own scratch files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

UPSTREAM = "c78187dffffb60f31517eadcb87413386e8ce729"
VERSION = "26.3"


def digest(path: Path, algorithm: str) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def verify_jar(path: Path, metadata: dict) -> None:
    size, sha = metadata.get("size"), metadata.get("sha1")
    if not isinstance(size, int) or size <= 0 or not isinstance(sha, str):
        raise ValueError("missing JAR size/SHA-1 in installed version metadata")
    if not path.is_file() or path.stat().st_size != size or digest(path, "sha1") != sha.lower():
        raise ValueError("JAR missing or does not match installed version metadata")


def separate_output(output: Path, *inputs: Path) -> Path:
    if output.is_symlink() or output.exists():
        raise ValueError("output must be a new directory")
    target = output.resolve()
    for item in inputs:
        source = item.resolve()
        if target == source or source in target.parents or target in source.parents:
            raise ValueError("output must be separate from inputs and upstream checkout")
    return target


def build_commands(minecraft: Path, upstream: Path, tools: Path,
                   java_home: Path, server_jar: Path, output: Path) -> tuple[list[str], list[str]]:
    output = separate_output(output, minecraft, upstream, tools, java_home, server_jar)
    if subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"],
                               text=True, timeout=15).strip() != UPSTREAM:
        raise ValueError("Horizon checkout must match the pinned revision")
    if subprocess.check_output(["git", "-C", str(upstream), "status", "--porcelain",
                                "--untracked-files=no"], text=True, timeout=15).strip():
        raise ValueError("Horizon checkout has modified tracked files")
    build = read_object(tools / "build-result.json")
    if (build.get("upstream_commit") != UPSTREAM or build.get("minecraft") != VERSION
            or build.get("platform") != "linux-x86_64" or build.get("default_features") is not False):
        raise ValueError("native build does not match pinned Linux headless tools")
    preparer = tools / "horizon-prepare"
    hashes = build.get("sha256", {})
    if not isinstance(hashes, dict) or digest(preparer, "sha256") != hashes.get("horizon-prepare"):
        raise ValueError("preparer SHA-256 mismatch")
    version_dir = minecraft / "versions" / VERSION
    metadata = read_object(version_dir / (VERSION + ".json"))
    if metadata.get("id") != VERSION:
        raise ValueError("installed Minecraft version must be exactly 26.3")
    downloads = metadata.get("downloads", {})
    verify_jar(version_dir / (VERSION + ".jar"), downloads.get("client", {}))
    verify_jar(server_jar, downloads.get("server", {}))
    if not (minecraft / "libraries").is_dir() or not (minecraft / "assets/indexes").is_dir() or not (minecraft / "assets/objects").is_dir():
        raise ValueError("installed libraries or asset store missing")
    if not (java_home / "bin/java").is_file() or not (java_home / "bin/javac").is_file():
        raise ValueError("a Java 25 JDK is required for the pinned development exporters")
    # The official preparer also enforces the pinned Java version and resource schema.
    common = [str(preparer.resolve()), "--root", str(upstream.resolve()), "--output", str(output)]
    prepare = common + ["--prepare", "--complete", "--minecraft-dir", str(minecraft.resolve()),
                        "--server-jar", str(server_jar.resolve()), "--java-home", str(java_home.resolve())]
    return prepare, common + ["--check"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("minecraft-dir", "upstream", "tools", "java-home", "server-jar", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = {"schema": 1, "minecraft": VERSION, "upstream_commit": UPSTREAM,
              "resources_prepared": False, "official_check_passed": False,
              "server_boot_tested": False, "world_save_reopen_tested": False,
              "combined_mod_load_tested": False, "ownership_verified": False}
    try:
        prepare, check = build_commands(args.minecraft_dir, args.upstream, args.tools,
                                        args.java_home, args.server_jar, args.output)
        # Local only: official tools may print local paths; do not upload raw logs.
        subprocess.run(prepare, check=True, timeout=1800)
        subprocess.run(check, check=True, timeout=120)
        report["resources_prepared"] = report["official_check_passed"] = True
    except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        # No absolute paths, game content, or secrets in the summary.
        report["error_type"] = type(exc).__name__
        if isinstance(exc, ValueError):
            report["reason"] = str(exc) if not isinstance(exc, json.JSONDecodeError) else "invalid JSON"
    print(json.dumps(report, indent=2))
    return 0 if report["official_check_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

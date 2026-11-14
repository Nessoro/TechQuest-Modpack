#!/usr/bin/env python3
"""Produce an OFFLINE-signed TechQuest release. Never upload or commit the private key.

Example:
  python scripts/sign_release.py --tag v0.3.3-micro3-preview \
    --pack output/TechQuest_1.21.1_0.3.3_ALPHA.mrpack \
    --installer dist/TechQuestInstaller.exe \
    --private-key /secure/offline/TechQuest_release_signing_PRIVATE.pem \
    --out signed-release
Upload ALL four files from signed-release to the matching GitHub Release tag.
"""
import argparse
import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NAME = "Nessoro/TechQuest-Modpack"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"v[0-9A-Za-z][0-9A-Za-z._-]{0,79}", args.tag):
        parser.error("Invalid signed release tag")
    key = args.private_key.resolve(strict=True)
    if key.is_relative_to(REPO):
        parser.error("Private key must never be kept inside the public repository")
    pack = args.pack.resolve(strict=True)
    installer = args.installer.resolve(strict=True)
    if pack == installer or installer.suffix.lower() != ".exe":
        parser.error("Expected separate pack and Windows EXE")
    with zipfile.ZipFile(pack) as archive:
        index = json.loads(archive.read("modrinth.index.json"))
    if (index["game"] != "minecraft" or
            index["dependencies"]["minecraft"] != "1.21.1" or
            index["dependencies"]["neoforge"] != "21.1.264"):
        parser.error("Unexpected Minecraft or NeoForge version in pack")
    version = index["versionId"]
    if not isinstance(version, str) or not 3 <= len(version) <= 80:
        parser.error("Invalid pack version")
    if installer.stat().st_size > 250 * 1024 * 1024:
        parser.error("EXE exceeds downloader safety limit")
    if pack.stat().st_size > 64 * 1024 * 1024:
        parser.error("Pack exceeds downloader safety limit")

    manifest = {
        "schema": 1,
        "repository": NAME,
        "tag": args.tag,
        "versionId": version,
        "packSha256": hashlib.sha256(pack.read_bytes()).hexdigest(),
        "installerSha256": hashlib.sha256(installer.read_bytes()).hexdigest()
    }
    # Sign the EXACT UTF-8 bytes sent to players, not a reparsed/reformatted JSON.
    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    signature = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(key)],
        input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    ).stdout
    out = args.out.resolve()
    if out == REPO or REPO in out.parents:
        parser.error("Signed release output must be outside the repository to prevent accidental uploads")
    out.mkdir(parents=True, exist_ok=True)
    # Explicit fixed asset names: updater refuses any unexpected asset URL.
    shutil.copyfile(pack, out / "TechQuest_Optimized.mrpack")
    shutil.copyfile(installer, out / "TechQuestInstaller.exe")
    (out / "techquest-release.json").write_bytes(data)
    (out / "techquest-release.sig").write_text(
        base64.b64encode(signature).decode("ascii") + "\n", encoding="ascii"
    )
    print("Created 4 signed release assets in", out)
    print("Tag:", args.tag, "Pack:", version)
    print("PRIVATE KEY: do not upload, email, publish in Actions logs or commit.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.CalledProcessError) as e:
        print("Signing failed:", str(e), file=sys.stderr)
        sys.exit(1)

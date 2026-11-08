#!/usr/bin/env python3
"""Check the GUI's committed metadata against the pinned official installer."""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_pack


def check(plan, data):
    installer = plan["installer"]
    if len(data) != installer["size"] or hashlib.sha512(data).hexdigest() != installer["sha512"]:
        raise ValueError("Pinned NeoForge installer integrity mismatch")
    expected = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in ("install_profile.json", "version.json"):
            for library in json.loads(archive.read(name))["libraries"]:
                file = library["downloads"]["artifact"]
                row = {key: file[key] for key in ("path", "url", "size", "sha1")}
                previous = expected.setdefault(row["path"], row)
                if previous != row:
                    raise ValueError("Conflicting official library: " + row["path"])
    actual = {row["path"]: row for row in plan["libraries"]}
    if actual != expected or len(actual) != len(plan["libraries"]):
        raise ValueError("Committed library metadata differs from official installer")
    print("Verified pinned installer and", len(actual), "official library records; game not run")


if __name__ == "__main__":
    plan = json.loads((ROOT / "windows-installer/assets/neoforge-21.1.264-bootstrap.json").read_text())
    check(plan, build_pack.get_url(plan["installer"]["url"]))

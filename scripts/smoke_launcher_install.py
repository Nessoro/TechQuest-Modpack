#!/usr/bin/env python3
"""CI-only, temporary official client-profile installation with Maven unavailable.

Does not launch Minecraft, accept a server EULA, or upload game/library binaries.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, sha1=None):
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    if sha1 and hashlib.sha1(data).hexdigest() != sha1:
        raise ValueError("Official Minecraft fixture checksum mismatch: " + url)
    return data


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("This installer smoke test is restricted to an isolated GitHub Actions runner")
    with tempfile.TemporaryDirectory(prefix="TechQuest-client-smoke-") as tmp:
        root = Path(tmp)
        launcher = root / "launcher"
        version = launcher / "versions/1.21.1"
        version.mkdir(parents=True)
        index = json.loads(fetch("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
        entry = next(v for v in index["versions"] if v["id"] == "1.21.1")
        data = fetch(entry["url"], entry["sha1"])
        (version / "1.21.1.json").write_bytes(data)
        metadata = json.loads(data)
        client = metadata["downloads"]["client"]
        (version / "1.21.1.jar").write_bytes(fetch(client["url"], client["sha1"]))
        (launcher / "launcher_profiles.json").write_text('{"profiles":{}}', encoding="utf-8")
        cache = root / "cache"
        subprocess.run(["dotnet", "run", "--project", str(ROOT / "tests/neoforge-bootstrap/BootstrapTests.csproj"),
                        "--configuration", "Release", "--", "--prepare-client", str(launcher), str(cache)], check=True)
        # Apply to child processor JVMs too. Mojang stays available for mappings;
        # Maven has an intentionally unreachable proxy. No host/network settings change.
        env = dict(os.environ)
        env["JAVA_TOOL_OPTIONS"] = env.get("JAVA_TOOL_OPTIONS", "") + (
            " -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=9"
            " -Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=9"
            " -Dhttp.nonProxyHosts=*.mojang.com|*.minecraft.net|mirrors.neoforged.net")
        subprocess.run(["java", "-jar", str(cache / "neoforge-21.1.264-installer.jar"),
                        "--installClient", str(launcher)], cwd=root, env=env, check=True, timeout=600)
        profile = launcher / "versions/neoforge-21.1.264/neoforge-21.1.264.json"
        if not profile.is_file() or json.loads(profile.read_text())["inheritsFrom"] != "1.21.1":
            raise ValueError("Official NeoForge client version was not created")
        profiles = json.loads((launcher / "launcher_profiles.json").read_text())["profiles"]
        if not any(p.get("lastVersionId") == "neoforge-21.1.264" for p in profiles.values()):
            raise ValueError("Official Minecraft Launcher profile was not created")
        print("PASS: official client installer created NeoForge version and Launcher profile with primary Maven unavailable.")
        print("Minecraft gameplay and GUI interaction were NOT tested; no game files are uploaded.")


if __name__ == "__main__":
    main()

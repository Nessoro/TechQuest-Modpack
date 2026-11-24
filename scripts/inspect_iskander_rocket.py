#!/usr/bin/env python3
"""Read-only official Modrinth metadata inspection for Iskander Rocket.
Never changes modlist and does not download or redistribute the JAR.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_pack as b

PROJECT = "iskander-rocket-mod"

def main():
    try:
        meta = b.get_json("/project/" + PROJECT)
        versions = b.get_json("/project/" + PROJECT + "/version", {
            "loaders": json.dumps(["neoforge"]),
            "game_versions": json.dumps(["1.21.1"]),
        })
        rows = []
        for version in versions:
            try:
                file = b.select_mod_file(version)
            except Exception as e:
                rows.append({"error": str(e), "version_id": version.get("id")})
                continue
            rows.append({
                "version": version.get("version_number"),
                "version_id": version.get("id"),
                "name": version.get("name"),
                "published": version.get("date_published"),
                "game_versions": version.get("game_versions"),
                "loaders": version.get("loaders"),
                "filename": file.get("filename"),
                "sha512": file.get("hashes", {}).get("sha512"),
                "sha1": file.get("hashes", {}).get("sha1"),
                "size": file.get("size"),
                "url": file.get("url"),
                "dependencies": version.get("dependencies", []),
                "version_type": version.get("version_type"),
            })
        print("ISKANDER_METADATA_BEGIN")
        print(json.dumps({
            "project": PROJECT, "id": meta["id"], "title": meta["title"],
            "client_side": meta.get("client_side"), "server_side": meta.get("server_side"),
            "license": meta.get("license"),
            "versions": rows
        }, indent=2, ensure_ascii=False))
        print("ISKANDER_METADATA_END")
        if not rows:
            raise SystemExit("No official NeoForge 1.21.1 Modrinth files.")
    except Exception as exc:
        print("ISKANDER_METADATA_ERROR", type(exc).__name__, str(exc))
        raise

if __name__ == "__main__":
    main()

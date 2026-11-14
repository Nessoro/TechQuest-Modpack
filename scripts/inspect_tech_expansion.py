#!/usr/bin/env python3
"""Read-only metadata inspection for optional TechQuest technology expansion.

Produces exact project IDs, NeoForge 1.21.1 version IDs, filenames, hashes,
side metadata and required dependency links. Writes NOTHING to modlist.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import build_pack as builder

CANDIDATES = (
    ("trash-cans", "lSKYKJdm", ""),
    ("pretty-pipes", "lrhbGGSe", ""),
)

def show(project, exact="", prefix=""):
    versions = builder.get_json("/project/" + project + "/version", {
        "loaders": json.dumps(["neoforge"]),
        "game_versions": json.dumps(["1.21.1"]),
    })
    meta = builder.get_json("/project/" + project)
    version = builder.select_version(versions, prefix, exact)
    file = builder.select_mod_file(version)
    return {
        "project": project, "id": meta["id"], "title": meta["title"],
        "version": version["version_number"], "version_id": version["id"],
        "filename": file["filename"], "sha512": file["hashes"].get("sha512"),
        "sha1": file["hashes"].get("sha1"), "size": file.get("size"),
        "env": {"client": meta.get("client_side", "required"),
                "server": meta.get("server_side", "required")},
        "url": file.get("url"), "deps": [
            {"project_id": d.get("project_id"), "version_id": d.get("version_id"),
             "dependency_type": d.get("dependency_type")}
            for d in version.get("dependencies", [])],
    }

def main():
    cfg = builder.load_cfg()
    old = cfg["modrinth_lock"]
    results, visited = [], set()
    def inspect(project, exact="", prefix=""):
        item = show(project, exact, prefix)
        if item["id"] in visited:
            return
        visited.add(item["id"])
        item["already_locked"] = item["id"] in old
        if item["already_locked"]:
            item["previous_version"] = old[item["id"]]["version_id"]
        results.append(item)
        for dependency in item["deps"]:
            if dependency["dependency_type"] != "required":
                continue
            ident = dependency["project_id"]
            if not ident and dependency["version_id"]:
                info = builder.get_json("/version/" + dependency["version_id"])
                ident = info["project_id"]
            if not ident:
                raise RuntimeError("Unresolved mandatory dep for " + item["id"])
            # Preserve lock for already-installed dependencies.
            if ident in old:
                item.setdefault("locked_dependencies", []).append(
                    {"id":ident,"version_id":old[ident]["version_id"]})
            else:
                inspect(ident, exact=dependency["version_id"] or "")
    for p, v, prefix in CANDIDATES:
        inspect(p, exact=v, prefix=prefix)
    print("TECHQUEST_EXPANSION_PLAN_START")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("TECHQUEST_EXPANSION_PLAN_END")

if __name__ == "__main__":
    main()

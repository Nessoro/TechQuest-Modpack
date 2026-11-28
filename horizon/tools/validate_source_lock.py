#!/usr/bin/env python3
"""Validate a frozen NeoForge source lock against cached public Modrinth metadata.

Never selects latest releases, downloads JARs, edits the source or claims a port.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from stage_terralith_content import read_checked


def unique(values, key):
    result = {value[key]: value for value in values}
    if len(result) != len(values):
        raise ValueError("duplicate metadata " + key)
    return result


def validate(source, projects, versions):
    if (source.get("minecraft"), source.get("loader")) != ("1.21.1", "neoforge"):
        raise ValueError("expected NeoForge 1.21.1")
    pins = source.get("modrinth_lock", {})
    projects, versions = unique(projects, "id"), unique(versions, "id")
    if (not pins or set(projects) != set(pins) or
            set(versions) != {p["version_id"] for p in pins.values()}):
        raise ValueError("metadata and source lock sets differ")
    aliases = {p["slug"]: p["id"] for p in projects.values()}
    aliases.update({pid: pid for pid in projects})
    denied = ("mcheli", "tacz", "timelessandclassicszero", "parcool")

    def excluded(value):
        return any(token in re.sub(r"[^a-z0-9]", "", str(value).lower()) for token in denied)

    for section in ("mods", "manual_mods", "external_mods", "optional_local_mods"):
        for mod in source.get(section, []):
            if any(excluded(mod.get(key, "")) for key in ("project", "id", "name", "file_name")):
                raise ValueError("excluded mod in active source")
    direct, client_only, unresolved_optional = set(), set(), []
    for mod in source["mods"]:
        pid = aliases.get(mod["project"])
        if pid not in pins and mod.get("required") is False:
            unresolved_optional.append(mod["project"])
            continue
        if pid not in pins or pid in direct:
            raise ValueError("missing or duplicate direct project: " + mod["project"])
        direct.add(pid)
        if mod.get("version_id") and mod["version_id"] != pins[pid]["version_id"]:
            raise ValueError("direct version pin differs: " + mod["project"])
        if not pins[pid]["version"].startswith(mod.get("version_prefix", "")):
            raise ValueError("direct version prefix differs: " + mod["project"])
        if mod.get("client_only"):
            client_only.add(pid)
    filenames, dependencies, side_labels = set(), [], []
    for pid, pin in pins.items():
        project, version = projects[pid], versions[pin["version_id"]]
        if any(excluded(v) for v in (project["slug"], pin["title"], pin["filename"])):
            raise ValueError("excluded mod hidden behind a project ID")
        if (project["project_type"] != "mod" or version["project_id"] != pid or
                version["version_number"] != pin["version"] or
                source["minecraft"] not in version["game_versions"] or
                source["loader"] not in version["loaders"]):
            raise ValueError("version identity or game/loader differs: " + pid)
        name = pin["filename"]
        if (Path(name).name != name or "\\" in name or not name.endswith(".jar") or
                name.casefold() in filenames or not re.fullmatch(r"[0-9a-f]{128}", pin["sha512"])):
            raise ValueError("unsafe/duplicate filename or missing SHA-512")
        filenames.add(name.casefold())
        files = [f for f in version["files"] if f["filename"] == name and
                 f["hashes"].get("sha512") == pin["sha512"]]
        if len(files) != 1:
            raise ValueError("source file/hash differs from version metadata: " + pid)
        url = urlsplit(files[0]["url"])
        if (url.scheme != "https" or url.hostname != "cdn.modrinth.com" or
                url.username or url.password or not 0 < files[0]["size"] <= 256 * 1024 * 1024):
            raise ValueError("unexpected file URL or size: " + pid)
        environment = pin["environment"]
        if (set(environment) != {"client", "server"} or
                any(v not in ("required", "optional", "unsupported") for v in environment.values()) or
                pid in client_only and environment["server"] != "unsupported"):
            raise ValueError("invalid source environment: " + pid)
        published = {"client": project["client_side"], "server": project["server_side"]}
        if pid in client_only:
            published["server"] = "unsupported"
        if published != environment:
            # Project labels are mutable and not the pack's installation policy.
            side_labels.append({"id": pid, "source": environment, "published": published})
        for dep in version.get("dependencies", []):
            other, vid = dep.get("project_id"), dep.get("version_id")
            if not other and vid in versions:
                other = versions[vid]["project_id"]
            if dep["dependency_type"] == "required":
                if other not in pins or vid and pins[other]["version_id"] != vid:
                    raise ValueError("missing or conflicting required dependency: " + pid)
                dependencies.append({"from": pid, "to": other, "version_id": vid})
            elif (dep["dependency_type"] == "incompatible" and other in pins and
                  (not vid or pins[other]["version_id"] == vid)):
                raise ValueError("incompatible selected dependency: " + pid)
    return {"schema": 1, "source_minecraft": "1.21.1", "source_loader": "neoforge",
            "declared_direct_modrinth_projects": len(source["mods"]),
            "resolved_direct_modrinth_projects": len(direct), "locked_modrinth_projects": len(pins),
            "unresolved_optional_direct_projects": unresolved_optional,
            "required_dependency_edges": len(dependencies), "dependencies": dependencies,
            "source_environment_preserved": True, "mutable_side_label_differences": side_labels,
            "excluded_mods_present": False, "all_file_hashes_match_metadata": True,
            "jar_bytes_verified": False, "horizon_gameplay_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "metadata-dir", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    raw = read_checked(args.source)
    report = validate(json.loads(raw),
                      json.loads(read_checked(args.metadata_dir / "projects.json")),
                      json.loads(read_checked(args.metadata_dir / "versions.json")))
    report["source_sha256"] = hashlib.sha256(raw).hexdigest()
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("Validated", report["locked_modrinth_projects"], "exact project/file pins and",
          report["required_dependency_edges"], "required dependency edges; no JARs executed")


if __name__ == "__main__":
    main()

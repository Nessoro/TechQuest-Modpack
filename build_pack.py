#!/usr/bin/env python3
"""Build TechQuest for Minecraft 1.21.1 / NeoForge.

Resolves Modrinth mod versions and mandatory dependencies, verifies hashes,
produces an .mrpack and separate client/server folders. The pinned IC2 Nostalgia
JAR is read from manual-mods/ and referenced through its immutable GitHub URL.
The .mrpack contains only a URL and verified hashes, not the third-party JAR.
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = "https://api.modrinth.com/v2"
UA = "TechQuest-Modpack/0.1 (modpack installer)"
MAX_DOWNLOAD = 256 * 1024 * 1024
COMPAT_JAR_NAME = "techquest-compat-1.0.0.jar"

class BuildError(Exception):
    pass

def load_cfg():
    return json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def get_url(url):
    if not url.startswith("https://"):
        raise BuildError("HTTPS is required: " + url)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=50) as response:
                data = response.read(MAX_DOWNLOAD + 1)
            if len(data) > MAX_DOWNLOAD:
                raise BuildError("File exceeds size limit")
            return data
        except (OSError, urllib.error.HTTPError) as exc:
            if attempt == 2:
                raise BuildError("Download failed for %s: %s" % (url, exc)) from exc
            time.sleep(attempt + 1)

def get_json(path, args=None):
    url = API + path
    if args:
        url += "?" + urllib.parse.urlencode(args)
    return json.loads(get_url(url).decode("utf-8"))

def safe_filename(name):
    if not isinstance(name, str) or name != Path(name).name or "/" in name or "\\" in name:
        raise BuildError("Unsafe JAR filename: %r" % name)
    return name

def select_version(versions, prefix="", version_id=""):
    options = [v for v in versions
               if (not prefix or v.get("version_number", "").startswith(prefix))
               and (not version_id or v.get("id") == version_id)]
    if not options:
        raise BuildError("No matching NeoForge 1.21.1 version")
    stable = [v for v in options if v.get("version_type") == "release"]
    return max(stable or options, key=lambda v: v.get("date_published", ""))

def resolve_manifest(cfg):
    found = {}
    skipped = []
    visiting = set()
    def add(project, required=True, prefix="", parent="modlist", version_id=""):
        project = str(project)
        if project in visiting:
            for record in found.values():
                if project in (record["requested"], record["id"]):
                    if version_id and record["version_id"] != version_id:
                        raise BuildError("Exact dependency conflict in cycle for " + project)
            return
        visiting.add(project)
        previous = set(found)
        try:
            versions = get_json("/project/%s/version" % urllib.parse.quote(project, safe=""), {
                "loaders": json.dumps([cfg["loader"]]),
                "game_versions": json.dumps([cfg["minecraft"]])
            })
            version = select_version(versions, prefix, version_id)
            meta = get_json("/project/" + urllib.parse.quote(project, safe=""))
            canonical_id = meta["id"]
            if meta.get("project_type") != "mod":
                raise BuildError("Project is not a mod")
            if canonical_id in found:
                if version_id and found[canonical_id]["version_id"] != version_id:
                    raise BuildError("Exact dependency conflict for %s: resolved %s but %s requires %s" %
                                     (project, found[canonical_id]["version_id"], parent, version_id))
                if prefix and not found[canonical_id]["version"].startswith(prefix):
                    raise BuildError("Version conflict for %s: resolved %s but requested %s" %
                                     (project, found[canonical_id]["version"], prefix))
                return
            modfiles = [f for f in version.get("files", []) if f["filename"].endswith(".jar")]
            if not modfiles:
                raise BuildError("Version has no JAR")
            selected = next((f for f in modfiles if f.get("primary")), modfiles[0])
            safe_filename(selected["filename"])
            side = {"client": meta.get("client_side", "required"),
                    "server": meta.get("server_side", "required")}
            found[canonical_id] = {"requested": project, "id": canonical_id,
                "title": meta.get("title", project), "version": version["version_number"],
                "version_id": version["id"], "filename": selected["filename"],
                "file": selected, "environment": side}
            for dep in version.get("dependencies", []):
                if dep.get("dependency_type") != "required":
                    continue
                dependency_id = dep.get("project_id")
                if not dependency_id and dep.get("version_id"):
                    dv = get_json("/version/" + urllib.parse.quote(str(dep["version_id"]), safe=""))
                    dependency_id = dv.get("project_id")
                if not dependency_id:
                    raise BuildError("Unknown mandatory dependency in " + project)
                add(dependency_id, True, parent=project, version_id=dep.get("version_id") or "")
            print("  +", meta.get("title", project), version["version_number"])
        except (KeyError, TypeError, ValueError, BuildError) as exc:
            for key in set(found) - previous:
                found.pop(key)
            if required:
                raise BuildError("%s (dependency of %s): %s" % (project, parent, exc)) from exc
            print("  ? Optional unavailable:", project, exc)
            skipped.append({"project": project, "reason": str(exc)})
        finally:
            visiting.discard(project)
    # Resolve explicitly pinned entries first, so a transitive dependency does not
    # silently select a different release before its own version_prefix is applied.
    ordered = sorted(cfg["mods"], key=lambda item: not bool(item.get("version_prefix") or item.get("version_id")))
    for entry in ordered:
        add(entry["project"], entry.get("required", True), entry.get("version_prefix", ""),
            version_id=entry.get("version_id", ""))
    return list(found.values()), skipped

def verify(data, hashes):
    checked = False
    for algo in ("sha512", "sha1"):
        if hashes.get(algo):
            checked = True
            if hashlib.new(algo, data).hexdigest().lower() != hashes[algo].lower():
                raise BuildError("Invalid %s checksum" % algo)
    if not checked:
        raise BuildError("Missing file integrity hash")

def download_checked(info, dest):
    file = info["file"]
    path = dest / safe_filename(file["filename"])
    if path.is_file():
        try:
            verify(path.read_bytes(), file.get("hashes", {}))
            return path
        except BuildError:
            path.unlink()
    url = file["url"]
    if not url.startswith("https://"):
        raise BuildError("Insecure download URL")
    data = get_url(url)
    verify(data, file.get("hashes", {}))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path

def manual_records(cfg):
    """Verify owner-supplied mod JARs and prepare hash-pinned download entries.

    The public .mrpack references an immutable GitHub URL; it does not embed the
    third-party binary. The GitHub-hosted copy requires license compliance.
    """
    records = []
    for mod in cfg.get("manual_mods", []):
        name = safe_filename(mod["file_name"])
        path = ROOT / "manual-mods" / name
        if not path.is_file():
            if mod.get("required"):
                raise BuildError("Missing REQUIRED manual mod: " + name)
            continue
        if path.stat().st_size <= 1024 or not zipfile.is_zipfile(path):
            raise BuildError("Invalid manual JAR: " + name)
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise BuildError("Corrupt manual JAR: " + name)
            if not any(x in archive.namelist() for x in
                       ("META-INF/neoforge.mods.toml", "META-INF/mods.toml")):
                raise BuildError("Mod metadata not found in manual JAR: " + name)
        url = mod.get("download_url")
        if not url or not url.startswith("https://raw.githubusercontent.com/"):
            raise BuildError("Manual mod has no pinned GitHub raw URL: " + name)
        data = path.read_bytes()
        records.append({
            "name": mod["name"], "filename": name, "source_path": path,
            "url": url, "fileSize": len(data),
            "hashes": {"sha1": hashlib.sha1(data).hexdigest(),
                       "sha512": hashlib.sha512(data).hexdigest()}})
    return records


def compatibility_jar():
    """Package our data-only NeoForge mod; no third-party binary is embedded."""
    import io
    source = ROOT / "compat" / "techquest-compat"
    if not (source / "META-INF" / "neoforge.mods.toml").is_file():
        raise BuildError("Missing TechQuest compatibility resources")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                # Fixed timestamps make repeated builds byte-identical.
                info = zipfile.ZipInfo(path.relative_to(source).as_posix(), (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def patch_superb_server_jar(path):
    """Remove a client mixin from SBW 0.8.9.2's common list, on servers only.

    Call only AFTER verifying the original download hash. The original remains
    unchanged in the client and .mrpack download manifest; no patched JAR is published.
    """
    path = Path(path)
    if not path.name.startswith("superbwarfare-0.8.9.2-"):
        return False
    config_name = "mixins.superbwarfare.json"
    with zipfile.ZipFile(path) as source:
        config = json.loads(source.read(config_name))
        if "ClientLevelMixin" not in config.get("client", []):
            raise BuildError("Unexpected Superb Warfare mixin layout; review workaround")
        if "ClientLevelMixin" not in config.get("mixins", []):
            return False
        if any(name.upper().endswith((".SF", ".RSA", ".DSA"))
               for name in source.namelist() if name.startswith("META-INF/")):
            raise BuildError("Refusing to patch a signed Superb Warfare JAR")
        config["mixins"].remove("ClientLevelMixin")
        temporary = path.with_suffix(".jar.tmp")
        try:
            with zipfile.ZipFile(temporary, "w") as target:
                for info in source.infolist():
                    data = (json.dumps(config, indent=2).encode("utf-8")
                            if info.filename == config_name else source.read(info.filename))
                    target.writestr(info, data)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)
    print("Applied server-only Superb Warfare ClientLevelMixin fix:", path.name)
    return True


def remove_stale_generated_jars(directory, expected):
    """Generated output must not retain older mod versions after rebuilding."""
    for path in directory.glob("*.jar"):
        if path.name not in expected:
            path.unlink()
            print("Removed obsolete generated mod:", path.name)


def make_mrpack(cfg, mods, output, manual_files=()):
    files = []
    for rec in mods:
        f = rec["file"]
        hashes = {k: v for k,v in f.get("hashes", {}).items() if k in ("sha1", "sha512")}
        if not hashes:
            raise BuildError("No hash: " + f["filename"])
        side = {k: ("unsupported" if v == "unsupported" else "required")
                for k,v in rec["environment"].items()}
        if all(v == "unsupported" for v in side.values()):
            continue
        files.append({"path": "mods/" + safe_filename(f["filename"]),
                      "hashes": hashes, "env": side, "downloads": [f["url"]],
                      "fileSize": f["size"]})
    for local in manual_files:
        files.append({
            "path": "mods/" + safe_filename(local["filename"]),
            "hashes": local["hashes"],
            "env": {"client": "required", "server": "required"},
            "downloads": [local["url"]],
            "fileSize": local["fileSize"]})
    idx = {"formatVersion": 1, "game": "minecraft", "versionId": cfg["version"],
           "name": cfg["pack_name"], "summary": cfg["description"],
           "files": files,
           "dependencies": {"minecraft": cfg["minecraft"], "neoforge": cfg["loader_version"]}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("modrinth.index.json", json.dumps(idx, ensure_ascii=False, indent=2))
        archive.writestr("overrides/mods/" + COMPAT_JAR_NAME, compatibility_jar())
    return len(files)

def main():
    argp = argparse.ArgumentParser(description="TechQuest client/server pack generator")
    argp.add_argument("--resolve-only", action="store_true",
                      help="check Modrinth versions without downloading mod JARs")
    argp.add_argument("--no-mrpack", action="store_true", help="skip Modrinth archive")
    args = argp.parse_args()
    cfg = load_cfg()
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    print("Resolving Minecraft", cfg["minecraft"], cfg["loader"], "...")
    resolved, optional = resolve_manifest(cfg)
    manual = manual_records(cfg)
    write_json(out / "versions-lock.json", {
        "minecraft": cfg["minecraft"], "loader_version": cfg["loader_version"],
        "mods": [{k:m[k] for k in ("requested","title","version","version_id","filename","environment")}
                 for m in resolved], "optional_skipped": optional,
        "manual_mods": [{"name": row["name"], "file_name": row["filename"],
                          "url": row["url"], "hashes": row["hashes"]}
                         for row in manual]})
    if not args.no_mrpack:
        n = make_mrpack(cfg, resolved, out / "TechQuest_1.21.1_0.1.0.mrpack", manual)
        print("Generated Modrinth manifest:", n, "files")
    if args.resolve_only:
        print("Version resolution done. Minecraft startup is NOT verified.")
        return
    client = out / "client" / "mods"
    server = out / "server" / "mods"
    client.mkdir(parents=True, exist_ok=True)
    server.mkdir(parents=True, exist_ok=True)
    for side, directory in (("client", client), ("server", server)):
        expected = {rec["filename"] for rec in resolved if rec["environment"][side] != "unsupported"}
        expected.update(local["filename"] for local in manual)
        expected.add(COMPAT_JAR_NAME)
        remove_stale_generated_jars(directory, expected)
    for rec in resolved:
        env = rec["environment"]
        if env["client"] != "unsupported":
            local = download_checked(rec, client)
            if env["server"] != "unsupported":
                shutil.copy2(local, server / local.name)
        elif env["server"] != "unsupported":
            download_checked(rec, server)
    missing = []
    for local in manual:
        shutil.copy2(local["source_path"], client / local["filename"])
        shutil.copy2(local["source_path"], server / local["filename"])
    for directory in (client, server):
        (directory / COMPAT_JAR_NAME).write_bytes(compatibility_jar())
    for path in server.glob("superbwarfare-*.jar"):
        patch_superb_server_jar(path)
    (out / "server" / "server.properties").write_text(
        "motd=TechQuest Industrial Frontier\nmax-players=8\nonline-mode=true\n"
        "white-list=true\nenforce-whitelist=true\nenable-rcon=false\n"
        "view-distance=8\nsimulation-distance=6\nallow-flight=true\n", encoding="utf-8")
    (out / "server" / "START_HERE.txt").write_text(
        "Install official NeoForge %s for Minecraft %s with Java 21; then "
        "review Mojang EULA and set eula=true only if you agree. Enable whitelist "
        "and back up the world before mod updates.\n" %
        (cfg["loader_version"], cfg["minecraft"]), encoding="utf-8")
    write_json(out / "BUILD_STATUS.json", {
        "status": "READY_FOR_GAME_TESTS",
        "missing_mods": missing,
        "warning": "Successful build DOES NOT confirm client/server runtime compatibility"})
    print("Client/server files created. Missing manually supplied mods:", missing)
    print("Test both client and server before sharing a world.")

if __name__ == "__main__":
    try:
        main()
    except (BuildError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("BUILD FAILED:", exc, file=sys.stderr)
        sys.exit(2)

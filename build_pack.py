#!/usr/bin/env python3
"""Build TechQuest for Minecraft 1.21.1 / NeoForge.

Resolves Modrinth mod versions and mandatory dependencies, verifies hashes,
produces an .mrpack and separate client/server folders. The pinned IC2 Nostalgia
JAR is read from manual-mods/ and referenced through its immutable GitHub URL.
The .mrpack contains only a URL and verified hashes, not the third-party JAR.
"""
import argparse
import hashlib
import io
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from scripts.guide_assets import guide_overrides

ROOT = Path(__file__).resolve().parent
API = "https://api.modrinth.com/v2"
UA = "TechQuest-Modpack/0.1 (modpack installer)"
MAX_DOWNLOAD = 256 * 1024 * 1024

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


def select_mod_file(version):
    # Some authors mark their sources JAR primary (Forgematica 0.4.3 does).
    # A source/documentation archive is never a playable mod binary.
    files = [file for file in version.get("files", [])
             if file["filename"].lower().endswith(".jar")
             and not file["filename"].lower().endswith(("-sources.jar", "-javadoc.jar"))]
    if not files:
        raise BuildError("Version has no runtime JAR (sources/javadoc are not mods)")
    return next((file for file in files if file.get("primary")), files[0])

def resolve_manifest(cfg):
    pins = cfg.get("modrinth_lock", {})
    if not isinstance(pins, dict):
        raise BuildError("Invalid Modrinth lock")
    for identity, lock in pins.items():
        if (not isinstance(identity, str) or not isinstance(lock, dict)
                or not isinstance(lock.get("version_id"), str) or not lock["version_id"]
                or not isinstance(lock.get("filename"), str)
                or not isinstance(lock.get("sha512"), str) or len(lock["sha512"]) != 128
                or any(c not in "0123456789abcdef" for c in lock["sha512"])
                or not isinstance(lock.get("environment"), dict)
                or set(lock.get("environment", {})) != {"client", "server"}
                or any(v not in ("required", "optional", "unsupported") for v in lock["environment"].values())):
            raise BuildError("Invalid Modrinth lock entry: " + str(identity))
    found = {}
    canonical_ids = {}
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
            meta = get_json("/project/" + urllib.parse.quote(project, safe=""))
            canonical_id = meta["id"]
            canonical_ids[project] = canonical_id
            lock = pins.get(canonical_id, {})
            if pins and not lock:
                raise BuildError("Unlocked Modrinth project requires review: " + project)
            locked = lock.get("version_id", "")
            if locked and version_id and locked != version_id:
                raise BuildError("Exact version pin conflict for %s: locked %s but %s requires %s" %
                                 (project, locked, parent, version_id))
            version_id = locked or version_id
            version = select_version(versions, prefix, version_id)
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
            if lock:
                files = [f for f in version.get("files", []) if f.get("filename") == lock["filename"]
                         and f.get("hashes", {}).get("sha512") == lock["sha512"]]
                if not files:
                    raise BuildError("Locked Modrinth file is missing or changed: " + project)
                selected = select_mod_file(dict(version, files=files))
            else:
                selected = select_mod_file(version)
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
    # A dependency may have been resolved first via a Modrinth ID rather than
    # the explicit slug. Apply reviewed sides to the canonical project identity.
    client_only = {canonical_ids[entry["project"]] for entry in cfg["mods"]
                   if entry.get("client_only") and entry["project"] in canonical_ids}
    side_overrides = {canonical_ids[entry["project"]]: entry["environment"] for entry in cfg["mods"]
                      if entry.get("environment") and entry["project"] in canonical_ids}
    for item in found.values():
        override = side_overrides.get(item["id"], {})
        if any(side not in ("client", "server") or value not in ("required", "optional", "unsupported")
               for side, value in override.items()):
            raise BuildError("Invalid reviewed environment override: " + item["requested"])
        item["environment"].update(override)
        if item["id"] in client_only:
            if item["environment"]["client"] == "unsupported":
                raise BuildError("Client-only mod is not client-compatible: " + item["requested"])
            item["environment"]["server"] = "unsupported"
        lock = pins.get(item["id"])
        if lock and item["environment"] != lock["environment"]:
            raise BuildError("Locked Modrinth environment changed: " + item["requested"])
    if pins and set(found) != set(pins):
        raise BuildError("Locked profile is incomplete; missing projects: " + ", ".join(sorted(set(pins) - set(found))))
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


def external_records(cfg):
    """Resolve a pinned, author-hosted binary without vendoring it into TechQuest.

    The manifest keeps only an official release URL and freshly verified hashes.
    The source SHA-256 pin comes from the author's GitHub Release asset metadata.
    """
    records = []
    for mod in cfg.get("external_mods", []):
        filename = safe_filename(mod["file_name"])
        url = mod["download_url"]
        parsed = urllib.parse.urlsplit(url)
        trusted = {
            "incoming-3.10.4.jar": (
                "github.com", "/zentixua/incoming/releases/download/v3.10.4/incoming-3.10.4.jar"),
            "ftb-library-neoforge-2101.1.39.jar": (
                "maven.ftb.dev", "/releases/dev/ftb/mods/ftb-library-neoforge/2101.1.39/ftb-library-neoforge-2101.1.39.jar"),
            "ftb-ultimine-neoforge-2101.1.15.jar": (
                "maven.ftb.dev", "/releases/dev/ftb/mods/ftb-ultimine-neoforge/2101.1.15/ftb-ultimine-neoforge-2101.1.15.jar"),
        }
        if (parsed.scheme != "https" or (parsed.hostname, parsed.path) != trusted.get(filename)
                or parsed.query or parsed.fragment):
            raise BuildError("Unexpected author release URL: " + url)
        size = mod["file_size"]
        expected = mod["sha256"]
        if (not isinstance(size, int) or size <= 1024 or size > MAX_DOWNLOAD
                or not isinstance(expected, str) or len(expected) != 64
                or any(c not in "0123456789abcdefABCDEF" for c in expected)):
            raise BuildError("Missing trusted size/SHA256 pin: " + filename)
        print("  + Fetching author-hosted", filename, flush=True)
        data = get_url(url)
        if len(data) != size or hashlib.sha256(data).hexdigest().lower() != expected.lower():
            raise BuildError("Author release size/SHA256 mismatch: " + filename)
        if not zipfile.is_zipfile(io.BytesIO(data)):
            raise BuildError("Author release is not a JAR: " + filename)
        with zipfile.ZipFile(io.BytesIO(data)) as jar:
            if jar.testzip() is not None:
                raise BuildError("Corrupt author release JAR: " + filename)
            if not any(n in jar.namelist() for n in
                       ("META-INF/neoforge.mods.toml", "META-INF/mods.toml")):
                raise BuildError("NeoForge metadata missing: " + filename)
        records.append({
            "name": mod["name"], "filename": filename, "data": data,
            "url": url, "fileSize": len(data), "sha256": expected,
            "hashes": {"sha1": hashlib.sha1(data).hexdigest(),
                       "sha512": hashlib.sha512(data).hexdigest()}})
    return records


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


def client_config_overrides(cfg):
    """Version-reviewed client presets; the server-named file is for singleplayer."""
    result = {}
    physics = next((mod for mod in cfg.get("mods", [])
                    if mod["project"] == "physicsmod"), None)
    if physics:
        if physics.get("version_id") != "wudTG1nk" or not physics.get("client_only"):
            raise BuildError("Review Physics Mod client preset before changing its version or side")
        result.update({"config/physicsmod/" + name: (ROOT / "compat" / "physicsmod" / name).read_bytes()
                       for name in ("physics_client_config.json", "physics_server_config.json")})
    zoom = next((mod for mod in cfg.get("mods", []) if mod["project"] == "better-zoom"), None)
    if zoom:
        if zoom.get("version_id") != "NwwnadOr" or not zoom.get("client_only"):
            raise BuildError("Review Better Zoom client preset before changing its version or side")
        result["config/betterzoom-client.toml"] = (ROOT / "compat/client-controls/betterzoom-client.toml").read_bytes()
    pmmo = next((mod for mod in cfg.get("mods", [])
                 if mod["project"] == "project-mmo"), None)
    if pmmo:
        # The installed version is pinned in the Modrinth lock (not in the root mod row).
        lock = cfg.get("modrinth_lock", {}).get("KFQYC1Uy", {})
        if (lock.get("version_id") != "9lu4zNd1" or
                lock.get("filename") != "pmmo-1.21.1-2.10.47.jar"):
            raise BuildError("Review Project MMO HUD preset before changing its version")
        result["config/pmmo-client.toml"] = (
            ROOT / "compat/client-hud/pmmo-client.toml").read_bytes()
    # Schema and keys reviewed against the exact pinned JARs. In particular,
    # TXF uses .json5 and Jade groups plugin switches by namespace, not full IDs.
    reviewed = (
        ("health-indicator-txf", "N56hoqkq", "xGqsX1go", "healthindicatortxf.json5", "healthindicatortxf.json5"),
        ("jade", "nvQzSEkH", "eYz2YBGT", "jade-plugins.json", "jade/plugins.json"),
        ("explosion-overhaul-a-new-level-of-destruction", "sOxnTLKl", "mxfQE01f",
         "explosionoverhaul-client.toml", "explosionoverhaul/explosionoverhaul-client.toml"),
    )
    projects = {mod["project"] for mod in cfg.get("mods", [])}
    for project, project_id, version_id, source, destination in reviewed:
        if project in projects:
            if cfg.get("modrinth_lock", {}).get(project_id, {}).get("version_id") != version_id:
                raise BuildError("Review HUD/blast preset before changing version: " + project)
            result["config/" + destination] = (ROOT / "compat/client-hud" / source).read_bytes()
    incoming = next((mod for mod in cfg.get("external_mods", [])
                     if mod.get("name") == "Incoming: Air Strikes & Nukes"), None)
    if incoming:
        if (incoming.get("version") != "3.10.4" or incoming.get("sha256") !=
                "445c8549f6fec60758b841313adc8d1b58c3770eb4e08bb04c3845e22690d53f"):
            raise BuildError("Review Incoming client preset before changing its file")
        result["config/incoming-client.toml"] = (ROOT / "compat/client-hud/incoming-client.toml").read_bytes()
    return result


def make_mrpack(cfg, mods, output, manual_files=(), external_files=()):
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
    for external in external_files:
        files.append({
            "path": "mods/" + safe_filename(external["filename"]),
            "hashes": external["hashes"],
            "env": {"client": "required", "server": "required"},
            "downloads": [external["url"]],
            "fileSize": external["fileSize"]})
    idx = {"formatVersion": 1, "game": "minecraft", "versionId": cfg["version"],
           "name": cfg["pack_name"], "summary": cfg["description"],
           "files": files,
           "dependencies": {"minecraft": cfg["minecraft"], "neoforge": cfg["loader_version"]}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("modrinth.index.json", json.dumps(idx, ensure_ascii=False, indent=2))
        settings = client_options(cfg)
        if settings:
            archive.writestr("overrides/options.txt", settings)
            archive.writestr("overrides/TECHQUEST_OPTIMIZED.txt",
                "Unified optimized TechQuest client. Iris shaders are not included. "
                "Gameplay mods are preserved. Set graphics Fast, view distance 4-6, "
                "particles minimal. The settings are not a guarantee of FPS gains.\n")
        for relative, data in guide_overrides().items():
            archive.writestr("overrides/" + relative, data)
        for relative, data in client_config_overrides(cfg).items():
            archive.writestr("overrides/" + relative, data)
        # CurseForge-only, All Rights Reserved additions stay user-supplied.
        # Include metadata for the GUI and server operator, never the author JAR.
        local_mods = cfg.get("optional_local_mods", [])
        if local_mods:
            for local_mod in local_mods:
                if (local_mod.get("install_mode") != "manual_user_import" or
                    local_mod.get("loader") != cfg["loader"] or
                    local_mod.get("minecraft") != cfg["minecraft"] or
                    not local_mod.get("source", "").startswith(
                        "https://www.curseforge.com/minecraft/mc-mods/")):
                    raise BuildError("Invalid optional manual mod metadata")
                safe_filename(local_mod["file_name"])
            archive.writestr("overrides/TECHQUEST_OPTIONAL_LOCAL_MODS.json",
                             json.dumps(local_mods, ensure_ascii=False, indent=2) + "\n")
    return len(files)


def client_options(cfg):
    """One options.txt source for .mrpack, generated client and Windows GUI."""
    profile = cfg.get("performance_profile", {})
    lines = ["%s:%s" % item for item in profile.get("video_defaults", {}).items()]
    for name, value in profile.get("key_defaults", {}).items():
        if any(character in name + value for character in ("\n", "\r")) or ":" in name:
            raise BuildError("Invalid keybinding default: " + name)
        lines.append("key_%s:%s" % (name, value))
    if lines:
        # Without this header Minecraft applies pre-1.13 integer-key migrations to
        # modern key.keyboard.* strings and discards the generated options.
        if cfg.get("minecraft") != "1.21.1":
            raise BuildError("Review options.txt DataVersion for this Minecraft version")
        lines.insert(0, "version:3955")
    return ("\n".join(lines) + "\n").encode("utf-8") if lines else b""

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
    external = external_records(cfg)
    write_json(out / "versions-lock.json", {
        "minecraft": cfg["minecraft"], "loader_version": cfg["loader_version"],
        "mods": [{k:m[k] for k in ("requested","title","version","version_id","filename","environment")}
                 for m in resolved], "optional_skipped": optional,
        "manual_mods": [{"name": row["name"], "file_name": row["filename"],
                          "url": row["url"], "hashes": row["hashes"]}
                         for row in manual],
        "external_mods": [{"name": row["name"], "file_name": row["filename"],
                           "url": row["url"], "sha256": row["sha256"],
                           "hashes": row["hashes"]}
                          for row in external]})
    if not args.no_mrpack:
        n = make_mrpack(cfg, resolved, out / "TechQuest_1.21.1_0.3.3_ALPHA.mrpack", manual, external)
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
        expected.update(extra["filename"] for extra in external)
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
    for extra in external:
        (client / extra["filename"]).write_bytes(extra["data"])
        (server / extra["filename"]).write_bytes(extra["data"])
    for jar in server.glob("superbwarfare-*.jar"):
        patch_superb_server_jar(jar)
    if client_options(cfg):
        (out / "client" / "options.txt").write_bytes(client_options(cfg))
    for relative, data in client_config_overrides(cfg).items():
        target = out / "client" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    for relative, data in guide_overrides().items():
        target = out / "client" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if relative.startswith(("config/openloader/", "patchouli_books/techquest_guide/")):
            server_target = out / "server" / relative
            server_target.parent.mkdir(parents=True, exist_ok=True)
            server_target.write_bytes(data)
    (out / "server" / "server.properties").write_text(
        "motd=TechQuest Industrial Frontier\nmax-players=8\nonline-mode=true\n"
        "white-list=true\nenforce-whitelist=true\nenable-rcon=false\n"
        "view-distance=6\nsimulation-distance=5\nallow-flight=true\n", encoding="utf-8")
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

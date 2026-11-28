"""Issue #80: generate reviewed candidate pins, never publish or modify the source manifest."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlsplit
import zipfile

API = "https://api.modrinth.com/v2"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "construction-evidence"
CANDIDATES = (
    ("building-wands", "XkisZUfp", "nvMyIx0w", "3.0.5_beta_neoforge_1.21.1",
     {"client": "required", "server": "required"}, {"9s6osm5g", "lhGA9TYQ"}),
    ("inventory-essentials", "Boon8xwi", "MVsaPKmO", "21.1.14+neoforge-1.21.1",
     {"client": "required", "server": "required"}, {"MBAkmtvl"}),
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected redirect; review official source")


def read(url, host, limit, headers=None):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.netloc != host or parts.username or parts.password:
        raise ValueError("Unexpected source host")
    request = urllib.request.Request(url, headers={
        "User-Agent": "Nessoro-TechQuest/issue-80", **(headers or {})})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Response exceeds size limit")
    return data


def mr(path):
    return json.loads(read(API + path, "api.modrinth.com", 2_000_000))


def check_jar(data):
    with zipfile.ZipFile(io.BytesIO(data)) as jar:
        if "META-INF/neoforge.mods.toml" not in jar.namelist():
            raise ValueError("NeoForge metadata missing")
        metadata = jar.read("META-INF/neoforge.mods.toml").decode("utf-8")
        return metadata


def resolve(cfg, candidate):
    slug, pid, vid, number, sides, expected_deps = candidate
    project = mr("/project/" + pid)
    version = mr("/version/" + vid)
    if (project["id"] != pid or project["slug"] != slug or version["id"] != vid
            or version["project_id"] != pid or version["version_number"] != number
            or "1.21.1" not in version["game_versions"]
            or "neoforge" not in version["loaders"]):
        raise ValueError("Unexpected project/version identity: " + slug)
    deps = [d for d in version["dependencies"] if d["dependency_type"] == "required"]
    if {d.get("project_id") for d in deps} != expected_deps:
        raise ValueError("Dependency changes require review: " + slug)
    for dep in deps:
        pin = cfg["modrinth_lock"][dep["project_id"]]
        if dep.get("version_id") and dep["version_id"] != pin["version_id"]:
            raise ValueError("Existing dependency pin conflict: " + slug)
    files = [f for f in version["files"] if f["primary"] and f["filename"].endswith(".jar")]
    if len(files) != 1:
        raise ValueError("Expected one primary JAR")
    f = files[0]
    if not re.fullmatch(r"[0-9a-f]{128}", f["hashes"]["sha512"]):
        raise ValueError("Invalid SHA-512")
    if not 0 < f["size"] <= 100_000_000:
        raise ValueError("Unexpected JAR size")
    jar = read(f["url"], "cdn.modrinth.com", f["size"])
    if len(jar) != f["size"] or hashlib.sha512(jar).hexdigest() != f["hashes"]["sha512"]:
        raise ValueError("Original JAR hash/size mismatch: " + slug)
    metadata = check_jar(jar)
    if slug == "inventory-essentials":
        with zipfile.ZipFile(io.BytesIO(jar)) as z:
            classes = [z.read(n) for n in z.namelist() if n.endswith(".class")
                       and "config" in n.lower()]
        if not any(b"enableStackRefill" in c and b"enableToolRefill" in c for c in classes):
            raise ValueError("Both refill keys not found in pinned config bytecode")
    row = {"project": slug, "group": "Строительство" if slug == "building-wands"
           else "Интерфейс", "required": True, "version_id": vid, "environment": sides}
    lock = {"title": project["title"], "version": number, "version_id": vid,
            "filename": f["filename"], "sha512": f["hashes"]["sha512"], "environment": sides}
    return row, lock, {"project": pid, "version": vid, "url": f["url"],
                       "size": f["size"], "license": project.get("license"),
                       "dependencies": deps, "upstream_sides": {
                           "client": project.get("client_side"), "server": project.get("server_side")},
                       "metadata": metadata, "lock": lock}


def modrinth():
    cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
    if cfg["minecraft"] != "1.21.1" or cfg["loader"] != "neoforge":
        raise ValueError("Wrong base profile")
    proposed = copy.deepcopy(cfg)
    evidence = []
    for candidate in CANDIDATES:
        row, lock, proof = resolve(cfg, candidate)
        if any(x["project"] == row["project"] for x in proposed["mods"]):
            raise ValueError("Mod already present")
        proposed["mods"].append(row)
        proposed["modrinth_lock"][candidate[1]] = lock
        evidence.append(proof)
    # Candidate only. Do not build/distribute with the inherited version.
    (OUT / "modrinth-evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    (OUT / "modlist.proposed.json").write_text(json.dumps(proposed, ensure_ascii=False, indent=2)+"\n",
                                               encoding="utf-8")
    print("Verified two official JARs; proposed manifest only. Runtime and config schema pending.")


def curseforge():
    key = os.environ.get("CURSEFORGE_API_KEY")
    if not key:
        raise ValueError("Approved CurseForge API key unavailable; no download attempted")
    headers = {"x-api-key": key}
    base = "https://api.curseforge.com/v1/mods/298187"
    project = json.loads(read(base, "api.curseforge.com", 2_000_000, headers))["data"]
    f = json.loads(read(base + "/files/9310471", "api.curseforge.com", 2_000_000, headers))["data"]
    if (project["id"] != 298187 or project.get("allowModDistribution") is not True
            or f["id"] != 9310471 or f["modId"] != 298187
            or f["fileName"] != "buildinggadgets2-21.1.1.jar"
            or "1.21.1" not in f["gameVersions"] or "NeoForge" not in f["gameVersions"]):
        raise ValueError("File identity or distribution permission not verified")
    # Only metadata: the approved source and MRPACK host eligibility need separate review.
    proof = {k: f.get(k) for k in ("id", "modId", "fileName", "gameVersions",
                                   "fileLength", "hashes", "dependencies")}
    proof["allowModDistribution"] = True
    proof["download_url_present"] = bool(f.get("downloadUrl"))
    (OUT / "curseforge-evidence.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    if not proof["download_url_present"]:
        raise ValueError("No authorized download URL returned")
    print("Official metadata verified; JAR hashes and MRPACK delivery not yet verified.")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    if sys.argv[1:] == ["modrinth"]:
        modrinth()
    elif sys.argv[1:] == ["curseforge"]:
        curseforge()
    else:
        raise SystemExit("Usage: audit_construction_80.py modrinth|curseforge")

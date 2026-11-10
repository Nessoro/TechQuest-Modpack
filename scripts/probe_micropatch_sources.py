"""Temporary review: query publicly hosted publisher metadata; no secrets, no downloads from untrusted mirrors."""
import hashlib
import io
import json
import urllib.request
import zipfile

API = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "TechQuest-MicroPatch-Review/1.0"}
TARGETS = {
    "sophisticated-storage": "1.21.1-1.4.21.1123",
    "inventory-profiles-next": "neoforge-1.21.1-2.2.4",
    "libipn": "neoforge-1.21.1-6.6.3",
    "kotlin-for-forge": "",
    "architectury-api": "",
}
PINNED = set(json.load(open("modlist.json", encoding="utf-8"))["modrinth_lock"])

def read(url, limit=20000000):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=65) as conn:
        data = conn.read(limit+1)
    if len(data) > limit: raise ValueError("Unusually large publisher object")
    return data

def api(path, params=None):
    import urllib.parse
    u = API + path
    if params: u += "?" + urllib.parse.urlencode(params)
    return json.loads(read(u))

def project(slug, exact=""):
    meta=api("/project/"+slug)
    versions=api("/project/"+slug+"/version", {"loaders":json.dumps(["neoforge"]), "game_versions":json.dumps(["1.21.1"])})
    choices=[x for x in versions if x["version_type"]=="release" and (not exact or x["version_number"]==exact)]
    if not choices: raise ValueError("No release for "+slug+" at "+exact)
    chosen=max(choices,key=lambda v:v["date_published"])
    entries=[f for f in chosen["files"] if f["filename"].lower().endswith(".jar") and not f["filename"].endswith(("-sources.jar","-javadoc.jar"))]
    f=next((x for x in entries if x.get("primary")), entries[0])
    return {"slug":slug,"id":meta["id"],"title":meta["title"],"version":chosen["version_number"],
            "version_id":chosen["id"],"filename":f["filename"],"sha512":f["hashes"]["sha512"],
            "file_size":f.get("size"),"url":f["url"],"environment":{"client":meta.get("client_side"),"server":meta.get("server_side")},
            "dependencies":[d for d in chosen.get("dependencies",[]) if d.get("dependency_type")=="required"]}

for slug, exact in TARGETS.items():
    try: print("PROBE_MODRINTH",json.dumps(project(slug,exact),separators=(",",":")),flush=True)
    except Exception as exc: print("PROBE_ERROR",slug,repr(exc),flush=True)

# FTB does not publish these artifacts on Modrinth: verify the official Maven files and their SHA-512.
for artifact, ver in (("ftb-library-neoforge","2101.1.39"), ("ftb-ultimine-neoforge","2101.1.15")):
    url="https://maven.ftb.dev/releases/dev/ftb/mods/"+artifact+"/"+ver+"/"+artifact+"-"+ver+".jar"
    try:
        data=read(url,15000000)
        with zipfile.ZipFile(io.BytesIO(data)) as jar:
            names=jar.namelist()
            mods=next((jar.read(x).decode("utf8") for x in ("META-INF/neoforge.mods.toml","META-INF/mods.toml") if x in names),"not found")
        print("PROBE_FTB",json.dumps({"url":url,"file_name":artifact+"-"+ver+".jar","size":len(data),"sha256":hashlib.sha256(data).hexdigest(),"sha512":hashlib.sha512(data).hexdigest(),"mods_toml":mods[:7000]},separators=(",",":")),flush=True)
    except Exception as exc: print("PROBE_ERROR",artifact,repr(exc),flush=True)

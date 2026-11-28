"""Read-only CurseForge consent and checksum probe. Never infer a missing download URL."""
import hashlib
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile

PROJECT=1346094
FILE=9208025
NAME="dragonrise_reforge-1.5.1-release.jar"
EXPECTED_SHA256="80ef4546d78bd7e0d5733ace4aa32448dc3c899905aaedfa2cf0c706538397f9"
API="https://api.curseforge.com/v1"
LIMIT=150_000_000
HOSTS={"mediafilez.forgecdn.net","media.forgecdn.net","edge.forgecdn.net"}

def allowed(url):
    u=urllib.parse.urlsplit(url)
    return (u.scheme=="https" and u.netloc in HOSTS and
            u.path=="/files/9208/25/"+NAME and not u.query and not u.fragment)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class CDNRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed(newurl):
            raise ValueError("Untrusted CDN redirect")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def probe():
    key=os.environ.get("CURSEFORGE_API_KEY")
    if not key:
        raise ValueError("approved CurseForge API key unavailable in workflow secret CURSEFORGE_API_KEY")
    api=urllib.request.build_opener(NoRedirect())
    def get(path):
        request=urllib.request.Request(API+path,headers={"x-api-key":key,"Accept":"application/json"})
        with api.open(request,timeout=30) as response:
            return json.load(response)["data"]
    mod=get(f"/mods/{PROJECT}")
    if mod.get("id")!=PROJECT or mod.get("allowModDistribution") is not True:
        raise ValueError("third-party distribution permission not explicitly true")
    file=get(f"/mods/{PROJECT}/files/{FILE}")
    if file.get("id")!=FILE or file.get("modId")!=PROJECT or file.get("fileName")!=NAME:
        raise ValueError("wrong file identity")
    if not {"1.21.1","NeoForge"}.issubset(set(file.get("gameVersions",[]))):
        raise ValueError("wrong game version or loader")
    if not any(x.get("relationType")==3 for x in file.get("dependencies",[])):
        raise ValueError("required dependency metadata absent")
    url=get(f"/mods/{PROJECT}/files/{FILE}/download-url")
    if not isinstance(url,str) or url!=file.get("downloadUrl") or not allowed(url):
        raise ValueError("authorized download URL absent or outside exact CDN allowlist")
    size=file.get("fileLength")
    if not isinstance(size,int) or not 1024<size<=LIMIT:
        raise ValueError("invalid official file size")
    cdn=urllib.request.build_opener(CDNRedirect())
    with cdn.open(urllib.request.Request(url),timeout=120) as response:
        if not allowed(response.geturl()):
            raise ValueError("unexpected final download URL")
        data=response.read(size+1)
    if len(data)!=size or hashlib.sha256(data).hexdigest()!=EXPECTED_SHA256:
        raise ValueError("original file size/SHA256 does not match audit")
    with zipfile.ZipFile(io.BytesIO(data)) as jar:
        if jar.testzip() is not None or "META-INF/neoforge.mods.toml" not in jar.namelist():
            raise ValueError("invalid NeoForge JAR")
    print(json.dumps({"project":PROJECT,"file":FILE,"filename":NAME,"file_size":size,
                      "sha256":EXPECTED_SHA256,"sha512":hashlib.sha512(data).hexdigest(),
                      "download_url":url,"allowModDistribution":True},indent=2))
    print("Evidence only: review API terms, dependency identity and permitted mrpack delivery before integrating.")

if __name__=="__main__":
    try:
        probe()
    except urllib.error.HTTPError as exc:
        print(f"::warning::DragonRise automatic delivery remains BLOCKED: official endpoint HTTP {exc.code}")
    except ValueError as exc:
        print("::warning::DragonRise automatic delivery remains BLOCKED: "+str(exc))
    except Exception as exc:
        # Do not log request headers, secrets, response bodies or signed URLs.
        print("::warning::DragonRise automatic delivery remains BLOCKED: "+type(exc).__name__)

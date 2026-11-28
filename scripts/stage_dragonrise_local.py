"""Local-only test staging: do not publish the resulting mod directories."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

NAME = "dragonrise_reforge-1.5.1-release.jar"
SHA256 = "80ef4546d78bd7e0d5733ace4aa32448dc3c899905aaedfa2cf0c706538397f9"

def stage(source, output):
    source = Path(source)
    output = Path(output)
    if source.name != NAME or not source.is_file():
        raise ValueError("Expected exact original DragonRise 1.5.1 NeoForge file")
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError("Original JAR hash mismatch")
    with zipfile.ZipFile(source) as z:
        if "META-INF/neoforge.mods.toml" not in z.namelist() or z.testzip() is not None:
            raise ValueError("Invalid original NeoForge JAR")
    targets = [output / side / "mods" / NAME for side in ("client","server")]
    for target in targets:
        if not target.parent.is_dir() or not list(target.parent.glob("superbwarfare-*.jar")):
            raise ValueError("Missing assembled TechQuest profile or Superb Warfare: "+str(target.parent))
        if any(p != target and "dragonrise" in p.name.lower() for p in target.parent.glob("*.jar")):
            raise ValueError("Conflicting DragonRise JAR: "+str(target.parent))
        if target.exists() and target.read_bytes() != data:
            raise ValueError("Refusing to overwrite different existing JAR")
    created = []
    try:
        for target in targets:
            if not target.exists():
                with target.open("xb") as f:
                    created.append(target)
                    f.write(data)
            if hashlib.sha256(target.read_bytes()).hexdigest() != SHA256:
                raise ValueError("Staged JAR hash mismatch")
    except Exception:
        for p in created:
            p.unlink(missing_ok=True)
        raise
    return {"status":"LOCAL_STAGING_ONLY_NOT_DISTRIBUTABLE_NOT_RUNTIME_TESTED",
            "filename":NAME,"file_size":len(data),"sha256":SHA256,
            "sha512":hashlib.sha512(data).hexdigest(),
            "client_jar_count":len(list(targets[0].parent.glob("*.jar"))),
            "server_jar_count":len(list(targets[1].parent.glob("*.jar"))),
            "client_server_identical":True}

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jar",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--report",required=True,type=Path)
    args=parser.parse_args()
    report=stage(args.jar,args.output)
    args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

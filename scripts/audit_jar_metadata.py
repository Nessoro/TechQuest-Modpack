#!/usr/bin/env python3
"""Inspect built NeoForge JAR metadata without loading game code (Python 3.11+).

Checks Minecraft/NeoForge ranges and required mod presence, including declared
Jar-in-Jar mods. This is not a complete mod-version resolver or a runtime test.
"""
import argparse
import io
import json
import re
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FML_SOURCE = ("https://maven.neoforged.net/releases/net/neoforged/"
              "fancymodloader/loader/4.0.45/loader-4.0.45-sources.jar")


def version_key(value):
    """The numeric/release/beta forms used by our Minecraft/NeoForge bounds."""
    match = re.fullmatch(r"(\d+(?:\.\d+)*)(?:-(beta|alpha|rc)(?:[.-]?(\d+))?)?-?", value.strip())
    if not match:
        raise ValueError("Unsupported version bound: " + value)
    numbers = tuple(map(int, match[1].split(".")))
    numbers += (0,) * (8 - len(numbers))
    qualifier = {"alpha": 0, "beta": 1, "rc": 2, None: 3}[match[2]]
    return numbers, qualifier, int(match[3] or 0)


def contains(version, spec):
    """Inclusive/exclusive Maven intervals, exact ranges and interval unions."""
    spec = spec.strip()
    if not spec or spec == "*":
        return True
    if spec[0] not in "[(":
        # A bare Maven version is a recommendation, not a hard restriction.
        return True
    intervals = re.findall(r"[\[(][^\[\]()]*[\])]", spec)
    if not intervals or ",".join(intervals).replace(" ", "") != spec.replace(" ", ""):
        raise ValueError("Unsupported version range: " + spec)
    value = version_key(version)
    for interval in intervals:
        body = interval[1:-1]
        if "," not in body:
            if interval[0] != "[" or interval[-1] != "]":
                raise ValueError("Invalid exact version range: " + interval)
            if value == version_key(body):
                return True
            continue
        low, high = (part.strip() for part in body.split(","))
        if low and (value < version_key(low) or (value == version_key(low) and interval[0] == "(")):
            continue
        if high and (value > version_key(high) or (value == version_key(high) and interval[-1] == ")")):
            continue
        return True
    return False


def supported_versions(cfg, mod_id):
    result = [cfg["minecraft"] if mod_id == "minecraft" else cfg["loader_version"]]
    # Verified in the actual FML bundled by NeoForge 21.1.264, not guessed from
    # Modrinth tags. Do not carry this exception to other loader versions.
    if cfg["minecraft"] == "1.21.1" and cfg["loader_version"] == "21.1.264":
        result.append({"minecraft": "1.21", "neoforge": "21.0.166"}[mod_id])
    return result


def read_metadata(data, origin, depth=0):
    if depth > 8:
        raise ValueError("Jar-in-Jar nesting limit exceeded: " + origin)
    records = []
    with zipfile.ZipFile(io.BytesIO(data)) as jar:
        names = jar.namelist()
        if any(name.endswith(".java") for name in names) and not any(name.endswith(".class") for name in names):
            raise ValueError("Source-only JAR is not a runtime mod: " + origin)
        metadata = next((name for name in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml")
                         if name in jar.namelist()), None)
        if metadata:
            doc = tomllib.loads(jar.read(metadata).decode("utf-8"))
            for mod in doc.get("mods", []):
                records.append({"mod_id": mod["modId"], "origin": origin,
                                "dependencies": doc.get("dependencies", {}).get(mod["modId"], [])})
        if "META-INF/jarjar/metadata.json" in jar.namelist():
            nested = json.loads(jar.read("META-INF/jarjar/metadata.json"))
            for entry in nested.get("jars", []):
                path = entry["path"]
                records.extend(read_metadata(jar.read(path), origin + "!/" + path, depth + 1))
    return records


def check_records(records, cfg, side):
    available = {row["mod_id"] for row in records} | {"minecraft", "neoforge"}
    errors, matrix_matches = [], []
    for row in records:
        for dep in row["dependencies"]:
            if dep.get("side", "BOTH").lower() not in ("both", side):
                continue
            kind = dep.get("type", "required" if dep.get("mandatory", True) else "optional")
            target = dep["modId"]
            identity = {"mod": row["mod_id"], "dependency": target, "origin": row["origin"]}
            if kind == "required" and target not in available:
                errors.append(dict(identity, reason="Required mod is missing"))
            if target not in ("minecraft", "neoforge"):
                continue
            spec = dep.get("versionRange", "*")
            versions = supported_versions(cfg, target)
            try:
                matches = [version for version in versions if contains(version, spec)]
            except ValueError as exc:
                # Unknown syntax must be reviewed, not silently accepted by CI.
                errors.append(dict(identity, range=spec, reason=str(exc)))
                continue
            if kind in ("required", "optional") and not matches:
                errors.append(dict(identity, range=spec, reason="Game/loader range rejected"))
            elif kind == "incompatible" and matches:
                errors.append(dict(identity, range=spec, reason="Game/loader declared incompatible"))
            elif matches and versions[0] not in matches:
                matrix_matches.append(dict(identity, range=spec, accepted_as=matches[0]))
    return {"side": side, "mod_ids": len(available - {"minecraft", "neoforge"}),
            "errors": errors, "fml_matrix_matches": matrix_matches}


def audit(directory, cfg, side):
    records = []
    jars = sorted(directory.glob("*.jar"))
    if not jars:
        raise ValueError("No built JARs found: " + str(directory))
    for jar in jars:
        records.extend(read_metadata(jar.read_bytes(), jar.name))
    result = check_records(records, cfg, side)
    result["jar_files"] = len(jars)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
    result = {"runtime_tested": False, "scope": "Game/loader ranges and required mod presence only",
              "minecraft": cfg["minecraft"], "neoforge": cfg["loader_version"],
              "not_checked": "All inter-mod version ranges, mixin behaviour, gameplay and performance",
              "fml_support_matrix_source": FML_SOURCE,
              "sides": [audit(args.output / side / "mods", cfg, side) for side in ("client", "server")]}
    (args.output / "jar-metadata-audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for side in result["sides"]:
        print(side["side"], "JARs:", side["jar_files"], "errors:", len(side["errors"]),
              "FML compatibility matches:", len(side["fml_matrix_matches"]))
        for error in side["errors"]:
            print(json.dumps(error, ensure_ascii=False))
    return int(any(side["errors"] for side in result["sides"]))


if __name__ == "__main__":
    raise SystemExit(main())

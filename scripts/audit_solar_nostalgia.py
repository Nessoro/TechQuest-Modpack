#!/usr/bin/env python3
"""Isolated, read-only audit of Advanced Solar Panels 1.21.1 against IC2 Nostalgia.

This script never installs, edits or republishes third-party mod JAR files.
It checks the upstream JAR archive, NeoForge metadata and references to IC2
classes against the exact local.26 JAR currently pinned in TechQuest.

Passing static inspection is NOT a Minecraft runtime compatibility guarantee.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import urllib.error
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IC2_JAR = ROOT / "manual-mods" / "industrial-craft-2-nostalgia-21.1.0-local.26.jar"
SOLAR_FILE = "advanced_solar_panels-1.1.8-1.21.1.jar"
SOLAR_FILE_ID = 9525863
SOLAR_PROJECT_ID = 1793968
MAX_JAR_BYTES = 5 * 1024 * 1024

# Official CurseForge CDN paths for the immutable published file ID.
# Do not ever fall back to unverified mirror or execute downloaded Java code.
SOLAR_URLS = (
    "https://mediafilez.forgecdn.net/files/9525/863/" + SOLAR_FILE,
    "https://edge.forgecdn.net/files/9525/863/" + SOLAR_FILE,
    "https://www.curseforge.com/api/v1/mods/1793968/files/9525863/download",
)


class AuditError(RuntimeError):
    pass


def download_solar():
    failures = []
    for url in SOLAR_URLS:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TechQuest-Solar-Compatibility-Audit/1.0 (metadata only)",
                "Accept": "application/java-archive,application/octet-stream,*/*",
            })
            with urllib.request.urlopen(req, timeout=35) as response:
                # A response larger than this budget is never inspected.
                if int(response.headers.get("Content-Length", "0")) > MAX_JAR_BYTES:
                    raise AuditError("Unexpected upstream JAR size")
                data = response.read(MAX_JAR_BYTES + 1)
            if len(data) > MAX_JAR_BYTES:
                raise AuditError("Upstream file exceeded 5 MB")
            if len(data) < 30_000 or not zipfile.is_zipfile(BytesIO(data)):
                raise AuditError("Received HTML or invalid JAR from upstream")
            with zipfile.ZipFile(BytesIO(data)) as archive:
                if archive.testzip() is not None:
                    raise AuditError("Upstream JAR CRC mismatch")
                if not any(x in archive.namelist() for x in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml")):
                    raise AuditError("No NeoForge metadata in upstream JAR")
            return data, url
        except (OSError, ValueError, zipfile.BadZipFile, AuditError) as error:
            failures.append({"url": url, "error": str(error)[:220]})
    raise AuditError("Could not verify original CurseForge JAR: " + json.dumps(failures))


def class_refs_from_bytecode(data):
    """Read CONSTANT_Class names without loading or executing any mod classes."""
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        return set()
    pos = 8
    count = struct.unpack_from(">H", data, pos)[0]
    pos += 2
    utf8 = {}
    class_indices = []
    index = 1
    while index < count:
        tag = data[pos]
        pos += 1
        if tag == 1:  # CONSTANT_Utf8
            length = struct.unpack_from(">H", data, pos)[0]
            pos += 2
            utf8[index] = data[pos:pos + length].decode("utf-8", "replace")
            pos += length
        elif tag == 7:  # CONSTANT_Class
            class_indices.append(struct.unpack_from(">H", data, pos)[0])
            pos += 2
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):  # Long or Double counts as two entries
            pos += 8
            index += 1
        elif tag in (8, 16, 19, 20):
            pos += 2
        elif tag == 15:
            pos += 3
        else:
            raise AuditError(f"Unknown Java class constant pool tag {tag}")
        if pos > len(data):
            raise AuditError("Truncated class constant pool")
        index += 1
    # JVM array types such as '[Lic2/...;' can appear as CONSTANT_Class.
    refs = set()
    for idx in class_indices:
        name = utf8.get(idx, "")
        if name.startswith("ic2/"):
            refs.add(name)
        elif name.startswith("["):
            refs.update("ic2/" + suffix for suffix in re.findall(r"Lic2/([A-Za-z0-9_$/]+);", name))
    return refs


def inspect(jar_data, solar_data, url):
    import hashlib
    if not zipfile.is_zipfile(BytesIO(jar_data)):
        raise AuditError("Pinned IC2 Nostalgia binary is not a valid ZIP/JAR")
    with zipfile.ZipFile(BytesIO(jar_data)) as ic2:
        if ic2.testzip() is not None:
            raise AuditError("IC2 binary CRC failed")
        ic2_classes = {name[:-6] for name in ic2.namelist() if name.endswith(".class")}
        ic2_meta = next((ic2.read(p).decode("utf-8", "replace") for p in (
            "META-INF/neoforge.mods.toml", "META-INF/mods.toml") if p in ic2.namelist()), "")
    if not re.search(r"""modId\s*=\s*["']ic2["']""", ic2_meta):
        raise AuditError("Pinned IC2 Nostalgia does not declare modId ic2")
    with zipfile.ZipFile(BytesIO(solar_data)) as solar:
        meta = next((solar.read(p).decode("utf-8", "replace") for p in (
            "META-INF/neoforge.mods.toml", "META-INF/mods.toml") if p in solar.namelist()), "")
        entries = [p for p in solar.namelist() if p.endswith(".class") and not p.startswith("META-INF/versions/")]
        required_classes = set()
        ic2_mentions = set()
        for path in entries:
            content = solar.read(path)
            required_classes.update(class_refs_from_bytecode(content))
            ic2_mentions.update(part.decode("utf-8", "replace") for part in re.findall(rb"[A-Za-z0-9_/$;:.-]*[iI][cC]2[A-Za-z0-9_/$;:.-]*", content))
        solar_class_examples = entries[:30]
        solar_resource_examples = [p for p in solar.namelist() if "recipe" in p.lower() or "solar" in p.lower()][:35]
    required_classes = {x for x in required_classes if x.startswith("ic2/")}
    missing = sorted(required_classes - ic2_classes)
    return {
        "minecraft_target": "1.21.1",
        "neoforge_target": "21.1.264",
        "ic2_project": "Industrial Craft 2: Nostalgia",
        "ic2_file": IC2_JAR.name,
        "ic2_sha512": hashlib.sha512(jar_data).hexdigest(),
        "ic2_class_count": len(ic2_classes),
        "solar_project": "advanced solar panels Refactored",
        "solar_file_id": SOLAR_FILE_ID,
        "solar_project_id": SOLAR_PROJECT_ID,
        "solar_file": SOLAR_FILE,
        "solar_sha512": hashlib.sha512(solar_data).hexdigest(),
        "solar_verified_upstream_url": url,
        "solar_metadata": meta[:10000],
        "solar_bytecode_classes": len(entries),
        "solar_class_examples": solar_class_examples,
        "solar_resource_examples": solar_resource_examples,
        "solar_ic2_string_mentions": sorted(ic2_mentions)[:90],
        "solar_ic2_class_references": len(required_classes),
        "solar_ic2_missing_class_count": len(missing),
        "solar_ic2_missing_classes": missing,
        "static_class_linkage_possible": bool(required_classes) and not missing,
        "ready_for_distribution": False,
        "runtime_compatible": "NOT_TESTED",
        "warnings": [
            "Static class presence does not check method or field signatures, runtime mixins or energy transfer.",
            "CurseForge describes this release as an addon for IC2 Refactored, NOT Nostalgia.",
            "A separate, lawful source-based port may be necessary if symbols or version constraints differ.",
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", default="output/solar-nostalgia-audit.json")
    args = p.parse_args(argv)
    if not IC2_JAR.is_file():
        raise AuditError("Pinned IC2 Nostalgia JAR missing: " + str(IC2_JAR))
    solar_bytes, url = download_solar()
    report = inspect(IC2_JAR.read_bytes(), solar_bytes, url)
    outfile = ROOT / args.output
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Solar addon official file:", report["solar_file"], report["solar_sha512"])
    print("Solar class files:", report["solar_bytecode_classes"], report["solar_class_examples"][:15])
    print("Solar metadata:", report["solar_metadata"][:1600])
    print("IC2 string mentions:", report["solar_ic2_string_mentions"][:40])
    print("Required IC2 symbols:", report["solar_ic2_class_references"])
    print("Missing IC2 classes in pinned Nostalgia:", report["solar_ic2_missing_class_count"])
    print("Missing class names:", report["solar_ic2_missing_classes"][:60])
    print("Full report:", outfile)
    print("NOT TESTED in real Minecraft; this is only a static class-availability audit.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AuditError as exc:
        print("SOLAR_AUDIT_BLOCKED:", exc, file=sys.stderr)
        sys.exit(1)

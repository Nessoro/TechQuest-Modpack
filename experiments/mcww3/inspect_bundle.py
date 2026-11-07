#!/usr/bin/env python3
"""Read an original McWW3 ZIP/JAR without executing or extracting game code.

Python 3.11+. Produces metadata only; never produces a port or copies assets.
"""
import argparse
import collections
import hashlib
import io
import json
import struct
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

SOURCE_PAGE = "https://mcww3.com/download/2.1-beta"
SOURCE_URL = "https://cdn.mcww3.com/raw/McWW3-Bundle-v2.1-beta.zip?download=true"
TARGET = {"minecraft": "1.21.1", "loader": "neoforge", "loader_version": "21.1.264", "java": 21}
LIMIT = 256 * 1024 * 1024


def safe_members(archive):
    names = set()
    for entry in archive.infolist():
        name = entry.filename
        parts = PurePosixPath(name).parts
        if (name in names or name.startswith("/") or ".." in parts or
                any(token in name for token in ("\\", "\x00", ":"))):
            raise ValueError("Unsafe or duplicate archive entry")
        names.add(name)
        if entry.file_size > LIMIT:
            raise ValueError("Archive member exceeds inspection limit")
    return names


def inspect_jar(data, name):
    if len(data) > LIMIT:
        raise ValueError("JAR exceeds inspection limit")
    with zipfile.ZipFile(io.BytesIO(data)) as jar:
        names = safe_members(jar)
        metadata_path = next((n for n in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml")
                              if n in names), None)
        if metadata_path is None:
            raise ValueError("No Forge/NeoForge metadata in mod JAR")
        if jar.getinfo(metadata_path).file_size > 1024 * 1024:
            raise ValueError("Oversized mod metadata")
        metadata = tomllib.loads(jar.read(metadata_path).decode("utf-8"))
        bytecode = collections.Counter()
        package_counts = collections.Counter()
        references = collections.Counter()
        for entry in jar.infolist():
            if not entry.filename.endswith(".class"):
                continue
            with jar.open(entry) as stream:
                header = stream.read(8)
                if len(header) != 8 or header[:4] != b"\xca\xfe\xba\xbe":
                    raise ValueError("Invalid class header")
                _, _, major = struct.unpack(">IHH", header)
                bytecode[str(major)] += 1
                # Count API coupling without decompilation or publishing class text.
                if entry.file_size > 8 * 1024 * 1024:
                    raise ValueError("Oversized class file")
                body = stream.read()
                for label, token in (("forge", b"net/minecraftforge/"),
                                     ("neoforge", b"net/neoforged/"),
                                     ("minecraft", b"net/minecraft/"),
                                     ("distant_horizons", b"com/seibel/distanthorizons/"),
                                     ("lwjgl", b"org/lwjgl/")):
                    if token in body:
                        references[label] += 1
                package_counts[entry.filename.split("/")[0]] += 1
        licenses = sorted(n for n in names if not n.endswith("/") and
                          any(token in PurePosixPath(n).name.lower() for token in ("license", "copying", "notice")))
        source_files = sorted(n for n in names if n.endswith((".java", "build.gradle", "build.gradle.kts")))
        native_files = sorted(n for n in names if n.lower().endswith((".dll", ".so", ".dylib", ".exe")))
        return {"file": name, "size": len(data), "sha256_observed": hashlib.sha256(data).hexdigest(),
                "metadata_path": metadata_path, "mod_loader": metadata.get("modLoader"),
                "loader_range": metadata.get("loaderVersion"), "declared_license": metadata.get("license"),
                "mods": [{k: mod[k] for k in ("modId", "version", "displayName", "authors", "displayURL") if k in mod}
                         for mod in metadata.get("mods", [])],
                "dependencies": metadata.get("dependencies", {}),
                "class_count": sum(bytecode.values()), "class_file_major_versions": dict(bytecode),
                "top_level_package_class_counts": dict(package_counts),
                "classes_referencing_api_namespace": dict(references),
                "license_notice_paths": licenses, "source_file_count": len(source_files),
                "source_file_examples": source_files[:10], "native_file_count": len(native_files)}


def inspect_bundle(path):
    if path.stat().st_size > LIMIT:
        raise ValueError("Bundle exceeds inspection limit")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    with zipfile.ZipFile(path) as bundle:
        names = safe_members(bundle)
        jars = sorted(n for n in names if n.lower().endswith(".jar"))
        if not jars:
            raise ValueError("No mod JAR in bundle")
        metadata = [inspect_jar(bundle.read(name), name) for name in jars]
        source_files = sorted(n for n in names if n.endswith((".java", "build.gradle", "build.gradle.kts")))
        content_files = [n for n in names if "ww3-content-packs" in PurePosixPath(n).parts and not n.endswith("/")]
        source_count = len(source_files) + sum(jar["source_file_count"] for jar in metadata)
        return {"status": "PREFLIGHT_ONLY_NOT_PORTED", "port_completed": False, "runtime_tested": False,
                "source_page": SOURCE_PAGE, "source_download_url": SOURCE_URL,
                "target": TARGET, "bundle_size": path.stat().st_size,
                "bundle_sha256_observed": digest.hexdigest(),
                "hash_provenance": "Computed after HTTPS download; not an independently published author checksum",
                "jars": metadata, "source_file_count": source_count,
                "source_files_detected": bool(source_count), "buildable_source_project_verified": False,
                "source_review": "File presence alone does not establish a complete buildable project or modification rights",
                "bundle_source_examples": source_files[:10], "content_pack_file_count": len(content_files),
                "distribution_permission_verified": False,
                "next_requirement": "Obtain a complete mod source/build project and review the actual modification/distribution terms"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = inspect_bundle(args.bundle)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"], "JARs:", len(result["jars"]), "source files:", result["source_file_count"])
    for jar in result["jars"]:
        print(jar["file"], "classes:", jar["class_count"], "declared license:", jar["declared_license"])


if __name__ == "__main__":
    main()

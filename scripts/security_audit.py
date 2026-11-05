#!/usr/bin/env python3
"""Reproducible integrity/source audit for all Optimized Minecraft JARs.

This validates signed-by-manifest SHA-1/SHA-512 and scans ZIP integrity. It is
NOT an antivirus. The CI workflow runs ClamAV separately on the downloaded
JARs AND the exact published Windows EXE, then publishes its results.
"""
import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "TechQuest-SecurityAudit/0.1"
HOSTS = {"cdn.modrinth.com", "raw.githubusercontent.com", "github.com"}
AUTHOR_RELEASE = "/zentixua/incoming/releases/download/v3.10.4/incoming-3.10.4.jar"
GITHUB_CDN_HOSTS = {"release-assets.githubusercontent.com", "objects.githubusercontent.com"}
PINNED_GITHUB = re.compile(
    r"^/Nessoro/TechQuest-Modpack/[0-9a-f]{40}/manual-mods/[^/]+\.jar$",
    re.I,
)
LIMIT = 512 * 1024 * 1024


class AuditError(Exception):
    pass


def manifest_entries(paths):
    records = {}
    by_pack = {}
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            index = json.loads(archive.read("modrinth.index.json"))
        if index.get("game") != "minecraft" or index.get("dependencies", {}).get("minecraft") != "1.21.1":
            raise AuditError("Unexpected game/version in " + str(path))
        name = path.name
        by_pack[name] = []
        for item in index["files"]:
            # Scan all files, including server-only entries, not just client-required.
            dest = str(item.get("path", ""))
            if not dest.startswith("mods/") or len(dest.split("/")) != 2 or not dest.endswith(".jar"):
                raise AuditError("Unexpected mod file path: " + dest)
            basename = dest[5:]
            if any(token in basename for token in ("..", "\\", ":", "\x00")):
                raise AuditError("Unsafe mod filename: " + basename)
            urls = item.get("downloads") or []
            if len(urls) != 1:
                raise AuditError("Expected exactly one pinned download URL: " + dest)
            url = urllib.parse.urlsplit(urls[0])
            if url.scheme != "https" or url.hostname not in HOSTS or url.username or url.password:
                raise AuditError("Unexpected download source: " + urls[0])
            if url.hostname == "raw.githubusercontent.com" and not PINNED_GITHUB.fullmatch(url.path):
                raise AuditError("Unpinned or foreign GitHub binary: " + urls[0])
            if url.hostname == "github.com" and (
                    url.path != AUTHOR_RELEASE or url.query or url.fragment):
                raise AuditError("Unexpected GitHub release: " + urls[0])
            hashes = {x: item.get("hashes", {}).get(x) for x in ("sha512", "sha1")}
            if not any(hashes.values()):
                raise AuditError("Missing digest: " + dest)
            for key, value in hashes.items():
                if value and (len(value) != hashlib.new(key).digest_size * 2 or
                              not re.fullmatch("[0-9a-fA-F]+", value)):
                    raise AuditError("Invalid " + key + " digest: " + dest)
            size = item.get("fileSize")
            if not isinstance(size, int) or size <= 1024 or size > LIMIT:
                raise AuditError("File size outside safety bounds: " + dest)
            record = {
                "path": dest, "url": urls[0], "sha1": hashes["sha1"],
                "sha512": hashes["sha512"], "size": size,
            }
            if dest in records and records[dest] != record:
                raise AuditError("Conflicting optimized mod identity: " + dest)
            records[dest] = record
            by_pack[name].append(dest)
    if len(paths) != 1:
        raise AuditError("Exactly one optimized pack is expected")
    return records, by_pack


def download_and_verify(item, directory):
    destination = directory / item["path"].removeprefix("mods/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file():
        temp = destination.with_suffix(destination.suffix + ".partial")
        try:
            for attempt in range(3):
                try:
                    request = urllib.request.Request(item["url"], headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(request, timeout=90) as response:
                        # Never forward a manifest entry to an untrusted redirected host.
                        final_url = urllib.parse.urlsplit(response.geturl())
                        allowed = HOSTS | (GITHUB_CDN_HOSTS
                                           if urllib.parse.urlsplit(item["url"]).hostname == "github.com"
                                           else set())
                        if final_url.scheme != "https" or final_url.hostname not in allowed:
                            raise AuditError("Redirected outside approved hosts: " + str(final_url))
                        with temp.open("wb") as stream:
                            total = 0
                            while chunk := response.read(1024 * 1024):
                                total += len(chunk)
                                if total > LIMIT:
                                    raise AuditError("Oversized binary download")
                                stream.write(chunk)
                    temp.replace(destination)
                    break
                except (OSError, urllib.error.URLError, TimeoutError):
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
        finally:
            temp.unlink(missing_ok=True)
    if destination.stat().st_size != item["size"]:
        raise AuditError("Size mismatch: " + item["path"])
    digests = {alg: hashlib.new(alg) for alg in ("sha256", "sha512", "sha1")}
    with destination.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            for digest in digests.values():
                digest.update(chunk)
    for alg in ("sha512", "sha1"):
        expected = item[alg]
        if expected and digests[alg].hexdigest().lower() != expected.lower():
            raise AuditError("Hash mismatch: " + item["path"])
    try:
        with zipfile.ZipFile(destination) as archive:
            if archive.testzip() is not None:
                raise AuditError("Corrupt ZIP archive inside JAR: " + item["path"])
            embedded = [
                n for n in archive.namelist() if
                n.lower().endswith((".exe", ".dll", ".so", ".dylib", ".ps1", ".bat", ".cmd", ".vbs"))
            ]
    except zipfile.BadZipFile as err:
        raise AuditError("Invalid JAR archive: " + item["path"]) from err
    return {
        "file": item["path"], "size": destination.stat().st_size,
        "sha256": digests["sha256"].hexdigest(),
        "source": urllib.parse.urlsplit(item["url"]).hostname,
        "embedded_executable_count": len(embedded),
        "embedded_examples": embedded[:5],
        "status": "HASH_AND_ARCHIVE_OK",
    }


def audit(pack, directory, report_dir):
    items, packs = manifest_entries([pack])
    directory.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    checked = []
    for i, item in enumerate(items.values(), 1):
        print(f"[{i}/{len(items)}] Verifying {item['path']}", flush=True)
        checked.append(download_and_verify(item, directory))
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit_audit": "Sources restricted to Modrinth, pinned IC2 commit, official Incoming release",
        "pack_mods": len(packs[pack.name]),
        "unique_jar_files": len(items),
        "result": "HASH_AND_ARCHIVE_OK",
        "antivirus_result": "NOT_SCANNED_BY_THIS_SCRIPT",
        "caveat": "Hash verification and ZIP integrity DO NOT establish that code is safe.",
        "files": checked,
    }
    (report_dir / "manifest-integrity.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (report_dir / "manifest-integrity.md").write_text(
        "# TechQuest Optimized integrity audit\n\n" +
        f"- Optimized pack: {result['pack_mods']} JAR entries\n" +
        f"- Unique JAR binaries: {len(items)}\n" +
        "- All files downloaded from allowlisted HTTPS sources\n" +
        "- All manifest hashes and ZIP archives verified\n" +
        "- **This check is not malware detection. See separate ClamAV scan report.**\n",
        encoding="utf-8",
    )
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pack", type=Path, required=True)
    p.add_argument("--mods-dir", type=Path, default=Path("security-work/mods"))
    p.add_argument("--reports", type=Path, default=Path("security-work/reports"))
    args = p.parse_args()
    result = audit(args.pack, args.mods_dir, args.reports)
    print("Source/hash/JAR validation complete for", result["unique_jar_files"], "unique files")


if __name__ == "__main__":
    main()

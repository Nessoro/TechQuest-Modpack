#!/usr/bin/env python3
"""Download only the public dedicated-server JAR, from verified Mojang metadata."""
import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from probe_mojang_metadata import NoRedirect, official_url, probe, valid_sha1

MAX_SERVER_BYTES = 512 * 1024 * 1024


def open_download(url):
    req = urllib.request.Request(official_url(url), headers={"User-Agent": "TechQuest-Horizon-server-prep/1"})
    return urllib.request.build_opener(NoRedirect()).open(req, timeout=60)


def download_server(record, output: Path, opener=open_download):
    url = official_url(record["url"])
    size, sha1 = record["size"], record["sha1"]
    if type(size) is not int or not 0 < size <= MAX_SERVER_BYTES or not valid_sha1(sha1):
        raise ValueError("Invalid official server size/hash")
    if output.exists() or output.is_symlink():
        raise FileExistsError("Refusing to replace an existing server jar")
    output.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1()
    count = 0
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".server-", delete=False) as stream:
            temp = Path(stream.name)
            with opener(url) as response:
                while chunk := response.read(1024 * 1024):
                    count += len(chunk)
                    if count > size:
                        raise ValueError("Official server download exceeds pinned size")
                    digest.update(chunk)
                    stream.write(chunk)
        if count != size or digest.hexdigest() != sha1:
            raise ValueError("Official server download size or SHA-1 mismatch")
        with zipfile.ZipFile(temp) as jar:
            if "META-INF/MANIFEST.MF" not in jar.namelist() or jar.testzip() is not None:
                raise ValueError("Invalid server JAR archive")
        # Atomic no-clobber publication in the same directory.
        os.link(temp, output)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return {"server_jar_verified": True, "server_jar_size": count, "server_jar_sha1": sha1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report = {"schema": 1, "minecraft": "26.3", "server_jar_verified": False,
              "client_jar_downloaded": False, "resources_prepared": False,
              "server_boot_tested": False}
    status = 2
    try:
        metadata = probe("26.3")
        if metadata["java_major"] != 25:
            raise ValueError("Unexpected Java requirement for pinned version")
        report.update(download_server(metadata["downloads"]["server"], args.output))
        report["version_metadata_sha1"] = metadata["version_metadata_sha1"]
        status = 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        report["error"] = str(exc)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())

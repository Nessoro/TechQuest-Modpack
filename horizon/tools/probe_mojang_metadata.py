#!/usr/bin/env python3
"""Probe exact official Minecraft version metadata, not the game or login."""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
HOSTS = {"piston-meta.mojang.com", "piston-data.mojang.com",
         "launchermeta.mojang.com", "launcher.mojang.com", "resources.download.minecraft.net"}
MAX_METADATA = 16 * 1024 * 1024


def official_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.netloc != parsed.hostname
            or parsed.query or parsed.fragment):
        raise ValueError("Unexpected official download URL")
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected metadata redirect")


def get_metadata(url):
    request = urllib.request.Request(official_url(url), headers={"User-Agent": "TechQuest-Horizon-metadata-probe/1"})
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
        raw = response.read(MAX_METADATA + 1)
    if len(raw) > MAX_METADATA:
        raise ValueError("Metadata too large")
    return raw


def valid_sha1(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{40}", value) is not None


def probe(version, fetch=get_metadata):
    catalog = json.loads(fetch(MANIFEST))
    rows = [v for v in catalog["versions"] if v.get("id") == version]
    if len(rows) != 1:
        raise ValueError("Exact requested Minecraft version not uniquely present in official catalog")
    row = rows[0]
    if not valid_sha1(row.get("sha1")):
        raise ValueError("Missing official version metadata SHA-1")
    raw = fetch(official_url(row["url"]))
    if hashlib.sha1(raw).hexdigest() != row["sha1"]:
        raise ValueError("Official version metadata SHA-1 mismatch")
    metadata = json.loads(raw)
    if metadata.get("id") != version:
        raise ValueError("Official version metadata ID mismatch")
    downloads = {}
    for key in ("client", "server"):
        record = metadata["downloads"][key]
        size = record.get("size")
        if not valid_sha1(record.get("sha1")) or type(size) is not int or size <= 0:
            raise ValueError("Invalid official " + key + " download metadata")
        downloads[key] = {"url": official_url(record["url"]), "sha1": record["sha1"], "size": size}
    return {"schema": 1, "minecraft": version, "version_metadata_sha1": row["sha1"],
            "version_metadata_verified": True, "java_major": metadata.get("javaVersion", {}).get("majorVersion"),
            "downloads": downloads, "game_files_downloaded": False,
            "resources_prepared": False, "server_boot_tested": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = probe(args.version)
        status = 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {"schema": 1, "minecraft": args.version, "version_metadata_verified": False,
                  "error": str(exc), "game_files_downloaded": False,
                  "resources_prepared": False, "server_boot_tested": False}
        status = 2
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())

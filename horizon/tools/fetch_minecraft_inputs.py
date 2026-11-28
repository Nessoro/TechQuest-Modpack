#!/usr/bin/env python3
"""Fetch verified official 26.3 inputs into a separate developer cache.

Does not sign in, prepare resources, accept EULA, start a server or touch an
existing launcher installation. Requires the pinned upstream research-lock.json.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.error import HTTPError

VERSION = "26.3"
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
HOSTS = {"piston-meta.mojang.com", "piston-data.mojang.com",
         "libraries.minecraft.net", "resources.download.minecraft.net"}


def read_url(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS or parsed.username:
        raise ValueError("expected an official HTTPS download URL")
    with urlopen(url, timeout=90) as response:
        if urlparse(response.url).hostname not in HOSTS:
            raise ValueError("unexpected download redirect")
        return response.read()


def verify(data: bytes, record: dict) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", record["sha1"]):
        raise ValueError("invalid SHA-1 record")
    if len(data) != record.get("size", len(data)) or hashlib.sha1(data).hexdigest() != record["sha1"]:
        raise ValueError("download size or SHA-1 mismatch")


def destination(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or root.resolve() not in path.resolve().parents:
        raise ValueError("download path escapes the isolated cache")
    return path


def fetch(record: dict, path: Path) -> bytes:
    if path.is_file():
        data = path.read_bytes()
        try:
            verify(data, record)
            return data
        except ValueError:
            pass
    for attempt in range(3):
        try:
            data = read_url(record["url"])
            verify(data, record)
            break
        except HTTPError as exc:
            if attempt == 2 or exc.code not in (429, 500, 502, 503, 504):
                raise
            delay = exc.headers.get("Retry-After", "")
            time.sleep(int(delay) if delay.isdigit() else attempt + 1)
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(data)
    temporary.replace(path)
    return data


def run(cache: Path, lock: dict, jobs: int = 6) -> dict:
    pin = lock["minecraft"]
    if pin["version"] != VERSION or pin["java_major"] != 25:
        raise ValueError("expected the pinned Horizon 26.3 / Java 25 lock")
    # Marker prevents accidental modification of an installed launcher directory.
    marker = cache / ".techquest-input-cache"
    if cache.exists() and any(cache.iterdir()) and not marker.is_file():
        raise ValueError("cache must be new, empty or created by this tool")
    cache.mkdir(parents=True, exist_ok=True)
    marker.touch()
    versions = json.loads(read_url(MANIFEST))["versions"]
    version = next(v for v in versions if v["id"] == VERSION)
    if version["sha1"] not in [pin["manifest_sha1"], *pin.get("accepted_manifest_sha1", [])]:
        raise ValueError("Mojang metadata changed: review upstream lock before downloading")
    metadata = json.loads(fetch(version, destination(cache, f"versions/{VERSION}/{VERSION}.json")))
    tasks = []
    for kind in ("client", "server"):
        record = metadata["downloads"][kind]
        if record["sha1"] != pin[f"{kind}_sha1"]:
            raise ValueError("game JAR differs from pinned upstream")
        name = f"{VERSION}.jar" if kind == "client" else "server.jar"
        tasks.append((record, destination(cache, f"versions/{VERSION}/{name}")))
    for library in metadata["libraries"]:
        record = library.get("downloads", {}).get("artifact")
        if record:
            tasks.append((record, destination(cache, "libraries/" + record["path"])))
    index_record = metadata["assetIndex"]
    if index_record["sha1"] not in pin["accepted_asset_index_sha1"]:
        raise ValueError("asset index differs from pinned upstream")
    index = json.loads(fetch(index_record, destination(cache, f"assets/indexes/{index_record['id']}.json")))
    objects = {v["hash"]: v["size"] for v in index["objects"].values()}
    for sha1, size in objects.items():
        if not re.fullmatch(r"[0-9a-f]{40}", sha1):
            raise ValueError("invalid asset hash")
        suffix = f"{sha1[:2]}/{sha1}"
        tasks.append(({"url": f"https://resources.download.minecraft.net/{suffix}",
                       "sha1": sha1, "size": size}, destination(cache, f"assets/objects/{suffix}")))
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        # Keep only byte counts, not the entire asset store, in memory.
        list(pool.map(lambda task: len(fetch(*task)), tasks))
    return {"minecraft": VERSION, "verified_downloads": len(tasks) + 2,
            "resources_prepared": False, "server_boot_tested": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--research-lock", type=Path, required=True)
    parser.add_argument("--jobs", type=int, choices=range(1, 9), default=6)
    args = parser.parse_args()
    print(json.dumps(run(args.cache, json.loads(args.research_lock.read_text()), args.jobs), indent=2))


if __name__ == "__main__":
    main()

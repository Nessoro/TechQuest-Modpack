#!/usr/bin/env python3
"""Assemble missing append-only YUNG tags locally; report metadata, never gameplay success.

The official carry deliberately drops a namespace claimed by several mods.
These four reviewed tag files can be merged into two tags with one namespace owner.
All other outside files remain untouched and visible in the audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import tomllib
from collections import Counter
from pathlib import Path

MODULE = "techquest_yungs_shared"
SOURCES = ("betterdungeons", "betterfortresses")
TAGS = ("remove_basalt_columns_feature_in", "remove_delta_feature_in")
RESOURCE = re.compile(r"#?[a-z0-9_.-]+:[a-z0-9_./-]+\Z")


def tag_path(name: str) -> Path:
    return Path("data/yungsapi/tags/worldgen/structure") / (name + ".json")


def checked_bytes(path: Path, base: Path) -> bytes:
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != base.parent):
        raise ValueError("Symlink in reviewed input: " + str(path))
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Missing or oversized reviewed tag: " + str(path))
    return path.read_bytes()


def merge_tags(payloads: list[bytes]) -> dict:
    values = []
    for payload in payloads:
        tag = json.loads(payload)
        if (not isinstance(tag, dict) or set(tag) - {"replace", "values"}
                or tag.get("replace", False) is not False or not isinstance(tag.get("values"), list)):
            raise ValueError("Only reviewed append-only tags can be merged")
        for value in tag["values"]:
            if not isinstance(value, str) or not RESOURCE.fullmatch(value) or ".." in value:
                raise ValueError("Review unsupported tag entry before assembly")
            if value not in values:
                values.append(value)
    if not values:
        raise ValueError("Refusing an empty recovered tag")
    return {"replace": False, "values": values}


def assemble(work: Path) -> dict:
    work = work.resolve()
    mods = work / "mods"
    target = mods / MODULE
    if target.exists() or target.is_symlink():
        raise ValueError("Refusing to overwrite an existing shared module")
    # Namespace ownership is a pack-wide invariant, independent of individual SDK checks.
    for manifest in sorted(mods.glob("*/carry/horizon-mod.toml")):
        meta = tomllib.loads(checked_bytes(manifest, work).decode())
        if meta.get("id") == "yungsapi" or "yungsapi" in meta.get("namespaces", []):
            raise ValueError("Existing yungsapi namespace owner: " + str(manifest))
    source_rows, merged, recovered = [], {}, set()
    for name in TAGS:
        relative = tag_path(name)
        payloads = []
        for module in SOURCES:
            source = mods / module / "outside" / relative
            data = checked_bytes(source, work)
            payloads.append(data)
            recovered.add(source.relative_to(work).as_posix())
            source_rows.append({"module": module, "path": relative.as_posix(),
                                "sha256": hashlib.sha256(data).hexdigest()})
        merged[relative] = (json.dumps(merge_tags(payloads), indent=2) + "\n").encode()
    outside = []
    for path in sorted(mods.glob("*/outside")):
        if path.is_symlink():
            raise ValueError("Symlink outside directory")
        for file in sorted(path.rglob("*")):
            if file.is_symlink():
                raise ValueError("Symlink outside input")
            if not file.is_file():
                continue
            relative = file.relative_to(work).as_posix()
            inner = file.relative_to(path).as_posix()
            namespace = inner.split("/")[1] if inner.startswith(("data/", "assets/")) else "metadata"
            status = "recovered_shared_tag" if relative in recovered else "needs_review"
            outside.append({"module": path.parent.name, "path": inner,
                            "namespace": namespace, "status": status})
    # Validate everything before creating output. Original files stay byte-for-byte intact.
    with tempfile.TemporaryDirectory(prefix=".shared-tags-", dir=mods) as temporary:
        staging = Path(temporary) / MODULE
        carry = staging / "carry"
        carry.mkdir(parents=True)
        for relative, data in merged.items():
            destination = carry / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        (carry / "horizon-mod.toml").write_text(
            'id = "techquest_yungs_shared"\nname = "TechQuest shared YUNG tags"\n'
            'version = "0.1.0"\napi = "0.2"\nside = "both"\n'
            'capabilities = ["registries"]\nnamespaces = ["yungsapi"]\n'
            'license = "LGPL-3.0-only"\n', encoding="utf-8")
        staging.rename(target)
    return {"schema": 1, "purpose": "local_shared_tag_assembly_and_loss_audit",
            "module": MODULE, "source_files": source_rows,
            "merged_tags": [{"path": path.as_posix(), "sha256": hashlib.sha256(data).hexdigest()}
                            for path, data in merged.items()],
            "outside_count": len(outside), "outside": outside,
            "outside_status_counts": dict(Counter(row["status"] for row in outside)),
            "sdk_validated": False, "runtime_tested": False, "gameplay_ported": False,
            "third_party_files_redistributed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = assemble(args.work)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f'{len(report["source_files"])} source tags -> {len(report["merged_tags"])} shared tags; '
          f'{report["outside_status_counts"]}. SDK and gameplay not validated by this script.')


if __name__ == "__main__":
    main()

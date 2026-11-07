#!/usr/bin/env python3
"""Run official Horizon content SDK against locally carried YUNG data-tier mods.

The converted files remain in an ephemeral runner; output is metadata only.
A successful SDK check does not prove in-game worldgen or a complete port.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from pathlib import Path

IDS = ("betterdungeons", "betterstrongholds", "bettermineshafts", "betterfortresses")


def inspect_one(work: Path, sdk: Path, mod_id: str) -> dict:
    carry = work / "mods" / mod_id / "carry"
    row = {
        "mod_id": mod_id,
        "sdk_validated": False,
        "runtime_tested": False,
        "gameplay_ported": False,
        "result": "not_checked",
        "files": 0,
    }
    if not carry.is_dir():
        row["result"] = "missing_carry"
        return row
    row["files"] = sum(1 for p in carry.rglob("*") if p.is_file())
    manifest = carry / "horizon-mod.toml"
    if not manifest.is_file():
        row["result"] = "missing_manifest"
        return row
    try:
        meta = tomllib.loads(manifest.read_text(encoding="utf-8"))
        row["api"] = meta.get("api")
        row["side"] = meta.get("side")
        row["version"] = meta.get("version")
        if meta.get("id") != mod_id or meta.get("api") != "0.2":
            row["result"] = "invalid_manifest"
            return row
        build = subprocess.run(
            [str(sdk), "build"], cwd=carry, capture_output=True, text=True, timeout=180,
            check=False,
        )
        if build.returncode:
            row["result"] = "sdk_build_failed"
            row["message"] = (build.stdout + build.stderr)[-1200:]
            return row
        package = carry / "target" / "horizon-mod" / (mod_id + ".hmod")
        if not package.is_file():
            row["result"] = "sdk_package_missing"
            return row
        check = subprocess.run(
            [str(sdk), "check", str(package), "--json"],
            cwd=carry, capture_output=True, text=True, timeout=180, check=False,
        )
        try:
            verdict = json.loads(check.stdout)
        except json.JSONDecodeError:
            row["result"] = "sdk_check_invalid_json"
            row["message"] = (check.stdout + check.stderr)[-1200:]
            return row
        if check.returncode or not verdict.get("ok"):
            row["result"] = "sdk_check_failed"
            row["message"] = str(verdict.get("error", check.stderr))[-1200:]
            return row
        facts = verdict.get("report", {})
        if facts.get("id") != mod_id or facts.get("api") != "0.2":
            row["result"] = "sdk_report_mismatch"
            return row
        row["result"] = "sdk_validated"
        row["sdk_validated"] = True
        row["sdk_sha256"] = facts.get("sha256")
        row["size_bytes"] = facts.get("size")
        return row
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        row["result"] = "exception"
        row["message"] = str(exc)[-700:]
        return row


def validate(work: Path, sdk: Path) -> dict:
    sdk = sdk.resolve()
    if not sdk.is_file():
        raise FileNotFoundError("Official Horizon SDK binary not found: " + str(sdk))
    rows = [inspect_one(work, sdk, ident) for ident in IDS]
    return {
        "schema": 1,
        "purpose": "official_sdk_content_structure_validation",
        "horizon_game": "26.3",
        "horizon_runtime_tested": False,
        "third_party_code_migrated": False,
        "all_sdk_valid": all(r["sdk_validated"] for r in rows),
        "sdk_valid_count": sum(r["sdk_validated"] for r in rows),
        "sdk_invalid_count": sum(not r["sdk_validated"] for r in rows),
        "modules": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = validate(args.work.resolve(), args.sdk)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in report["modules"]:
        print(f'{row["mod_id"]}: {row["result"]} ({row["files"]} source files)')
        if row.get("message"):
            print("  ", row["message"][:400])
    print(f'Official SDK validated: {report["sdk_valid_count"]}/4; in-game worlds tested: NO.')
    return 0 if report["all_sdk_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

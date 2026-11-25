#!/usr/bin/env python3
"""Fail closed if a new TechQuest build reuses a reserved candidate number.

Legacy candidates through 0.3.3.4 were issued before this guard. Every newer
Build TechQuest alpha run reserves its version on first use, even if cancelled.
A retry of the original head SHA may retain that version.
"""
import base64
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

BASELINE = 4
FIRST_GUARDED_RUN = 602
HISTORY_START = "2026-11-25T19:57:43Z"
ROOT = Path(__file__).resolve().parents[1]


def patch_number(version):
    match = re.fullmatch(r"0\.3\.3\.([1-9][0-9]*)", version)
    return int(match.group(1)) if match else None


def check_reservation(version, sha, history):
    """History tuples: (workflow run_number, exact source SHA, pack version)."""
    number = patch_number(version)
    if number is None or number <= BASELINE:
        raise ValueError("Use a new four-part version above 0.3.3.4")
    reserved = {}
    highest = BASELINE
    for _, old_sha, old_version in sorted(history):
        n = patch_number(old_version)
        if n is None or n <= BASELINE:
            continue
        if n > highest:
            reserved[n] = old_sha
            highest = n
        # Repeated and out-of-order attempts never change the first reservation.
    if number in reserved:
        if reserved[number] != sha:
            raise ValueError(f"{version} is already reserved by {reserved[number]}; use 0.3.3.{highest + 1}")
        return
    if number <= highest:
        raise ValueError(f"{version} is out of order; use 0.3.3.{highest + 1}")


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    sha = os.environ["TECHQUEST_SOURCE_SHA"]
    run_id = int(os.environ["GITHUB_RUN_ID"])
    run_number = int(os.environ["GITHUB_RUN_NUMBER"])
    if run_number < FIRST_GUARDED_RUN:
        raise ValueError("Version guard must run on a new workflow execution")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != sha:
        raise ValueError("Checkout differs from the source commit used for version reservation")
    version = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))["version"]

    def get(path, query=None):
        url = os.environ.get("GITHUB_API_URL", "https://api.github.com") + "/repos/" + repo + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "TechQuest-version-guard",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    runs = []
    found_current = False
    for page in range(1, 12):
        result = get("/actions/workflows/build-alpha.yml/runs", {
            "created": ">=" + HISTORY_START, "per_page": 100, "page": page,
        })
        if result["total_count"] > 1000:
            raise ValueError("Build history API limit reached; extend the durable reservation baseline before building")
        entries = result["workflow_runs"]
        for row in entries:
            if row["id"] == run_id:
                found_current = True
            if FIRST_GUARDED_RUN <= row["run_number"] < run_number:
                runs.append((row["run_number"], row["head_sha"]))
        if len(entries) < 100:
            break
    else:
        raise ValueError("Unable to enumerate complete build history")
    if not found_current:
        raise ValueError("Current workflow is not visible in history; retry this exact commit")
    versions = {}
    for _, old_sha in runs:
        if old_sha not in versions:
            data = get("/contents/modlist.json", {"ref": old_sha})
            if data.get("encoding") != "base64":
                raise ValueError("Cannot read prior build manifest " + old_sha)
            manifest = json.loads(base64.b64decode(data["content"]))
            versions[old_sha] = manifest["version"]
    history = [(n, old_sha, versions[old_sha]) for n, old_sha in runs]
    check_reservation(version, sha, history)
    print(f"Version reservation OK: {version}, source {sha}, workflow run {run_number}")


if __name__ == "__main__":
    main()

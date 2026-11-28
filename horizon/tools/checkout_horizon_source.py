#!/usr/bin/env python3
"""Prepare one exact Horizon build source from the verified mirror or a local Git bundle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

SOURCE_LOCK = Path(__file__).resolve().parents[1] / "source/upstream-build-sources.json"


def checkout(name, output, bundle=None):
    source = json.loads(SOURCE_LOCK.read_text())[name]
    if bundle is None and "mirror" not in source:
        raise ValueError(f"{name} requires a local Git bundle")
    output = output.absolute()
    if output.exists() or any(path.is_symlink() for path in (output, *output.parents)):
        raise ValueError("output must be a new path without symlinks")
    if bundle is not None:
        bundle = bundle.resolve(strict=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1")

    with tempfile.TemporaryDirectory(prefix="horizon-source-", dir=output.parent) as tmp:
        repo = Path(tmp) / "source"
        repo.mkdir()

        def git(*args, capture=False):
            return subprocess.run(
                ["git", "-c", "core.hooksPath=/dev/null", *args],
                cwd=repo, env=env, check=True, stdout=subprocess.PIPE if capture else None,
            ).stdout

        pin = source["commit"]
        git("init", "--quiet")
        if bundle is None:
            git("fetch", "--no-tags", "--depth=1", "--no-recurse-submodules", source["mirror"], pin)
            if git("rev-parse", "FETCH_HEAD", capture=True).decode().strip() != pin:
                raise ValueError("mirror did not fetch the pinned commit")
        else:
            git("bundle", "verify", str(bundle))
            git("bundle", "unbundle", str(bundle), capture=True)
        if git("rev-parse", f"{pin}^{{tree}}", capture=True).decode().strip() != source["tree"]:
            raise ValueError("source tree differs from the lock")
        for path, field in (("Cargo.lock", "cargo_lock_sha256"), ("LICENSE", "license_sha256")):
            if hashlib.sha256(git("show", f"{pin}:{path}", capture=True)).hexdigest() != source[field]:
                raise ValueError(f"{path} differs from the lock")
        git("checkout", "--quiet", "--detach", pin)
        repo.rename(output)
    print(f"Verified {name} {pin} at {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=("horizon", "mixins"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--bundle", type=Path, help="offline input instead of the verified mirror")
    args = parser.parse_args()
    checkout(args.name, args.output, args.bundle)


if __name__ == "__main__":
    main()

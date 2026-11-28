"""Require verified source identity before creating the checkout."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import checkout_horizon_source as recovery


class CheckoutHorizonSourceTests(unittest.TestCase):
    def setUp(self):
        fixture = tempfile.TemporaryDirectory()
        self.addCleanup(fixture.cleanup)
        self.root = Path(fixture.name)
        local = self.root / "upstream"
        local.mkdir()

        def git(*args):
            return subprocess.check_output(
                ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgSign=false", *args], cwd=local,
            ).decode().strip()

        git("init", "--quiet", "--initial-branch=main")
        self.bundle = self.root / "source.bundle"
        self.source = {}
        for name, key in (("Cargo.lock", "cargo_lock_sha256"), ("LICENSE", "license_sha256")):
            data = name.encode()
            (local / name).write_bytes(data)
            self.source[key] = hashlib.sha256(data).hexdigest()
        git("add", "Cargo.lock", "LICENSE")
        git("commit", "--quiet", "-m", "Fixture source")
        self.source["commit"] = git("rev-parse", "HEAD")
        self.source["tree"] = git("rev-parse", "HEAD^{tree}")
        git("bundle", "create", str(self.bundle), "--all")
        self.lock = self.root / "lock.json"
        self.output = self.root / "checkout"
        mock = patch.object(recovery, "SOURCE_LOCK", self.lock)
        mock.start()
        self.addCleanup(mock.stop)

    def checkout(self):
        self.lock.write_text(json.dumps({"horizon": self.source}))
        with redirect_stdout(io.StringIO()):
            recovery.checkout("horizon", self.output, self.bundle)

    def test_complete_bundle_restores_exact_checkout(self):
        self.checkout()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.output)
        self.assertEqual(head.decode().strip(), self.source["commit"])

    def test_wrong_tree_never_creates_checkout(self):
        self.source["tree"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "source tree differs"):
            self.checkout()
        self.assertFalse(self.output.exists())

    def test_wrong_cargo_lock_never_creates_checkout(self):
        self.source["cargo_lock_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Cargo.lock differs"):
            self.checkout()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

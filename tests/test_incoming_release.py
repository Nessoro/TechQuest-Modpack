"""Incoming is pinned to the official author's GitHub release and cannot drift."""
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("incoming_builder", ROOT / "build_pack.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class IncomingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))

    @staticmethod
    def fake_archive():
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("META-INF/neoforge.mods.toml",
                       'modLoader="javafml"\n[[mods]]\nmodId="incoming"\n')
            z.writestr("assets/incoming/dummy", b"".join(
                hashlib.sha256(str(i).encode()).digest() for i in range(160)))
        return out.getvalue()

    def test_pin_and_loader_bumped(self):
        self.assertEqual(self.cfg["loader_version"], "21.1.264")
        self.assertEqual(self.cfg["version"], "0.3.2-alpha")
        mods = self.cfg["external_mods"]
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0]["name"], "Incoming: Air Strikes & Nukes")
        self.assertEqual(mods[0]["version"], "3.10.4")
        self.assertTrue(mods[0]["required"])
        self.assertIn("/v3.10.4/incoming-3.10.4.jar", mods[0]["download_url"])

    def test_official_release_is_hash_verified(self):
        data = self.fake_archive()
        ext = dict(self.cfg["external_mods"][0])
        ext["sha256"] = hashlib.sha256(data).hexdigest()
        ext["file_size"] = len(data)
        with patch.object(build, "get_url", return_value=data):
            rows = build.external_records({"external_mods": [ext]})
        self.assertEqual(rows[0]["filename"], "incoming-3.10.4.jar")
        self.assertEqual(rows[0]["hashes"]["sha512"], hashlib.sha512(data).hexdigest())

    def test_mrpack_installs_incoming_on_both_sides(self):
        data = self.fake_archive()
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "test.mrpack"
            extra = [{
                "filename": "incoming-3.10.4.jar",
                "url": self.cfg["external_mods"][0]["download_url"],
                "hashes": {"sha1": hashlib.sha1(data).hexdigest(),
                           "sha512": hashlib.sha512(data).hexdigest()},
                "fileSize": len(data)
            }]
            count = build.make_mrpack(self.cfg, [], file, external_files=extra)
            with zipfile.ZipFile(file) as z:
                index = json.loads(z.read("modrinth.index.json"))
            self.assertEqual(count, 1)
            record = index["files"][0]
            self.assertEqual(record["path"], "mods/incoming-3.10.4.jar")
            self.assertEqual(record["env"], {"client": "required", "server": "required"})
            self.assertEqual(index["dependencies"]["neoforge"], "21.1.264")

    def test_reject_wrong_digest(self):
        ext = dict(self.cfg["external_mods"][0])
        ext["file_size"] = len(self.fake_archive())
        with patch.object(build, "get_url", return_value=self.fake_archive()):
            with self.assertRaises(build.BuildError):
                build.external_records({"external_mods": [ext]})

    def test_reject_foreign_url(self):
        ext = dict(self.cfg["external_mods"][0])
        ext["download_url"] = "https://example.invalid/incoming.jar"
        with self.assertRaises(build.BuildError):
            build.external_records({"external_mods": [ext]})


if __name__ == "__main__":
    unittest.main()

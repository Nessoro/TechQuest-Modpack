"""TechQuest issue #56: BetterBlockZ 0.2.10 NeoForge 1.21.1.

This module verifies our reproducible manifest and website configuration;
it cannot replace a gameplay test. An official Modrinth JAR download and
SHA-512 comparison completed in GitHub Actions run 44538258165.
"""
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "oPU4euBQ"
VERSION = "7E52UnH3"
SLUG = "betterblockz"
VERSION_NUMBER = "0.2.10-1.21.1-neoforge"
FILENAME = "betterblockz-0.2.10-1.21.1-neoforge.jar"
SHA512 = "aa68aea80c5ab0c3d02ea41bb3eaafc3d29e23502dbfb24e7fd470a920ccf07f1fc91acc7c29268324a8ba9f4b09ce48b140ed053f9570982cbefbf55807b8f3"
SIDES = {"client": "required", "server": "required"}


class BetterBlockZTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = cls.cfg["mods"]
        cls.lock = cls.cfg["modrinth_lock"]

    def test_expected_platform_and_preserved_mods(self):
        self.assertEqual(("1.21.1", "neoforge", "21.1.264"),
                         (self.cfg["minecraft"], self.cfg["loader"], self.cfg["loader_version"]))
        self.assertEqual(82, len(self.mods))
        for slug in ("create", "mekanism", "oritech", "ae2", "refined-storage",
                     "interdimensional-wireless-transmitter", "refined-storage-quartz-arsenal"):
            self.assertEqual(1, sum(m["project"] == slug for m in self.mods), slug)

    def test_official_release_exact_pin_and_sides(self):
        rows = [m for m in self.mods if m["project"] == SLUG]
        self.assertEqual(1, len(rows))
        self.assertTrue(rows[0]["required"])
        self.assertEqual("Декор", rows[0]["group"])
        self.assertEqual(VERSION, rows[0]["version_id"])
        self.assertEqual(SIDES, rows[0]["environment"])
        self.assertFalse(rows[0].get("client_only", False))
        entry = self.lock[PROJECT]
        self.assertEqual("BetterBlockZ", entry["title"])
        self.assertEqual(VERSION_NUMBER, entry["version"])
        self.assertEqual(VERSION, entry["version_id"])
        self.assertEqual(FILENAME, entry["filename"])
        self.assertEqual(SHA512, entry["sha512"])
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{128}", entry["sha512"]))
        self.assertEqual(SIDES, entry["environment"])

    def test_retained_athena_is_client_only_not_installed_twice(self):
        # The official 0.2.10 Modrinth release lists no mandatory dependencies.
        # Athena is already pinned for other mods; it provides optional CTM support.
        self.assertEqual(1, sum(m["project"] == "b1ZV3DIJ" for m in self.mods))
        athena = self.lock["b1ZV3DIJ"]
        self.assertEqual("4.0.6", athena["version"])
        self.assertEqual({"client": "required", "server": "unsupported"}, athena["environment"])
        self.assertEqual("dJgL278E", athena["version_id"])

    def test_mrpack_keeps_original_modrinth_download_outside_overrides(self):
        record = {
            "filename": FILENAME, "environment": SIDES,
            "file": {
                "filename": FILENAME,
                "hashes": {"sha512": SHA512},
                "url": f"https://cdn.modrinth.com/data/{PROJECT}/versions/{VERSION}/{FILENAME}",
                "size": 7388885,
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.mrpack"
            build_pack.make_mrpack(self.cfg, [record], path)
            with zipfile.ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                files = json.loads(archive.read("modrinth.index.json"))["files"]
                rows = [row for row in files if row["path"] == "mods/" + FILENAME]
                self.assertEqual(1, len(rows))
                self.assertEqual(SHA512, rows[0]["hashes"]["sha512"])
                self.assertEqual(SIDES, rows[0]["env"])
                self.assertNotIn("overrides/mods/" + FILENAME, archive.namelist())

    def test_site_and_no_source_binaries(self):
        source = (ROOT / "scripts" / "sync_site_mods.py").read_text(encoding="utf-8")
        site = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('"betterblockz": "BetterBlockZ"', source)
        self.assertIn("https://modrinth.com/mod/betterblockz", site)
        for folder in (ROOT / "mods", ROOT / "manual-mods", ROOT / "overrides" / "mods"):
            if folder.exists():
                self.assertFalse(list(folder.rglob(FILENAME)), folder)


if __name__ == "__main__":
    unittest.main()

"""TechQuest issue #54: Refined Storage Quartz Arsenal 1.0.8.

The official NeoForge 1.21.1 JAR and Modrinth SHA-512 were independently
verified in GitHub Actions run 44505908861. Real wireless crafting,
power behavior, dimension access and dedicated-server gameplay still
require separate playtesting.
"""
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "gnwGOmBf"
SLUG = "refined-storage-quartz-arsenal"
VERSION = "toDdIhGu"
FILENAME = "refinedstorage-quartz-arsenal-neoforge-1.0.8.jar"
SHA512 = "faa6530135978a86b25301dd5a5ec673d9908edde01780e4f7ba72e3ead18a0c142a578c428fe49df650c8cca03ec69cdf7a97012b5852f3514fddd23052c8d9"
SIDES = {"client": "required", "server": "required"}


class QuartzArsenalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))

    def test_platform_and_existing_refined_storage_mods_unchanged(self):
        self.assertEqual(
            ("1.21.1", "neoforge", "21.1.264"),
            (self.cfg["minecraft"], self.cfg["loader"], self.cfg["loader_version"]),
        )
        self.assertEqual(81, len(self.cfg["mods"]))
        for slug in ("refined-storage", "refined-storage-jei-integration",
                     "interdimensional-wireless-transmitter", "ae2", "jei"):
            self.assertEqual(1, sum(m["project"] == slug for m in self.cfg["mods"]), slug)
        self.assertEqual("2.0.9", self.cfg["modrinth_lock"]["KDvYkUg3"]["version"])
        self.assertEqual("CcRkmcRp", self.cfg["modrinth_lock"]["nQR8XALE"]["version_id"])

    def test_exact_required_neo_version_and_sha512(self):
        rows = [m for m in self.cfg["mods"] if m["project"] == SLUG]
        self.assertEqual(1, len(rows))
        self.assertTrue(rows[0]["required"])
        self.assertEqual(VERSION, rows[0]["version_id"])
        self.assertEqual(SIDES, rows[0]["environment"])
        self.assertFalse(rows[0].get("client_only", False))
        pin = self.cfg["modrinth_lock"][PROJECT]
        self.assertEqual("1.0.8", pin["version"])
        self.assertEqual(VERSION, pin["version_id"])
        self.assertEqual(FILENAME, pin["filename"])
        self.assertEqual(SHA512, pin["sha512"])
        self.assertIsNotNone(re.fullmatch("[0-9a-f]{128}", pin["sha512"]))
        self.assertEqual(SIDES, pin["environment"])

    def test_official_dependency_is_already_present(self):
        # Modrinth API version toDdIhGu declares one required project,
        # KDvYkUg3 (Refined Storage), without a forced version ID.
        self.assertIn("KDvYkUg3", self.cfg["modrinth_lock"])
        self.assertEqual("lHHiI26k", self.cfg["modrinth_lock"]["KDvYkUg3"]["version_id"])

    def test_exact_mrpack_entry_not_embedded_jar(self):
        rec = {
            "filename": FILENAME,
            "environment": SIDES,
            "file": {
                "filename": FILENAME, "hashes": {"sha512": SHA512},
                "url": ("https://cdn.modrinth.com/data/" + PROJECT +
                        "/versions/" + VERSION + "/" + FILENAME),
                "size": 67115,
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            pack = Path(temp) / "test-quartz.mrpack"
            build_pack.make_mrpack(self.cfg, [rec], pack)
            with zipfile.ZipFile(pack) as archive:
                self.assertIsNone(archive.testzip())
                files = json.loads(archive.read("modrinth.index.json"))["files"]
                matches = [f for f in files if f["path"] == "mods/" + FILENAME]
                self.assertEqual(1, len(matches))
                self.assertEqual(SHA512, matches[0]["hashes"]["sha512"])
                self.assertEqual(SIDES, matches[0]["env"])
                self.assertNotIn("overrides/mods/" + FILENAME, archive.namelist())

    def test_website_entry_and_source_binary_exclusion(self):
        script = (ROOT / "scripts" / "sync_site_mods.py").read_text(encoding="utf-8")
        self.assertIn('"' + SLUG + '"', script)
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn("https://modrinth.com/mod/" + SLUG, html)
        for folder in (ROOT / "mods", ROOT / "manual-mods", ROOT / "overrides" / "mods"):
            if folder.exists():
                self.assertFalse(list(folder.rglob(FILENAME)), folder)


if __name__ == "__main__":
    unittest.main()

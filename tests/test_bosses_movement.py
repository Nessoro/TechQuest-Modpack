"""Proposed 0.3.3 adventure additions: manifest and guide contract tests.

These unit tests do not claim a successful runtime launch of Minecraft.
"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts.guide_assets import ENTRIES

ROOT = Path(__file__).resolve().parents[1]


class BossesAndMovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = {mod["project"]: mod for mod in cls.cfg["mods"]}

    def test_mods_pinned_for_neoforge_1211(self):
        self.assertEqual(self.cfg["minecraft"], "1.21.1")
        self.assertEqual(self.cfg["loader"], "neoforge")
        expected = {
            "bosses-of-mass-destruction-forge": "1.3.3",
            "parcool": "1.21.1-3.4.3.3",
        }
        for slug, prefix in expected.items():
            with self.subTest(slug=slug):
                mod = self.mods[slug]
                self.assertTrue(mod["required"])
                self.assertEqual(mod["version_prefix"], prefix)
                self.assertFalse(mod.get("client_only", False))
        self.assertNotIn("crawl", self.mods, "Do not duplicate ParCool's crawling action")

    def test_guides_cover_new_mods(self):
        for entry_id in ("bomd", "parcool"):
            with self.subTest(entry_id=entry_id):
                self.assertIn(entry_id, ENTRIES)
                self.assertTrue(ENTRIES[entry_id][3])

    def test_pack_declares_both_mods_on_client_and_server(self):
        records = []
        for slug in ("bosses-of-mass-destruction-forge", "parcool"):
            records.append({
                "file": {
                    "filename": slug + ".jar",
                    "hashes": {"sha1": "a" * 40, "sha512": "b" * 128},
                    "url": "https://cdn.modrinth.com/data/example/" + slug + ".jar",
                    "size": 2048,
                },
                "environment": {"client": "required", "server": "required"},
            })
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "test.mrpack"
            self.assertEqual(build_pack.make_mrpack(self.cfg, records, target), 2)
            with zipfile.ZipFile(target) as archive:
                index = json.loads(archive.read("modrinth.index.json"))
                files = index["files"]
                for entry in files:
                    self.assertEqual(entry["env"], {
                        "client": "required", "server": "required"
                    })
                self.assertIn(
                    "overrides/patchouli_books/techquest_guide/en_us/entries/parcool.json",
                    archive.namelist(),
                )
                self.assertIn(
                    "overrides/patchouli_books/techquest_guide/en_us/entries/bomd.json",
                    archive.namelist(),
                )


if __name__ == "__main__":
    unittest.main()

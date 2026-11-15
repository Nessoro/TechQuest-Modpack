"""Static regression checks for Refined Storage inclusion in TechQuest 0.3.3.

These checks verify the manifest only. They do not replace a NeoForge
client/server launch, world tests, or Windows installer testing.
"""
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODRINTH_PROJECT_ID = "KDvYkUg3"
VERSION_ID = "lHHiI26k"
FILENAME = "refinedstorage-neoforge-2.0.9.jar"
SHA512 = "b98a938b8af859f1952bfb35fb6db712835a7dead88fa15258ac0f4f06b26b08ebfa49fd9a35b2c81f7a745b3cd4370ced98c242d0fe7473ba019d92da8f6c57"


class TestRefinedStorageManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))

    def test_platform_and_both_storage_networks_present(self):
        self.assertEqual("1.21.1", self.cfg["minecraft"])
        self.assertEqual("neoforge", self.cfg["loader"])
        self.assertEqual("21.1.264", self.cfg["loader_version"])
        mods = {m["project"]: m for m in self.cfg["mods"]}
        self.assertTrue(mods["ae2"]["required"], "AE2 must not be removed")
        self.assertTrue(mods["refined-storage"]["required"])
        self.assertEqual(VERSION_ID, mods["refined-storage"]["version_id"])

    def test_refined_storage_pinned_and_installed_on_both_sides(self):
        lock = self.cfg["modrinth_lock"][MODRINTH_PROJECT_ID]
        mod = next(m for m in self.cfg["mods"] if m["project"] == "refined-storage")
        sides = {"client": "required", "server": "required"}
        self.assertEqual("2.0.9", lock["version"])
        self.assertEqual(VERSION_ID, lock["version_id"])
        self.assertEqual(FILENAME, lock["filename"])
        self.assertEqual(SHA512, lock["sha512"])
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{128}", lock["sha512"]))
        self.assertEqual(sides, lock["environment"])
        self.assertEqual(sides, mod["environment"])

    def test_no_duplicate_refined_storage_entry(self):
        self.assertEqual(1, sum(m["project"] == "refined-storage" for m in self.cfg["mods"]))
        self.assertNotIn("refined-storage", {m["project"] for m in self.cfg.get("removed_mods", [])})


if __name__ == "__main__":
    unittest.main()

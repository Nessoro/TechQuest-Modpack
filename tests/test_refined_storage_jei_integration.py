"""Static regression tests for official Refined Storage - JEI Integration 1.0.0.

Runtime recipe transfer, Pattern Grid, JEI overlay and multiplayer behavior
still require real Minecraft client/world tests.
"""
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "VzR5wiLo"
VERSION = "BYZmHubv"
FILENAME = "refinedstorage-jei-integration-neoforge-1.0.0.jar"
SHA512 = "95f91c5d634dd144c6acb8dcf946df47a1c09d348e987b00469acc8b5977c09a02f9810cc2d0636d07053c46f029cc3403c52c0759968a6a4673d643fd1543c2"
JEI_PROJECT = "u6dRKJwZ"
RS_PROJECT = "KDvYkUg3"


class TestRefinedStorageJeiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = {m["project"]: m for m in cls.cfg["mods"]}
        cls.lock = cls.cfg["modrinth_lock"]

    def test_platform_and_preserved_parent_mods(self):
        self.assertEqual(("1.21.1", "neoforge", "21.1.264"),
                         (self.cfg["minecraft"], self.cfg["loader"], self.cfg["loader_version"]))
        for name in ("ae2", "refined-storage", "jei", "open-parties-and-claims"):
            with self.subTest(mod=name):
                self.assertTrue(self.mods[name]["required"])
        self.assertEqual("19.64.0.455", self.lock[JEI_PROJECT]["version"])
        self.assertEqual("2.0.9", self.lock[RS_PROJECT]["version"])
        self.assertEqual("lHHiI26k", self.lock[RS_PROJECT]["version_id"])

    def test_official_neo_1_21_1_pin_and_both_sides(self):
        entries = [m for m in self.cfg["mods"] if m["project"] == "refined-storage-jei-integration"]
        self.assertEqual(1, len(entries))
        m = entries[0]
        self.assertTrue(m["required"])
        self.assertEqual(VERSION, m["version_id"])
        sides = {"client": "required", "server": "required"}
        self.assertEqual(sides, m["environment"])
        locked = self.lock[PROJECT]
        self.assertEqual("1.0.0", locked["version"])
        self.assertEqual(VERSION, locked["version_id"])
        self.assertEqual(FILENAME, locked["filename"])
        self.assertEqual(SHA512, locked["sha512"])
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{128}", locked["sha512"]))
        self.assertEqual(sides, locked["environment"])

    def test_mrpack_can_package_exact_artifact_with_both_sides(self):
        locked = self.lock[PROJECT]
        rec = {"filename": FILENAME, "environment": locked["environment"],
               "file": {"filename": FILENAME,
                        "hashes": {"sha512": SHA512},
                        "url": "https://cdn.modrinth.com/data/" + PROJECT
                               + "/versions/" + VERSION + "/" + FILENAME,
                        "size": 58343}}
        with tempfile.TemporaryDirectory() as d:
            pack = Path(d) / "TechQuest-test.mrpack"
            build_pack.make_mrpack(self.cfg, [rec], pack)
            with zipfile.ZipFile(pack) as zf:
                self.assertIsNone(zf.testzip())
                index = json.loads(zf.read("modrinth.index.json"))
                files = [f for f in index["files"] if f["path"] == "mods/" + FILENAME]
                self.assertEqual(1, len(files))
                self.assertEqual(SHA512, files[0]["hashes"]["sha512"])
                self.assertEqual({"client": "required", "server": "required"}, files[0]["env"])

    def test_existing_storage_and_jei_have_no_duplicate_mod_rows(self):
        for project in ("jei", "refined-storage", "refined-storage-jei-integration",
                        "open-parties-and-claims", "ae2"):
            self.assertEqual(1, sum(m["project"] == project for m in self.cfg["mods"]), project)


if __name__ == "__main__":
    unittest.main()

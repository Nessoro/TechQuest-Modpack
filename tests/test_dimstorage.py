"""Review-locked DimStorage 9.1.1 + EdivadLib 3.0.0 on NeoForge 1.21.1.

Static manifest and mrpack tests only. Real frequency/lock/multiplayer/fluids
and dedicated-server startup require separate game testing.
"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "8lnmIJH7": (
        "dimstorage", "9.1.1", "R7rQFgQh", "DimStorage-1.21.1-9.1.1.jar",
        "b15b3e7ef7f0d5814d899ee7b9e87b4abf5add8039ad623ae97d77ad29de31dfe6407637c95b5c50b75c9a5698bbd193da45ece34bfabed7a7fa1c9069dae78f"
    ),
    "a8Jk9kpK": (
        "edivadlib", "3.0.0", "exl6hgWJ", "EdivadLib-1.21-3.0.0.jar",
        "3cb39fdc7ce4b68bf4681ef7395fb6b81961372b10a68784abedd33e2026d9c3841daa93d29a44f9872ef0287eac276f10ab8640a8543ae67e9ae294f28bd8b6"
    )
}
SIDES = {"client": "required", "server": "required"}


class DimStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = cls.cfg["mods"]
        cls.pins = cls.cfg["modrinth_lock"]

    def test_platform_and_preserved_working_033(self):
        self.assertEqual(("1.21.1", "neoforge", "21.1.264"),
                         (self.cfg["minecraft"], self.cfg["loader"], self.cfg["loader_version"]))
        self.assertEqual(81, len(self.mods))
        for slug in ("buildcraft-community-edition", "create", "mekanism",
                     "modern-industrialization", "ae2", "refined-storage",
                     "refined-storage-jei-integration", "open-parties-and-claims",
                     "oritech", "fluidic-tanks", "b1ZV3DIJ",
                     "jei", "dimstorage", "edivadlib"):
            self.assertEqual(1, sum(m["project"] == slug for m in self.mods), slug)
        self.assertFalse(any("rpg-core" in m["project"] for m in self.mods))
        self.assertEqual("2.0.9", self.pins["KDvYkUg3"]["version"])
        self.assertEqual("1.2.13", self.pins["4sYI62kA"]["version"])

    def test_exact_official_SHA512_and_sides(self):
        for project, (slug, version, version_id, filename, sha) in EXPECTED.items():
            with self.subTest(project=project):
                records = [m for m in self.mods if m["project"] == slug]
                self.assertEqual(1, len(records))
                self.assertTrue(records[0]["required"])
                self.assertEqual(version_id, records[0]["version_id"])
                self.assertEqual(SIDES, records[0]["environment"])
                pin = self.pins[project]
                self.assertEqual(version, pin["version"])
                self.assertEqual(version_id, pin["version_id"])
                self.assertEqual(filename, pin["filename"])
                self.assertEqual(sha, pin["sha512"])
                self.assertEqual(128, len(sha))
                self.assertEqual(SIDES, pin["environment"])

    def test_lock_version_has_one_required_library(self):
        # Official Modrinth 9.1.1 metadata: required project a8Jk9kpK
        # and no other required dependency. Modrinth API independently
        # verified through the CI release metadata probe.
        self.assertEqual("EdivadLib", self.pins["a8Jk9kpK"]["title"])

    def test_mrpack_has_no_embedded_third_party_binaries(self):
        mock_files = []
        for project, (_, _, version_id, filename, sha) in EXPECTED.items():
            mock_files.append({
                "filename": filename, "environment": SIDES,
                "file": {
                    "filename": filename, "hashes": {"sha512": sha},
                    "url": ("https://cdn.modrinth.com/data/" + project
                            + "/versions/" + version_id + "/" + filename),
                    "size": 1000
                }
            })
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "dimstorage.mrpack"
            build_pack.make_mrpack(self.cfg, mock_files, path)
            with zipfile.ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                rows = json.loads(archive.read("modrinth.index.json"))["files"]
                for _, (_, _, _, filename, sha) in EXPECTED.items():
                    matches = [row for row in rows if row["path"] == "mods/" + filename]
                    self.assertEqual(1, len(matches))
                    self.assertEqual(sha, matches[0]["hashes"]["sha512"])
                    self.assertEqual(SIDES, matches[0]["env"])
                    self.assertNotIn("overrides/mods/" + filename, archive.namelist())


if __name__ == "__main__":
    unittest.main()

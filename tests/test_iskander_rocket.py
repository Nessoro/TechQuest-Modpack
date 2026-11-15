"""TechQuest micro5: pin and package only official Iskander Rocket NeoForge release."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts.guide_assets import ENTRIES, guide_overrides

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "iskander-rocket-mod"
PROJECT_ID = "XUogRnhj"
VERSION_ID = "M1b2lYax"
FILENAME = "iskander-2.0.1+mc1.21-1.21.1-neoforge.jar"
SHA512 = "539ea44461455b3af6e799e17c59d8284300c06b81f6012f687fe8031452c5e60fa0a93d8e59229d4717d0032e53408f80ad7670a681a932acf736a574a7a07c"


class IskanderRocketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = build_pack.load_cfg()
        cls.roots = {row["project"]: row for row in cls.cfg["mods"]}
        cls.lock = cls.cfg["modrinth_lock"]

    def test_exact_official_1211_release_is_pinned(self):
        self.assertEqual(self.cfg["minecraft"], "1.21.1")
        self.assertEqual(self.cfg["loader"], "neoforge")
        self.assertEqual(self.cfg["loader_version"], "21.1.264")
        root = self.roots[PROJECT]
        self.assertTrue(root["required"])
        self.assertEqual(root["version_id"], VERSION_ID)
        self.assertEqual(root["environment"], {"client":"required","server":"required"})
        file = self.lock[PROJECT_ID]
        self.assertEqual(file["version_id"], VERSION_ID)
        self.assertEqual(file["filename"], FILENAME)
        self.assertEqual(file["sha512"], SHA512)
        self.assertEqual(file["environment"], {"client":"required","server":"required"})

    def test_no_false_dependency_or_conflicting_reactor(self):
        self.assertNotIn("colossal-reactors", self.roots)
        self.assertNotIn("fusion-connected-textures", self.roots)
        self.assertNotIn("ftb-industrial-contraptions", self.roots)
        self.assertNotIn("project-mmo", self.roots)
        self.assertNotIn("y16HgCOF", self.lock)  # Iskandert's Library is unrelated.
        self.assertNotIn("x18RjbsF", self.lock)
        self.assertIn("trash-cans", self.roots)
        self.assertIn("pretty-pipes", self.roots)
        self.assertTrue(hasattr(build_pack, "compatibility_jar"))
        self.assertFalse(hasattr(build_pack, "rpg_core_jar"))

    def test_russian_guide_and_web_catalog_contain_missile(self):
        self.assertIn("iskander_rocket", ENTRIES)
        self.assertIn("patchouli_books/techquest_guide/en_us/entries/iskander_rocket.json", guide_overrides())
        html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        start = html.index("window.TQ_MODS = ") + len("window.TQ_MODS = ")
        end = html.index(";\n", start)
        catalog = json.loads(html[start:end])
        matches = [m for m in catalog if m["url"] == "https://modrinth.com/mod/" + PROJECT]
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0]["required"])

    def test_mrpack_includes_guide_but_no_unverified_third_party_jar(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pack.mrpack"
            build_pack.make_mrpack(self.cfg, [], path)
            with zipfile.ZipFile(path) as archive:
                self.assertIn("overrides/patchouli_books/techquest_guide/en_us/entries/iskander_rocket.json", archive.namelist())
                self.assertNotIn("overrides/mods/" + FILENAME, archive.namelist())
                self.assertIn("overrides/mods/" + build_pack.COMPAT_JAR_NAME, archive.namelist())


if __name__ == "__main__":
    unittest.main()

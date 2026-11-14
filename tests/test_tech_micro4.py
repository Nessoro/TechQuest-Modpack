"""Regression tests: micro4 adds logistics, not the incompatible FTB reactor."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDITIONS = {
    "trash-cans": ("4QrnfueM", "lSKYKJdm", "Комфорт"),
    "pretty-pipes": ("XExdLWCQ", "lrhbGGSe", "Технологии"),
}
REQUIRED_LIBRARIES = {
    "LN9BxssP": ("qKL9jM75", "optional", "optional"),
    "rOUBggPv": ("sLRKmslC", "required", "required"),
}
REJECTED_MODS = {"colossal-reactors", "fusion-connected-textures",
                 "ftb-industrial-contraptions", "ftb-industrial-contraptions-forge"}
REJECTED_LOCKS = {"x18RjbsF", "y16HgCOF", "p19vrgc2"}


class TechnologyExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = {m["project"]: m for m in cls.cfg["mods"]}
        cls.lock = cls.cfg["modrinth_lock"]

    def test_logistics_mods_are_locked_for_both_sides(self):
        self.assertEqual((self.cfg["minecraft"], self.cfg["loader_version"]),
                         ("1.21.1", "21.1.264"))
        for slug, (mod_id, version_id, group) in ADDITIONS.items():
            with self.subTest(mod=slug):
                mod = self.mods[slug]
                self.assertTrue(mod["required"])
                self.assertEqual(mod["version_id"], version_id)
                self.assertEqual(mod["group"], group)
                self.assertEqual(mod["environment"],
                                 {"client": "required", "server": "required"})
                self.assertEqual(self.lock[mod_id]["version_id"], version_id)
                self.assertEqual(self.lock[mod_id]["environment"],
                                 {"client": "required", "server": "required"})

    def test_two_required_libraries_are_pinned(self):
        for mod_id, (version_id, client, server) in REQUIRED_LIBRARIES.items():
            with self.subTest(mod=mod_id):
                lock = self.lock[mod_id]
                self.assertEqual(lock["version_id"], version_id)
                self.assertEqual(lock["environment"],
                                 {"client": client, "server": server})
                self.assertEqual(len(lock["sha512"]), 128)
                self.assertTrue(lock["filename"].endswith(".jar"))

    def test_no_wrong_reactor_or_transitive_dependencies(self):
        for slug in REJECTED_MODS:
            self.assertNotIn(slug, self.mods)
        for mod_id in REJECTED_LOCKS:
            self.assertNotIn(mod_id, self.lock)
        self.assertNotIn("advanced-solar-panels-refactored", self.mods)
        self.assertNotIn("solar-industrialization", self.mods)

    def test_core_unchanged_and_compatibility_retained(self):
        for slug in ("buildcraft-community-edition", "create", "mekanism",
                     "modern-industrialization", "ae2", "sophisticated-storage"):
            self.assertIn(slug, self.mods)
        self.assertNotIn("project-mmo", self.mods)
        import build_pack
        self.assertTrue(hasattr(build_pack, "compatibility_jar"))
        self.assertFalse(hasattr(build_pack, "rpg_core_jar"))

    def test_new_logistics_are_in_ingame_guide(self):
        from scripts.guide_assets import ENTRIES, guide_overrides
        assets = guide_overrides()
        for key in ("trash_cans", "pretty_pipes"):
            self.assertIn(key, ENTRIES)
            self.assertIn(
                "patchouli_books/techquest_guide/en_us/entries/" + key + ".json",
                assets)
        self.assertNotIn("colossal_reactors", ENTRIES)

    def test_site_matches_new_profile(self):
        html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        start = html.index("window.TQ_MODS = ") + len("window.TQ_MODS = ")
        end = html.index(";\n", start)
        catalog = json.loads(html[start:end])
        urls = {m["url"] for m in catalog}
        for slug in ADDITIONS:
            self.assertIn("https://modrinth.com/mod/" + slug, urls)
        for slug in REJECTED_MODS:
            self.assertNotIn("https://modrinth.com/mod/" + slug, urls)


if __name__ == "__main__":
    unittest.main()

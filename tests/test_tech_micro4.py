"""Regression tests for TechQuest micro4 logistics and reactor candidate."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ADDITIONS = {
    "trash-cans": ("4QrnfueM", "lSKYKJdm", "Комфорт"),
    "pretty-pipes": ("XExdLWCQ", "lrhbGGSe", "Технологии"),
    "colossal-reactors": ("x18RjbsF", "vEqPFJY7", "Технологии"),
}
DEPENDENCIES = {
    "LN9BxssP": ("qKL9jM75", "optional", "optional"),
    "rOUBggPv": ("sLRKmslC", "required", "required"),
    "y16HgCOF": ("TqPQSxui", "required", "required"),
    "p19vrgc2": ("AYDaLPK8", "required", "unsupported"),
}


class TechnologyExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = {m["project"]: m for m in cls.cfg["mods"]}
        cls.lock = cls.cfg["modrinth_lock"]

    def test_three_releases_locked_for_both_client_and_server(self):
        self.assertEqual((self.cfg["minecraft"], self.cfg["loader_version"]), ("1.21.1", "21.1.264"))
        for slug, (mod_id, version_id, group) in ADDITIONS.items():
            with self.subTest(mod=slug):
                mod = self.mods[slug]
                self.assertTrue(mod["required"])
                self.assertFalse(mod.get("client_only", False))
                self.assertEqual(mod["version_id"], version_id)
                self.assertEqual(mod["group"], group)
                self.assertEqual(self.lock[mod_id]["version_id"], version_id)
                self.assertEqual(self.lock[mod_id]["environment"],
                                 {"client": "required", "server": "required"})

    def test_new_dependencies_pinned_without_client_only_on_server(self):
        for project_id, (version_id, client, server) in DEPENDENCIES.items():
            with self.subTest(dependency=project_id):
                lock = self.lock[project_id]
                self.assertEqual(lock["version_id"], version_id)
                self.assertEqual(lock["environment"], {"client": client, "server": server})
                self.assertEqual(len(lock["sha512"]), 128)
                self.assertTrue(lock["filename"].endswith(".jar"))
        self.assertNotIn("p19vrgc2", {k for k,v in self.lock.items()
                                    if k == "p19vrgc2" and v["environment"]["server"] != "unsupported"})

    def test_original_core_preserved_and_experimental_solar_not_installed(self):
        for slug in ("buildcraft-community-edition", "create", "mekanism",
                     "modern-industrialization", "ae2", "sophisticated-storage"):
            self.assertIn(slug, self.mods)
        self.assertNotIn("project-mmo", self.mods)
        self.assertNotIn("advanced-solar-panels-refactored", self.mods)
        self.assertNotIn("solar-industrialization", self.mods)
        import build_pack
        self.assertTrue(hasattr(build_pack, "compatibility_jar"))
        self.assertFalse(hasattr(build_pack, "rpg_core_jar"))

    def test_russian_ingame_guide_includes_new_technology(self):
        from scripts.guide_assets import ENTRIES, guide_overrides
        for key in ("trash_cans", "pretty_pipes", "colossal_reactors"):
            self.assertIn(key, ENTRIES)
            self.assertIn(
                "patchouli_books/techquest_guide/en_us/entries/" + key + ".json",
                guide_overrides(),
            )

    def test_lock_metadata_and_matching_website_catalog(self):
        html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        start = html.index("window.TQ_MODS = ") + len("window.TQ_MODS = ")
        end = html.index(";\n", start)
        catalog = json.loads(html[start:end])
        for slug,(project_id,_,_) in ADDITIONS.items():
            lock = self.lock[project_id]
            self.assertTrue(all(c in "0123456789abcdef" for c in lock["sha512"]))
            self.assertIn("1.21", lock["filename"].lower() if slug != "pretty-pipes" else "1.21")
            matches = [m for m in catalog if m["url"] == "https://modrinth.com/mod/" + slug]
            self.assertEqual(len(matches), 1)
            self.assertTrue(matches[0]["required"])


if __name__ == "__main__":
    unittest.main()

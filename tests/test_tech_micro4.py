"""Regression tests: micro4 adds logistics, not the incompatible FTB reactor."""
import json
import tempfile
import unittest
import zipfile
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

    def test_locked_filenames_and_hashes_for_new_additions(self):
        expected = {"trash-cans": "4QrnfueM", "pretty-pipes": "XExdLWCQ"}
        for slug, project_id in expected.items():
            with self.subTest(mod=slug):
                mod = self.mods[slug]
                lock = self.lock[project_id]
                self.assertEqual(lock["version_id"], mod["version_id"])
                self.assertEqual(lock["environment"], mod["environment"])
                self.assertTrue(lock["filename"].endswith(".jar"))
                self.assertNotIn("/", lock["filename"])
                self.assertNotIn("\\", lock["filename"])
                self.assertEqual(len(lock["sha512"]), 128)
                self.assertTrue(all(ch in "0123456789abcdef" for ch in lock["sha512"]))

    def test_mrpack_contains_pinned_logistics_on_both_sides(self):
        """Offline manifest test; runtime JAR downloads are verified by build CI."""
        import build_pack
        records = []
        for project_id in ("4QrnfueM", "XExdLWCQ", "LN9BxssP", "rOUBggPv"):
            lock = self.lock[project_id]
            records.append({
                "file": {
                    "filename": lock["filename"],
                    "hashes": {"sha512": lock["sha512"]},
                    "url": "https://cdn.modrinth.com/data/test/" + lock["filename"],
                    "size": 1024,
                },
                "environment": lock["environment"],
            })
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "micro4-test.mrpack"
            build_pack.make_mrpack(self.cfg, records, target)
            with zipfile.ZipFile(target) as archive:
                index = json.loads(archive.read("modrinth.index.json"))
                by_name = {row["path"]: row for row in index["files"]}
                for project_id in ("4QrnfueM", "XExdLWCQ", "LN9BxssP", "rOUBggPv"):
                    lock = self.lock[project_id]
                    with self.subTest(project_id=project_id):
                        path = "mods/" + lock["filename"]
                        self.assertIn(path, by_name)
                        self.assertEqual(by_name[path]["hashes"]["sha512"], lock["sha512"])
                        self.assertEqual(by_name[path]["env"],
                                         {"client": "required", "server": "required"})
                        self.assertNotIn("overrides/" + path, archive.namelist())
                forbidden = ("colossal", "fusion", "iska", "ftb-industrial",
                             "rpg-core", "pmmo")
                self.assertFalse(any(any(word in row["path"].lower() for word in forbidden)
                                     for row in index["files"]))

    def test_disposal_guide_requires_isolation_and_allowlist(self):
        from scripts.guide_assets import ENTRIES
        trash_pages = " ".join(body for _, body in ENTRIES["trash_cans"][3])
        pipes_pages = " ".join(body for _, body in ENTRIES["pretty_pipes"][3])
        for term in ("булыжник", "фильтр", "сеть"):
            self.assertIn(term, trash_pages.lower() + pipes_pages.lower())
        self.assertIn("алмаз", trash_pages.lower() + pipes_pages.lower())
        self.assertIn("Extraction Module", pipes_pages)

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

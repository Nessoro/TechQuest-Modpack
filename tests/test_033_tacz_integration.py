"""Contracts for integrating official TaCZ into TechQuest Adventure 0.3.3."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tq_builder_unified_tacz", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Unified033Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.slugs = {x["project"] for x in cls.cfg["mods"]}
        cls.catalog = json.loads((ROOT / "tacz_official_gunpacks.json").read_text(encoding="utf-8"))

    def test_version_and_both_adventure_and_tacz(self):
        self.assertEqual(self.cfg["version"], "0.3.3-alpha")
        for slug in ("timeless-and-classics-zero", "wyrmroost",
                     "legendary-monsters", "twisted-mobs", "forgematica",
                     "parcool", "aether"):
            with self.subTest(slug=slug):
                self.assertIn(slug, self.slugs)
        self.assertNotIn("lootr", self.slugs)
        self.assertNotIn("iceandfire-ce", self.slugs)
        tacz = next(m for m in self.cfg["mods"] if m["project"] == "timeless-and-classics-zero")
        self.assertTrue(tacz["required"])
        self.assertEqual(tacz["version_prefix"], "1.2.0")
        self.assertFalse(tacz.get("client_only", False))
        self.assertTrue(self.cfg.get("optional_local_mods"))

    def test_mrpack_includes_tacz_and_amw_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "test.mrpack"
            builder.make_mrpack(self.cfg, [], pack)
            with zipfile.ZipFile(pack) as archive:
                names = archive.namelist()
                self.assertIn("overrides/TECHQUEST_TACZ_OFFICIAL_GUNPACKS.json", names)
                self.assertIn("overrides/TECHQUEST_OPTIONAL_LOCAL_MODS.json", names)
                info = json.loads(archive.read("overrides/TECHQUEST_TACZ_OFFICIAL_GUNPACKS.json"))
                self.assertEqual(len(info["gunpacks"]), 4)
                self.assertFalse(any(n.startswith("overrides/tacz/") for n in names))

    def test_windows_installer_has_both_import_controls(self):
        source = (ROOT / "windows-installer/Program.cs").read_text(encoding="utf-8")
        self.assertIn("ImportAcceleratedMcWarfare()", source)
        self.assertIn("ImportOfficialTaczGunpacks()", source)
        self.assertIn("4. Импорт TaCZ ZIP", source)
        self.assertIn("TECHQUEST_TACZ_OFFICIAL_GUNPACKS.json", source)
        self.assertIn("TECHQUEST_OPTIONAL_LOCAL_MODS.json", source)

    def test_guide_has_both_weapons_and_dragon_pages(self):
        from scripts.guide_assets import ENTRIES
        for page in ("tacz_weapons", "dragon_expedition", "colossal_enemies", "schematics"):
            self.assertIn(page, ENTRIES)


if __name__ == "__main__":
    unittest.main()

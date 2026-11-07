"""Contracts for the official TaCZ mod and author-listed gunpack catalog."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tq_builder_tacz", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class TaczOfficialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.catalog = json.loads((ROOT / "tacz_official_gunpacks.json").read_text(encoding="utf-8"))

    def test_official_tacz_1211_is_required_for_both_sides(self):
        entry = next(x for x in self.cfg["mods"] if x["project"] == "timeless-and-classics-zero")
        self.assertTrue(entry["required"])
        self.assertEqual(entry["version_prefix"], "1.2.0")
        self.assertFalse(entry.get("client_only", False))
        self.assertEqual(self.cfg["loader"], "neoforge")
        self.assertEqual(self.cfg["minecraft"], "1.21.1")

    def test_exact_four_author_listed_zip_packs(self):
        packs = self.catalog["gunpacks"]
        self.assertEqual({p["id"] for p in packs}, {"cyber", "create", "applied", "immersive"})
        self.assertEqual(len({p["filename"] for p in packs}), 4)
        for p in packs:
            self.assertTrue(p["filename"].endswith(".zip"))
            self.assertIn("www.curseforge.com/minecraft/customization/", p["source"])
            self.assertEqual(p["source_mc_version"], "1.20.1")
        self.assertIn("TaCZ:FCE", " ".join(packs[0]["requires"]))

    def test_mrpack_includes_only_metadata_not_third_party_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.mrpack"
            self.assertEqual(builder.make_mrpack(self.cfg, [], path), 0)
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                self.assertIn("overrides/TECHQUEST_TACZ_OFFICIAL_GUNPACKS.json", names)
                self.assertFalse(any(name.startswith("overrides/tacz/") for name in names))
                data = json.loads(archive.read("overrides/TECHQUEST_TACZ_OFFICIAL_GUNPACKS.json"))
                self.assertEqual(len(data["gunpacks"]), 4)

if __name__ == "__main__":
    unittest.main()

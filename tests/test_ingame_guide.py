"""TechQuest 0.3.2 internal handbook, minimap and HP overlays tests."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("techquest_guides", ROOT/"scripts"/"guide_assets.py")
guides = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guides)

spec2 = importlib.util.spec_from_file_location("techquest_build_with_guide", ROOT/"build_pack.py")
builder = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(builder)

class GuideTests(unittest.TestCase):
    def test_categories_entries_and_datapack(self):
        assets = guides.guide_overrides()
        base = "patchouli_books/techquest_guide/"
        book = json.loads(assets[base+"book.json"])
        self.assertEqual(book["name"], "Путеводитель TechQuest")
        self.assertEqual(book["use_resource_pack"], False)
        categories = {p.split("/")[-1].removesuffix(".json") for p in assets
                      if "/en_us/categories/" in p}
        entries = [json.loads(data) for path,data in assets.items()
                   if "/en_us/entries/" in path]
        self.assertGreaterEqual(len(categories), 5)
        self.assertGreaterEqual(len(entries), 14)
        for entry in entries:
            self.assertIn(entry["category"].split(":")[1], categories)
            self.assertTrue(entry["pages"])
            for page in entry["pages"]:
                self.assertEqual(page["type"],"patchouli:text")
        with zipfile.ZipFile(__import__("io").BytesIO(
                 assets["config/openloader/packs/techquest_starter_guide.zip"])) as z:
            self.assertEqual(z.testzip(),None)
            self.assertIn("pack.mcmeta",z.namelist())
            self.assertEqual(json.loads(z.read("pack.mcmeta"))["pack"]["pack_format"],48)
            adv=json.loads(z.read("data/techquest/advancement/first_guide.json"))
            self.assertIn("techquest:starter_guide",adv["rewards"]["loot"])
            loot=json.loads(z.read("data/techquest/loot_table/starter_guide.json"))
            comps=loot["pools"][0]["entries"][0]["functions"][0]["components"]
            self.assertEqual(comps["patchouli:book"],"patchouli:techquest_guide")

    def test_mrpack_embeds_complete_guide(self):
        cfg=json.loads((ROOT/"modlist.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"test.mrpack"
            builder.make_mrpack(cfg, [], path)
            with zipfile.ZipFile(path) as zip:
                self.assertEqual(zip.testzip(),None)
                self.assertIn("overrides/patchouli_books/techquest_guide/book.json",
                              zip.namelist())
                self.assertIn("overrides/config/openloader/packs/techquest_starter_guide.zip",
                              zip.namelist())

    def test_map_and_health_are_explicitly_client_only(self):
        cfg=json.loads((ROOT/"modlist.json").read_text(encoding="utf-8"))
        mods={m["project"]:m for m in cfg["mods"]}
        for slug in ("xaeros-minimap", "xaeros-world-map", "health-indicator-txf"):
            self.assertTrue(mods[slug]["required"])
            self.assertTrue(mods[slug]["client_only"])
        for slug in ("patchouli","open-loader"):
            self.assertTrue(mods[slug]["required"])
            self.assertFalse(mods[slug].get("client_only",False))
        self.assertEqual(cfg["version"],"0.3.3-alpha")

if __name__=="__main__":
    unittest.main()

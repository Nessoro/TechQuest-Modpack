"""Regression tests: original Superb Warfare armor and its texture are never replaced."""
import json
import pathlib
import unittest

from generate_assets import BASES, TECH, RECIPES, RES, generate


class OriginalArmorFusionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generate()

    def test_twenty_smithing_recipes_return_original_items(self):
        files = sorted(RECIPES.glob("*.json"))
        self.assertEqual(len(files), 20)
        for file in files:
            data = json.loads(file.read_text())
            base = data["base"]["item"]
            result = data["result"]
            self.assertEqual(data["type"], "minecraft:smithing_transform")
            self.assertEqual(result["id"], base)
            self.assertTrue(base.startswith("superbwarfare:"))
            self.assertIn(base[14:], BASES)
            self.assertEqual(data["template"]["item"],
                             "minecraft:netherite_upgrade_smithing_template")
            tech = result["components"]["techquest_hybrid:technology"]
            self.assertIn(tech, TECH)
            self.assertEqual(len(result["components"]), 1)
            self.assertNotIn("minecraft:custom_data", result["components"])

    def test_original_armor_in_trim_tag(self):
        tag = json.loads((RES / "data/minecraft/tags/item/trimmable_armor.json").read_text())
        self.assertFalse(tag["replace"])
        self.assertEqual(set(tag["values"]), {"superbwarfare:" + x for x in BASES})

    def test_no_custom_art_generated_or_committed(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        resources = root / "src/main/resources"
        self.assertEqual(list(resources.rglob("*.png")), [])
        self.assertEqual(list(resources.rglob("*.geo.json")), [])
        self.assertEqual(list(resources.rglob("*.cuboids")), [])
        self.assertFalse((root / "skin-packs").exists())

if __name__ == "__main__":
    unittest.main()

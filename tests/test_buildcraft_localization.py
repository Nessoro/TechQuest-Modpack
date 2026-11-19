"""Offline checks for the first-party BuildCraft localization overlay."""
import importlib.util
import io
import json
import re
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANG_PATH = "assets/buildcraft/lang/ru_ru.json"
SOURCE = ROOT / "compat" / "techquest-compat" / LANG_PATH
SPEC = importlib.util.spec_from_file_location("localization_pack_builder", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuildCraftLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.translations = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_techquest_has_russian_technical_terms(self):
        lang = self.translations
        self.assertGreaterEqual(len(lang), 300)
        self.assertEqual(lang["tile.quarryBlock.name"], "Карьер")
        self.assertEqual(lang["tile.engineFe.name"], "FE-двигатель")
        self.assertEqual(lang["tile.mjDynamo.name"], "MJ-динамо")
        self.assertEqual(lang["pipe.buildcrafttransport.wood_item"], "Деревянная транспортная труба")
        self.assertEqual(lang["itemGroup.buildcraft.main"], "BuildCraft")
        self.assertTrue(all(isinstance(key, str) and isinstance(value, str)
                            for key, value in lang.items()))

    def test_preserves_formatting_and_placeholders(self):
        lang = self.translations
        self.assertIn("%s", lang["gui.pipes.emzuli.paint"])
        self.assertIn("%s", lang["gui.buildcraftbuilders.replacer.status.ready"])
        self.assertIn("§7", lang["gui.list.nbt"])
        self.assertIn("§b", lang["block.buildcraftenergy.oil"])
        self.assertTrue(all(not re.search(r"[\x00-\x08\x0b-\x1f]", value)
                            for value in lang.values()))

    def test_compatibility_jar_embeds_russian_language(self):
        with zipfile.ZipFile(io.BytesIO(builder.compatibility_jar())) as jar:
            self.assertEqual(jar.testzip(), None)
            packaged = json.loads(jar.read(LANG_PATH))
            self.assertEqual(packaged, self.translations)
            self.assertIn("META-INF/neoforge.mods.toml", jar.namelist())


if __name__ == "__main__":
    unittest.main()

"""Offline checks for TechQuest's client localization overlays."""
import importlib.util
import io
import json
import re
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPAT = ROOT / "compat" / "techquest-compat"
SPEC = importlib.util.spec_from_file_location("techquest_build", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

LOCALE_COUNTS = {
    "ae2": 1,
    "betterzoom": 49,
    "create": 20,
    "critical_strike": 18,
    "ftbultimine": 20,
    "ic2": 418,
    "jei": 625,
    "guideme": 36,
    "oritech": 1,
}


class AdditionalTranslationTests(unittest.TestCase):
    def test_small_locale_patches_have_expected_coverage_and_valid_strings(self):
        for namespace, expected in LOCALE_COUNTS.items():
            with self.subTest(namespace=namespace):
                path = COMPAT / "assets" / namespace / "lang" / "ru_ru.json"
                with path.open(encoding="utf-8") as file:
                    data = json.load(file)
                self.assertEqual(len(data), expected)
                self.assertTrue(all(
                    isinstance(key, str) and isinstance(text, str)
                    for key, text in data.items()))
                self.assertFalse(any(
                    "\x00" in text or "\r" in text for text in data.values()))

    def test_original_brand_names_and_placeholders_are_preserved(self):
        betterzoom = json.loads((COMPAT / "assets/betterzoom/lang/ru_ru.json").read_text(encoding="utf-8"))
        ftb = json.loads((COMPAT / "assets/ftbultimine/lang/ru_ru.json").read_text(encoding="utf-8"))
        guideme = json.loads((COMPAT / "assets/guideme/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(betterzoom["key.categories.betterzoom"], "Better Zoom")
        self.assertIn("Better Zoom", betterzoom["betterzoom.hint.settings"])
        self.assertIn("%s", betterzoom["betterzoom.hint.settings"])
        self.assertIn("FTB Ultimine", ftb["ftbultimine.modifier.cooldown"])
        self.assertIn("%s", guideme["guideme.guidebook.HoldToShow"])
        ic2 = json.loads((COMPAT / "assets/ic2/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(ic2["block.ic2.advanced_machine"], "Корпус усовершенствованного механизма")
        self.assertEqual(ic2["block.ic2.generator"], "Генератор")
        self.assertIn("EU/t", ic2["ic2.NuclearReactor.gui.info.EUoutput"])
        jei = json.loads((COMPAT / "assets/jei/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertIn("JEI", jei["jei.tooltip.config"])

    def test_compatibility_jar_contains_every_localization(self):
        with zipfile.ZipFile(io.BytesIO(builder.compatibility_jar())) as jar:
            self.assertIsNone(jar.testzip())
            for namespace, expected in LOCALE_COUNTS.items():
                with self.subTest(namespace=namespace):
                    path = f"assets/{namespace}/lang/ru_ru.json"
                    self.assertIn(path, jar.namelist())
                    self.assertEqual(len(json.loads(jar.read(path))), expected)


if __name__ == "__main__":
    unittest.main()

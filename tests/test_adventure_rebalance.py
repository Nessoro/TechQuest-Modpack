"""Genre rebalance tests for the proposed exploration-focused TechQuest 0.3.3."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tq_adventure_builder", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

NEW_MODS = {
    "aether", "deeperdarker", "artifacts", "when-dungeons-arise",
    "yungs-better-strongholds", "yungs-better-nether-fortresses",
    "wyrmroost", "legendary-monsters", "twisted-mobs", "explorers-compass"
}
TECH = {"Технологии", "Хранение"}
ADVENTURE = {"RPG", "Мобы", "Боссы", "Мир", "Приключения"}
EXPLORATION = {"Исследование", "Комфорт", "Передвижение"}
MILITARY = {"Военная техника", "Разрушения"}


class AdventureRebalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = {m["project"]: m for m in cls.cfg["mods"]}

    def test_all_eight_additions_are_required_neoforge_mods(self):
        self.assertEqual((self.cfg["minecraft"], self.cfg["loader"]), ("1.21.1", "neoforge"))
        for slug in NEW_MODS:
            with self.subTest(slug=slug):
                mod = self.mods[slug]
                self.assertTrue(mod["required"])
                self.assertFalse(mod.get("client_only", False))
        for slug in ("buildcraft-community-edition", "create", "mekanism", "modern-industrialization", "ae2"):
            self.assertTrue(self.mods[slug]["required"])

    def test_no_lootr_or_duplicate_dragon_ports(self):
        self.assertNotIn("lootr", self.mods)
        self.assertNotIn("iceandfire-ce", self.mods)
        self.assertIn("wyrmroost", self.mods)
        self.assertIn("legendary-monsters", self.mods)
        self.assertIn("twisted-mobs", self.mods)
        self.assertNotIn("ice-and-fire-dragons", self.mods)
        self.assertNotIn("ice-and-fire-unofficial-port", self.mods)

    def test_client_only_forgematica(self):
        for slug in ("forgematica", "mafglib"):
            with self.subTest(slug=slug):
                m = self.mods[slug]
                self.assertTrue(m["client_only"])
                self.assertEqual(m["version_prefix"], "0.4.3+mc1.21.1")

    def test_gameplay_genre_distribution(self):
        self.assertEqual(self.mods["trash-cans"]["group"], "Комфорт")
        self.assertEqual(self.mods["pretty-pipes"]["group"], "Технологии")
        self.assertNotIn("ftb-industrial-contraptions", self.mods)
        self.assertNotIn("colossal-reactors", self.mods)
        # Micro5 + Refined Storage add one additional storage mod; OPAC is UI, not industry.
        counts = Counter(m["group"] for m in self.cfg["mods"])
        counts.update(m.get("group", "Технологии") for m in self.cfg.get("manual_mods", []))
        counts.update(m.get("group", "Военная техника") for m in self.cfg.get("external_mods", []))
        counts.update("Военная техника" for _ in self.cfg.get("optional_local_mods", []))
        tech = sum(counts[g] for g in TECH)
        adventure = sum(counts[g] for g in ADVENTURE)
        exploration = sum(counts[g] for g in EXPLORATION)
        military = sum(counts[g] for g in MILITARY)
        total = tech + adventure + exploration + military
        self.assertEqual((tech, adventure, exploration, military), (14, 20, 6, 7))
        self.assertEqual(total, 47)
        self.assertLess(tech / total, 0.32)
        self.assertGreater((adventure + exploration) / total, 0.55)

    def test_documentation_for_exploration(self):
        from scripts.guide_assets import ENTRIES
        for key in ("expedition_route", "aether_expedition", "deeper_expedition", "fortress_expedition", "dragon_expedition", "colossal_enemies", "schematics"):
            with self.subTest(key=key):
                self.assertIn(key, ENTRIES)

    def test_mrpack_guide_has_expedition_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.mrpack"
            builder.make_mrpack(self.cfg, [], path)
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                self.assertIn(
                    "overrides/patchouli_books/techquest_guide/en_us/entries/expedition_route.json",
                    names
                )


if __name__ == "__main__":
    unittest.main()

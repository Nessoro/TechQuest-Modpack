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
            self.assertEqual(data["type"], "techquest_hybrid:armor_fusion")
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

    def test_localized_tooltip_and_energy_hints(self):
        path = RES / "assets/techquest_hybrid/lang/ru_ru.json"
        translations = json.loads(path.read_text(encoding="utf-8"))
        for suffix in ("tech", "energy", "recharge", "effect.ic2", "trim"):
            self.assertIn("tooltip.techquest_hybrid." + suffix, translations)
        self.assertIn("FE", translations["tooltip.techquest_hybrid.energy"])

    def test_energy_system_registered_without_replacing_original_items(self):
        java = (pathlib.Path(__file__).resolve().parents[1] /
                "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        self.assertIn('COMPONENTS.register("energy", () -> ENERGY)', java)
        self.assertIn("Capabilities.EnergyStorage.ITEM", java)
        self.assertIn("new ArmorEnergyStorage(stack)", java)
        self.assertIn("getToolTip().add", java)
        self.assertNotIn("DeferredRegister.create(Registries.ITEM", java)

    def test_apotheosis_and_vanilla_anvil_data_are_not_overwritten(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        fusion_java = (root / "src/main/java/dev/techquest/hybrid/HybridFusionRecipe.java").read_text()
        self.assertIn("input.base().copyWithCount(1)", fusion_java)
        self.assertIn("input.addition().copyWithCount(1)", fusion_java)
        self.assertIn("combined.set(HybridWarfareMod.DONOR", fusion_java)
        self.assertNotIn("set(DataComponents.ENCHANTMENTS", fusion_java)
        self.assertNotIn("set(DataComponents.ATTRIBUTE_MODIFIERS", fusion_java)
        self.assertNotIn("AnvilUpdateEvent", fusion_java)
        self.assertNotIn("import dev.shadowsoffire.apotheosis", fusion_java)

    def test_donor_snapshot_codec_and_native_energy_priority(self):
        java = (pathlib.Path(__file__).resolve().parents[1] /
                "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        self.assertIn('COMPONENTS.register("donor", () -> DONOR)', java)
        self.assertIn("ItemStack.STRICT_CODEC", java)
        self.assertIn("EventPriority.LOWEST", java)
        self.assertIn("tooltip.techquest_hybrid.donor", java)

    def test_ic2_jetpack_keeps_native_attachment_and_mfsu_api(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        java = (root / "src/main/java/dev/techquest/hybrid/Ic2JetpackCompat.java").read_text()
        fusion = (root / "src/main/java/dev/techquest/hybrid/HybridFusionRecipe.java").read_text()
        mod = (root / "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        self.assertIn('"hasIC2Jetpack"', java)
        self.assertIn('CustomData.update(DataComponents.CUSTOM_DATA, chest', java)
        self.assertIn('Class.forName("ic2.api.item.ElectricItem")', java)
        self.assertIn('type.getMethod("charge", ItemStack.class', java)
        self.assertIn('type.getMethod("discharge", ItemStack.class', java)
        self.assertIn('"quantum_chestplate"', fusion)
        self.assertIn('Ic2JetpackCompat.attachIfAbsent(combined)', fusion)
        self.assertIn('Ic2JetpackCompat.current(armor)', mod)
        self.assertIn('Ic2JetpackCompat.receive(stack, accepted, simulate)', mod)
        self.assertIn('EventPriority.LOWEST', mod)
        self.assertNotIn('new ArmorItem(', fusion)

    def test_default_armor_stats_and_modifier_restrictions(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        sources = " ".join(p.read_text() for p in
                           (root / "src/main/java").rglob("*.java"))
        self.assertNotIn('ItemAttributeModifierEvent', sources)
        self.assertNotIn('AnvilUpdateEvent', sources)
        self.assertNotIn('ReforgeMenu', sources)
        self.assertNotIn('modifiyArmor', sources)

    def test_no_custom_art_generated_or_committed(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        resources = root / "src/main/resources"
        self.assertEqual(list(resources.rglob("*.png")), [])
        self.assertEqual(list(resources.rglob("*.geo.json")), [])
        self.assertEqual(list(resources.rglob("*.cuboids")), [])
        self.assertFalse((root / "skin-packs").exists())

if __name__ == "__main__":
    unittest.main()

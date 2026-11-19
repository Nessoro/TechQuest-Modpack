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

    def test_native_ic2_charge_uses_preserved_quantum_suit(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        src = (root / "src/main/java/dev/techquest/hybrid/Ic2QuantumChargeManager.java").read_text()
        mod = (root / "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        gradle = (root / "build.gradle").read_text()
        self.assertIn("implements IBackupElectricItemManager", src)
        self.assertIn("ElectricItem.registerBackupManager(INSTANCE)", src)
        self.assertIn("ElectricItem.manager.charge(donor", src)
        self.assertIn("ElectricItem.manager.discharge(", src)
        self.assertIn("HybridWarfareMod.DONOR", src)
        self.assertIn("save(armor, donor)", src)
        self.assertIn("Ic2QuantumChargeManager::register", mod)
        self.assertIn("Ic2QuantumChargeManager.isQuantumHybrid(armor)", mod)
        self.assertIn("Ic2QuantumChargeManager.receive(stack, accepted, simulate)", mod)
        self.assertIn("compileOnly files('../../manual-mods/industrial-craft-2-nostalgia-21.1.0-local.26.jar')", gradle)

    def test_fused_names_are_localized_and_anvil_can_rename_later(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        fusion = (root / "src/main/java/dev/techquest/hybrid/HybridFusionRecipe.java").read_text()
        self.assertIn("combined.set(DataComponents.CUSTOM_NAME, Component.translatable(", fusion)
        self.assertIn("input.base().getHoverName()", fusion)
        self.assertIn('"item.techquest_hybrid.fused_name"', fusion)
        for lang in ("ru_ru", "en_us"):
            localized = json.loads((RES / f"assets/techquest_hybrid/lang/{lang}.json").read_text())
            self.assertIn("item.techquest_hybrid.fused_name", localized)
            for tech in TECH:
                self.assertIn("item.techquest_hybrid.prefix." + tech, localized)

    def test_power_bar_does_not_replace_durability_or_plate_hud(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        decorator = (root / "src/main/java/dev/techquest/hybrid/client/HybridArmorEnergyDecorator.java").read_text()
        main = (root / "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        recipe = (root / "src/main/java/dev/techquest/hybrid/HybridFusionRecipe.java").read_text()
        self.assertIn("RegisterItemDecorationsEvent", decorator)
        self.assertIn("HybridWarfareMod.energyCapacity(stack)", decorator)
        self.assertIn("HybridWarfareMod.charge(stack)", decorator)
        self.assertIn("stack.isBarVisible() ? y + 10 : y + 13", decorator)
        self.assertIn("int width = capacity <= 0 ? 0", decorator)
        self.assertIn("graphics.fill", decorator)
        self.assertIn('data.contains("ArmorPlate")', main)
        self.assertIn('nbt.putDouble("ArmorPlate", 0.0D)', main)
        self.assertIn('ensureArmorPlateBar(chest)', main)
        self.assertIn('HybridWarfareMod.ensureArmorPlateBar(combined)', recipe)
        self.assertNotIn('set(DataComponents.CUSTOM_DATA,', recipe)

    def test_tooltip_uses_compact_energy_numbers(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        java = (root / "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        self.assertIn("EnergyText.compact(charge(stack))", java)
        self.assertIn("EnergyText.compact(energyCapacity(stack))", java)
        text = (root / "src/main/java/dev/techquest/hybrid/EnergyText.java").read_text()
        self.assertIn('1_000_000', text)
        self.assertIn('"m"', text)
        self.assertIn('"k"', text)

    def test_no_custom_art_generated_or_committed(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        resources = root / "src/main/resources"
        self.assertEqual(list(resources.rglob("*.png")), [])
        self.assertEqual(list(resources.rglob("*.geo.json")), [])
        self.assertEqual(list(resources.rglob("*.cuboids")), [])
        self.assertFalse((root / "skin-packs").exists())

if __name__ == "__main__":
    unittest.main()

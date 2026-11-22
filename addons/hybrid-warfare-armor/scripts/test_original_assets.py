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
        decorator = (root / "src/main/java/dev/techquest/hybrid/gui/HybridArmorEnergyDecorator.java").read_text()
        main = (root / "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        recipe = (root / "src/main/java/dev/techquest/hybrid/HybridFusionRecipe.java").read_text()
        # 0.2.3 boot regression: ordinary event subscriber in the same
        # package as an owned Mixin is rejected by Mixin's classloader.
        config = json.loads((root / "src/main/resources/techquest_hybrid.mixins.json").read_text())
        decorator_package = next(
            line.split(";", 1)[0].removeprefix("package ")
            for line in decorator.splitlines() if line.startswith("package ")
        )
        self.assertFalse(decorator_package.startswith(config["package"]),
                         "HUD decorator must not be in the reserved Mixin package")
        self.assertFalse((root / "src/main/java/dev/techquest/hybrid/client/HybridArmorEnergyDecorator.java").exists())
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
        self.assertIn('compactNativeIc2EnergyLine(event.getToolTip())', java)
        self.assertIn('IC2_RF_TOOLTIP', java)
        self.assertIn('Long.parseLong(match.group(1))', java)
        text = (root / "src/main/java/dev/techquest/hybrid/EnergyText.java").read_text()
        self.assertIn('1_000_000', text)
        self.assertIn('"m"', text)
        self.assertIn('"k"', text)

    def test_ic2_quantum_helmets_have_real_abilities_and_native_charge(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        main = (root / "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        helmet = (root / "src/main/java/dev/techquest/hybrid/Ic2QuantumHelmetCompat.java").read_text()
        charge = (root / "src/main/java/dev/techquest/hybrid/Ic2QuantumChargeManager.java").read_text()
        self.assertIn("Ic2QuantumHelmetCompat.serverTick(player, helmet);", main)
        self.assertIn("!isNativeQuantum(helmet)", main)  # no double night vision
        self.assertIn("!Ic2QuantumChargeManager.isQuantumHybrid(helmet)", helmet)
        self.assertIn("Ic2QuantumChargeManager.spend(helmet, 1_000)", helmet)
        self.assertIn("player.setAirSupply", helmet)
        self.assertIn("MobEffects.POISON", helmet)
        self.assertIn("MobEffects.WITHER", helmet)
        self.assertIn("Ic2Potion.radiationHolder()", helmet)
        self.assertIn("Ic2Items.FILLED_TIN_CAN", helmet)
        self.assertIn("can.onEaten(player, food)", helmet)
        self.assertIn("IC2.keyboard.isModeSwitchKeyDown(player)", helmet)
        self.assertIn("IC2.keyboard.isAltKeyDown(player)", helmet)
        self.assertIn("CustomData.update(DataComponents.CUSTOM_DATA, helmet", helmet)
        self.assertIn("Ic2QuantumChargeManager.spend(helmet, 1)", helmet)
        self.assertIn('case "quantum_helmet" -> base.getPath().contains("helmet")', charge)
        self.assertIn("ElectricItem.manager.charge(donor", charge)
        self.assertIn("save(armor, donor)", charge)
        # Never create replacement armor or modify base item IDs.
        self.assertNotIn("new ArmorItem(", helmet)
        self.assertNotIn("DataComponents.CUSTOM_NAME", helmet)

    def test_helmet_smithing_recipes_exist_for_all_technologies(self):
        expected = {"ru_helmet_6b47", "us_helmet_pasgt", "ge_helmet_m_35"}
        for tech in TECH:
            for helm in expected:
                path = RECIPES / (tech + "_" + helm + ".json")
                self.assertTrue(path.exists(), path)
                recipe = json.loads(path.read_text())
                self.assertEqual(recipe["base"]["item"], "superbwarfare:" + helm)
                self.assertEqual(recipe["result"]["id"], "superbwarfare:" + helm)
                self.assertEqual(recipe["addition"]["item"], TECH[tech][0])

    def test_powered_elytra_special_recipe_and_anti_duplication(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        recipe = json.loads((RECIPES / "special/powered_elytra.json").read_text())
        self.assertEqual(recipe["type"], "techquest_hybrid:powered_elytra_attach")
        source = (root / "src/main/java/dev/techquest/hybrid/PoweredElytraRecipe.java").read_text()
        self.assertIn("PoweredElytraEnergy.isPoweredChest(stack)", source)
        self.assertIn("PoweredElytra.canAttach(found[0], found[1])", source)
        self.assertIn("ItemStack.EMPTY", source)
        self.assertIn("input.base()", (root / "src/main/java/dev/techquest/hybrid/HybridFusionRecipe.java").read_text())
        self.assertIn("found[0].copyWithCount(1)", source)
        self.assertIn("found[1].copyWithCount(1)", source)
        self.assertIn("result.set(HybridWarfareMod.ELYTRA_ATTACHMENT", source)
        self.assertIn("width * height >= 2", source)
        self.assertIn("stack.is(Items.ELYTRA)", source)
        main = (root / "src/main/java/dev/techquest/hybrid/HybridWarfareMod.java").read_text()
        self.assertIn('COMPONENTS.register("elytra_attachment"', main)
        self.assertIn('SERIALIZERS.register("powered_elytra_attach"', main)
        self.assertIn("ItemStack.STRICT_CODEC", main)
        self.assertIn("ItemStack.STREAM_CODEC", main)

    def test_elytra_never_uses_durability_and_rejects_unpowered_chests(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        energy = (root / "src/main/java/dev/techquest/hybrid/PoweredElytraEnergy.java").read_text()
        flight = (root / "src/main/java/dev/techquest/hybrid/PoweredElytra.java").read_text()
        ic2 = (root / "src/main/java/dev/techquest/hybrid/Ic2ElytraEnergy.java").read_text()
        # In NeoForge 1.21.1 the optional ItemStack slot override is null
        # for normal ArmorItem stacks. 0.2.6 rejected all such chestplates.
        self.assertIn("EquipmentSlot override = stack.getEquipmentSlot()", energy)
        self.assertIn("if (override != null) return override == EquipmentSlot.CHEST", energy)
        self.assertIn("stack.getItem() instanceof ArmorItem armor", energy)
        self.assertIn("armor.getEquipmentSlot() == EquipmentSlot.CHEST", energy)
        self.assertNotIn("stack.getEquipmentSlot() != EquipmentSlot.CHEST", energy)
        self.assertIn('"ru_chest_6b43".equals(name)', energy)
        self.assertIn('"us_chest_iotv".equals(name)', energy)
        self.assertIn('&& HybridWarfareMod.technology(stack) != null', energy)
        self.assertIn('HybridWarfareMod.energyCapacity(stack) >= COST_PER_TICK', energy)
        self.assertLess(energy.index('if ("superbwarfare".equals(itemId.getNamespace()))'),
                        energy.index('if (!isChestArmor(stack)) return false;'))
        self.assertIn("power.getMaxEnergyStored() >= COST_PER_TICK", energy)
        self.assertIn("power.canExtract()", energy)
        self.assertIn("power.extractEnergy(COST_PER_TICK, true)", energy)
        self.assertIn("power.extractEnergy(COST_PER_TICK, false)", energy)
        self.assertIn("Ic2ElytraEnergy.spend(stack, COST_PER_TICK)", energy)
        self.assertIn("ElectricItem.manager.discharge(stack", ic2)
        self.assertIn("PoweredElytraEnergy.spend(chest)", flight)
        self.assertIn("if (!canFly(chest, wearer)) return false", flight)
        self.assertNotIn("hurtAndBreak(", flight)
        self.assertNotIn("setDamageValue(", flight)
        self.assertIn("GameEvent.ELYTRA_GLIDE", flight)
        self.assertIn("ElytraItem.isFlyEnabled(wings)", flight)

    def test_elytra_flight_mixin_and_client_renderer_are_isolated(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        resources = root / "src/main/resources"
        flightmix = json.loads((resources / "techquest_hybrid_flight.mixins.json").read_text())
        self.assertEqual(flightmix["package"], "dev.techquest.hybrid.flightmixin")
        self.assertEqual(set(flightmix["mixins"]),
                         {"PoweredElytraPlayerMixin", "PoweredElytraLivingMixin"})
        toml = (resources / "META-INF/neoforge.mods.toml").read_text()
        self.assertIn('config="techquest_hybrid_flight.mixins.json"', toml)
        mix = root / "src/main/java/dev/techquest/hybrid/flightmixin"
        self.assertIn("tryToStartFallFlying", (mix / "PoweredElytraPlayerMixin.java").read_text())
        living = (mix / "PoweredElytraLivingMixin.java").read_text()
        self.assertIn("updateFallFlying", living)
        self.assertIn("elytraFlightTick", living)
        self.assertIn("original.call(stack, owner", living)
        renderer = (root / "src/main/java/dev/techquest/hybrid/gui/PoweredElytraLayer.java").read_text()
        self.assertIn("ElytraLayer<", renderer)
        self.assertIn("PoweredElytra.hasElytra(stack)", renderer)
        self.assertIn('textures/entity/elytra.png', renderer)
        event = (root / "src/main/java/dev/techquest/hybrid/gui/PoweredElytraRenderEvents.java").read_text()
        self.assertIn("EntityRenderersEvent.AddLayers", event)
        self.assertIn("renderer.addLayer(new PoweredElytraLayer", event)
        self.assertNotIn("dev.techquest.hybrid.client;", event)

    def test_no_custom_art_generated_or_committed(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        resources = root / "src/main/resources"
        self.assertEqual(list(resources.rglob("*.png")), [])
        self.assertEqual(list(resources.rglob("*.geo.json")), [])
        self.assertEqual(list(resources.rglob("*.cuboids")), [])
        self.assertFalse((root / "skin-packs").exists())

if __name__ == "__main__":
    unittest.main()

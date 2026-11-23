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
    "appleskin": 10,
    "balm": 36,
    "betterzoom": 49,
    "betterblockz": 1748,
    "bookshelf": 200,
    "create": 20,
    "critical_strike": 18,
    "ftbultimine": 20,
    "fluidic_tanks": 24,
    "ic2": 1336,
    "immersiveengineering": 894,
    "jei": 625,
    "mekanism": 2279,
    "mekanismgenerators": 364,
    "modern_industrialization": 49,
    "mowziesmobs": 440,
    "guideme": 36,
    "oritech": 1,
    "openpartiesandclaims": 703,
    "prettypipes": 41,
    "refinedstorage": 10,
    "xaeroworldmap": 303,
    "waystones": 268,
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
        self.assertEqual(ic2["ic2.crop.seed_bag.plant"], "Растение: %s")
        self.assertEqual(ic2["ic2.generic.text.amount"], "Объём жидкости: %s mB")
        self.assertEqual(ic2["ic2.tooltip.upgrade.overclocker.power"], "Повысить энергопотребление до %1$s%%")
        self.assertIn("3 × 3", ic2["ic2.gravi.drill.mode.3"])
        jei = json.loads((COMPAT / "assets/jei/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertIn("JEI", jei["jei.tooltip.config"])
        self.assertEqual(jei["jei.config.client.bookmarkList.bookmarkPreviewMode.value.DISABLED"], "Выключено")
        blockz = json.loads((COMPAT / "assets/betterblockz/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(blockz["block.betterblockz.agon_blockz_0"], "Agon — цвет: белый")
        self.assertIn("§e[Shift]§7", blockz["item.betterblockz.auto_placer.tooltip"])
        self.assertIn("%s", blockz["item.betterblockz.omni_spade.shift.line4"])
        mekanism = json.loads((COMPAT / "assets/mekanism/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(mekanism["constants.mekanism.mod_name"], "Mekanism")
        self.assertIn("MekaSuit", mekanism["configuration.mekanism.client.hud.mekasuit.energy_bar.tooltip"])
        self.assertIn("Vein Mining", mekanism["configuration.mekanism.gear.disassembler.vein_mining.tooltip"])
        self.assertIn("mB/t", mekanism["configuration.mekanism.gear.canteen.transfer_rate.tooltip"])
        self.assertIn("MekaSuit", mekanism["configuration.mekanism.gear.meka_suit.capacity.energy.tooltip"])
        self.assertIn("mB/t", mekanism["configuration.mekanism.gear.meka_suit.jetpack.transfer_rate.tooltip"])
        self.assertIn("mekanism:mekasuit_absorption", mekanism["configuration.mekanism.gear.meka_suit.damage_absorption.unspecified.tooltip"])
        generators = json.loads((COMPAT / "assets/mekanismgenerators/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(generators["configuration.mekanismgenerators.server.fission.meltdowns.enabled"],
                         "Включено")
        self.assertIn("mB/t", generators["configuration.mekanismgenerators.server.hohlraum.fill_rate.tooltip"])
        self.assertIn("%2$s", generators["death.attack.mekanismgenerators.fusion.player"])
        self.assertIn("Mekanism: Generators", generators["mekanismgenerators.configuration.title"])
        self.assertIn("Extended Vein Mining", mekanism["configuration.mekanism.gear.meka_tool.extended_vein.tooltip"])
        self.assertIn("mB/t", mekanism["configuration.mekanism.gear.scuba_tank.fill_rate.tooltip"])
        self.assertEqual(mekanism["configuration.mekanism.gear.meka_tool.energy_usage.silk"],
                         "Шёлковое касание")
        self.assertIn("FE/RF", mekanism["configuration.mekanism.general.energy_conversion.blacklist.fluxnetworks.tooltip"])
        self.assertIn("mB/t", mekanism["configuration.mekanism.general.fill_rate.chemical.tooltip"])
        self.assertIn("mekanism", mekanism["configuration.mekanism.general.cardboard.mod_blacklist.tooltip"])
        immersive = json.loads((COMPAT / "assets/immersiveengineering/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(immersive["block.minecraft.banner.immersiveengineering.hammer.black"],
                         "Молот (чёрный)")
        self.assertEqual(immersive["advancement.immersiveengineering.mb_cokeoven.desc"],
                         "Постройте коксовую печь")
        self.assertIn("%1$s", immersive["gui.immersiveengineering.config.radio_tower.range_m"])
        self.assertEqual(immersive["manual.immersiveengineering.electrical_grids"],
                         "Электрические сети")
        self.assertEqual(immersive["block.immersiveengineering.concrete_reinforced"],
                         "Армированный бетон")
        self.assertEqual(immersive["item.immersiveengineering.bullet_armor_piercing"],
                         "Бронебойный патрон")
        self.assertEqual(immersive["chat.immersiveengineering.info.conveyor.stacksize"],
                         "Извлекать %1$s предметов в секунду")
        self.assertIn("%2$s", immersive["ie.manual.entry.minerals.biomes"])
        self.assertIn("§m6§r", immersive["desc.immersiveengineering.flavour.revolver.einhorn"])
        open_claims = json.loads((COMPAT / "assets/openpartiesandclaims/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertIn("%3$s", open_claims["gui.xaero_claims_claimed_at"])
        self.assertIn("%3$s", open_claims["gui.xaero_claims_anchored_at"])
        self.assertIn("%7$s", open_claims["gui.xaero_claims_claim_command_area_start"])
        self.assertIn("/oclaims anchor", open_claims["gui.xaero_claims_claim_not_within_anchor_range"])
        self.assertIn("%6$s", open_claims["gui.xaero_claims_forceload_command_area_start"])
        self.assertIn("%3$s", open_claims["gui.xaero_claims_transfer_target_message"])
        self.assertIn("%1$d", open_claims["gui.xaero_pac_config_create_sub_id_rules"])
        self.assertIn("confirm", open_claims["gui.xaero_pac_config_delete_group_confirmation_request"])
        self.assertIn("%3$s", open_claims["gui.xaero_claims_transfer_target_anchor_limit"])
        self.assertIn("%1$s", open_claims["gui.xaero_pac_player_config_playerConfig.claims.protection.exceptions.groups.entity.entityAttackAccess"])
        self.assertEqual(open_claims["gui.xaero_pac_ui_player_config_player_groups_group_id_allowed_chars2"],
                         "a-z, A-Z, 0-9, - или _, без пробелов")
        pipes = json.loads((COMPAT / "assets/prettypipes/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(pipes["dir.prettypipes.all"], "Все стороны")
        self.assertIn("§o", pipes["info.prettypipes.insert_unstacked.description"])
        self.assertEqual(pipes["info.prettypipes.million"], "%sM")
        self.assertEqual(pipes["item_group.prettypipes.tab"], "Pretty Pipes")
        bookshelf = json.loads((COMPAT / "assets/bookshelf/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(bookshelf["day.bookshelf.monday"], "Понедельник")
        xaero = json.loads((COMPAT / "assets/xaeroworldmap/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertIn("карты", xaero["effect.xaeroworldmap.no_cave_maps"])
        self.assertIn("%1$s", xaero["gui.xaero_wm_ceiling"])
        waystones = json.loads((COMPAT / "assets/waystones/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(waystones["gui.waystones.waystone_selection.item_requirement"],
                         "Стоимость предметами: %d %s")
        self.assertEqual(waystones["commands.waystones.cooldown.set.success.multiple"],
                         "Перезарядка %s установлена на %d секунд для %d игроков")
        self.assertIn("{Biome}", waystones["waystones.configuration.worldGen.nameGenerationTemplate.tooltip"])
        self.assertIn("BlueMap", waystones["waystones.configuration.blueMap.enabled.tooltip"])
        self.assertEqual(waystones["chat.waystones.teleport_failed"],
                         "Телепортация не удалась.")
        mowzie = json.loads((COMPAT / "assets/mowziesmobs/lang/ru_ru.json").read_text(encoding="utf-8"))
        self.assertEqual(mowzie["itemGroup.mowziesmobs.creativeTab"], "Mowzie's Mobs")


    def test_compatibility_jar_contains_every_localization(self):
        with zipfile.ZipFile(io.BytesIO(builder.compatibility_jar())) as jar:
            self.assertIsNone(jar.testzip())
            for namespace, expected in LOCALE_COUNTS.items():
                with self.subTest(namespace=namespace):
                    path = f"assets/{namespace}/lang/ru_ru.json"
                    self.assertIn(path, jar.namelist())
                    self.assertEqual(len(json.loads(jar.read(path))), expected)


    def test_localization_source_licenses_are_embedded(self):
        expected = {
            "THIRD_PARTY_LICENSES/MOWZIES_MOBS_LICENSE.txt",
            "THIRD_PARTY_LICENSES/MINWIX_MIT.txt",
            "THIRD_PARTY_LICENSES/XAERO_RU_CC-BY-SA-4.0.txt",
            "THIRD_PARTY_LICENSES/README.md",
        }
        with zipfile.ZipFile(io.BytesIO(builder.compatibility_jar())) as jar:
            self.assertTrue(expected.issubset(set(jar.namelist())))
            self.assertIn(b"Creative Commons", jar.read("THIRD_PARTY_LICENSES/XAERO_RU_CC-BY-SA-4.0.txt"))


if __name__ == "__main__":
    unittest.main()

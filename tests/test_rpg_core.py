"""Contract checks for the original lowcodefml RPG Core micro2 module."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts import install_client, install_server


class RPGCoreTests(unittest.TestCase):
    def test_mod_metadata_and_datapack_structure(self):
        blob = build_pack.rpg_core_jar()
        self.assertEqual(blob, build_pack.rpg_core_jar())
        with zipfile.ZipFile(io.BytesIO(blob)) as jar:
            self.assertIsNone(jar.testzip())
            paths = jar.namelist()
            toml = jar.read("META-INF/neoforge.mods.toml").decode()
            self.assertIn('modLoader="lowcodefml"', toml)
            self.assertIn('modId="techquest_rpg"', toml)
            self.assertIn('side="BOTH"', toml)
            meta = json.loads(jar.read("pack.mcmeta"))
            self.assertEqual(meta["pack"]["pack_format"], 48)
            for tag in ("tick", "load"):
                tag_data = json.loads(jar.read("data/minecraft/tags/function/" + tag + ".json"))
                self.assertEqual(tag_data["values"], ["techquest_rpg:" + tag])
            self.assertNotIn("data/pmmo/config/server.json", paths)
            self.assertFalse(any(p.endswith(".class") for p in paths))

    def test_perks_are_advancement_based_without_levels_or_mass_mining(self):
        with zipfile.ZipFile(io.BytesIO(build_pack.rpg_core_jar())) as jar:
            perk = jar.read("data/techquest_rpg/function/perks.mcfunction").decode()
            tick = jar.read("data/techquest_rpg/function/tick.mcfunction").decode()
            self.assertIn("advancements={minecraft:story/iron_tools=true}", perk)
            self.assertIn("advancements={minecraft:nether/obtain_blaze_rod=true}", perk)
            self.assertIn("advancements={minecraft:end/kill_dragon=true}", perk)
            self.assertIn("matches 100..", tick)
            for word in ("vein", "pmmo", "mine @", "destroy ", "setblock", "fill ", "xp add"):
                self.assertNotIn(word, (perk + tick).lower())

    def test_mob_scaling_is_bounded_and_opt_out_is_persistent(self):
        with zipfile.ZipFile(io.BytesIO(build_pack.rpg_core_jar())) as jar:
            mob_scale = jar.read("data/techquest_rpg/function/mob_scale.mcfunction").decode()
            for window in ("7..20", "21..41", "42.."):
                self.assertIn(window, mob_scale)
            load = jar.read("data/techquest_rpg/function/load.mcfunction").decode()
            self.assertIn("unless score #enabled", load)
            self.assertIn("unless score #perks", load)
            self.assertIn("unless score #mobs", load)
            self.assertIn("scoreboard objectives add tqrpg_flags dummy", load)
            tags = json.loads(jar.read("data/techquest_rpg/tags/entity_type/scaling_targets.json"))
            self.assertNotIn("minecraft:ender_dragon", tags["values"])
            self.assertNotIn("minecraft:wither", tags["values"])
            for tier in ("mob_tier1", "mob_tier2", "mob_tier3"):
                text = jar.read("data/techquest_rpg/function/" + tier + ".mcfunction").decode()
                self.assertIn("type=#techquest_rpg:scaling_targets", text)
                self.assertIn("execute in minecraft:the_end", text)

    def test_client_server_and_mrpack_use_identical_jar(self):
        cfg = build_pack.load_cfg()
        self.assertFalse(any(m["project"] == "project-mmo" for m in cfg["mods"]))
        for mod in ("apotheosis", "skill-tree", "irons-spells-n-spellbooks"):
            self.assertIn(mod, {m["project"] for m in cfg["mods"]})
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            pack = folder / "micro2.mrpack"
            build_pack.make_mrpack(cfg, [], pack)
            expected = build_pack.rpg_core_jar()
            with zipfile.ZipFile(pack) as archive:
                self.assertEqual(archive.read("overrides/mods/" + build_pack.RPG_JAR_NAME), expected)
                install_client.install_guide_overrides(archive, folder / "client")
            self.assertEqual((folder / "client/mods" / build_pack.RPG_JAR_NAME).read_bytes(), expected)
            mods = folder / "server" / "mods"
            mods.mkdir(parents=True)
            install_server.install_compatibility(pack, mods)
            self.assertEqual((mods / build_pack.RPG_JAR_NAME).read_bytes(), expected)
            self.assertEqual((mods / build_pack.COMPAT_JAR_NAME).read_bytes(),
                             build_pack.compatibility_jar())


if __name__ == "__main__":
    unittest.main()

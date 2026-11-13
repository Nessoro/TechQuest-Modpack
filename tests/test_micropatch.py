"""Regression checks for pinned micro-patch mods and persistent server datapack."""
import io
import json
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts.guide_assets import micro_patch_datapack, guide_overrides

ROOT = Path(__file__).resolve().parents[1]

class MicroPatchTests(unittest.TestCase):
    def setUp(self):
        self.cfg = build_pack.load_cfg()
        self.mods = {m["project"]: m for m in self.cfg["mods"]}

    def test_storage_and_dependencies_are_locked_without_ipn(self):
        for p in ("sophisticated-storage", "architectury-api"):
            self.assertIn(p, self.mods)
            self.assertTrue(self.mods[p]["required"])
        self.assertIn("iron-chests", self.mods)
        self.assertIn("sophisticated-backpacks", self.mods)
        # IPN automatically replaced worn-out tools and is no longer wanted.
        for slug in ("inventory-profiles-next", "libipn"):
            self.assertNotIn(slug, self.mods)
        for ident in ("O7RBXm3n", "onSQdWhM"):
            self.assertNotIn(ident, self.cfg["modrinth_lock"])
        # Do not remove other pinned libraries opportunistically.
        self.assertFalse(self.mods["architectury-api"].get("client_only", False))
        for ident in ("hMlaZH8f", "lhGA9TYQ", "ordsPcFz"):
            self.assertIn(ident, self.cfg["modrinth_lock"])

    def test_ftb_maven_only_and_same_client_server_versions(self):
        files = {m["name"]: m for m in self.cfg["external_mods"]}
        self.assertEqual({"FTB Ultimine", "FTB Library"}.intersection(files),
                         {"FTB Ultimine", "FTB Library"})
        for name in ("FTB Ultimine", "FTB Library"):
            mod = files[name]
            self.assertTrue(mod["download_url"].startswith("https://maven.ftb.dev/releases/dev/ftb/mods/"))
            self.assertEqual(len(mod["sha256"]), 64)
            self.assertGreater(mod["file_size"], 100000)
            self.assertTrue(mod["required"])

    def test_additive_datapack_separate_from_existing_guide(self):
        with zipfile.ZipFile(io.BytesIO(guide_overrides()["config/openloader/packs/techquest_starter_guide.zip"])) as z:
            self.assertNotIn("data/pmmo/config/server.json", z.namelist())
            self.assertNotIn("data/minecraft/tags/function/tick.json", z.namelist())
        self.assertIn("config/openloader/packs/techquest_micropatch_033.zip", guide_overrides())

    def test_micro2_replaces_pmmo_but_retains_ftb_and_apotheosis(self):
        self.assertNotIn("project-mmo", self.mods)
        self.assertNotIn("KFQYC1Uy", self.cfg["modrinth_lock"])
        self.assertNotIn("config/pmmo-client.toml", build_pack.client_config_overrides(self.cfg))
        self.assertIn("FTB Ultimine", {row["name"] for row in self.cfg["external_mods"]})
        with zipfile.ZipFile(io.BytesIO(micro_patch_datapack())) as z:
            self.assertNotIn("data/pmmo/config/server.json", z.namelist())
            self.assertIn("data/techquest/function/worldtier/sync.mcfunction", z.namelist())

    def test_betterzoom_startup_mixin_embedded(self):
        import zipfile
        from pathlib import Path
        from build_pack import compatibility_jar
        class_path = "techquest/compat/mixin/BetterZoomEarlyTickMixin.class"
        with zipfile.ZipFile(io.BytesIO(compatibility_jar())) as jar:
            names = jar.namelist()
            self.assertIn(class_path, names)
            self.assertIn("techquest-compat.mixins.json", names)
            config = json.loads(jar.read("techquest-compat.mixins.json"))
            self.assertEqual(config["client"], ["BetterZoomEarlyTickMixin"])
            self.assertIn('config="techquest-compat.mixins.json"',
                          jar.read("META-INF/neoforge.mods.toml").decode())
            compiled = jar.read(class_path)
            self.assertTrue(compiled.startswith(bytes.fromhex("cafebabe")))
            # SpongePowered Mixin @Mixin is retained in RuntimeInvisibleAnnotations
            # (RetentionPolicy.CLASS), not RuntimeVisibleAnnotations.
            self.assertIn(b"RuntimeInvisibleAnnotations", compiled)
            self.assertIn(b"Lorg/spongepowered/asm/mixin/Mixin;", compiled)

    def test_global_apotheosis_commands_and_persistent_scoreboard(self):
        with zipfile.ZipFile(io.BytesIO(micro_patch_datapack())) as z:
            load = json.loads(z.read("data/minecraft/tags/function/load.json"))
            tick = json.loads(z.read("data/minecraft/tags/function/tick.json"))
            self.assertIn("techquest:worldtier/load", load["values"])
            self.assertIn("techquest:worldtier/tick", tick["values"])
            startup = z.read("data/techquest/function/worldtier/load.mcfunction").decode()
            self.assertIn("scoreboard objectives add tq_worldtier dummy", startup)
            self.assertIn("unless score #global", startup)
            sync = z.read("data/techquest/function/worldtier/sync.mcfunction").decode()
            for i,tier in enumerate(("frontier", "ascent", "summit", "pinnacle"), 1):
                pred = json.loads(z.read("data/techquest/predicate/worldtier/" + tier + ".json"))
                self.assertEqual(pred["condition"], "minecraft:entity_properties")
                self.assertEqual(json.loads(pred["predicate"]["nbt"])["neoforge:attachments"]["apotheosis:world_tier"], tier)
                self.assertIn("run apoth set_world_tier @s " + tier, sync)
                self.assertIn("run scoreboard players set #global tq_worldtier " + str(i), sync)
            self.assertEqual(z.testzip(), None)

if __name__ == "__main__":
    unittest.main()

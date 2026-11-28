"""Guard against version branch forks shipping a pack without the Incoming damage bridge."""
import io, json, unittest, zipfile
from pathlib import Path
import build_pack
ROOT=Path(__file__).resolve().parents[1]
MIXINS=("IncomingLethalCapMixin","IncomingLegendaryBossMixin","IncomingLegendaryMiniBossMixin","IncomingMonstrosityMixin")
class DamageIntegration0337(unittest.TestCase):
    def test_world_tick_fix_survives(self):
        text=(ROOT/"compat/hotfix-src/techquest/compat/mixin/BossTrackingRangeMixin.java").read_text()
        self.assertIn("EntityType.getKey(type)",text)
        self.assertNotIn("BuiltInRegistries",text)
    def test_all_four_damage_mixins_in_real_compat_jar(self):
        registered=json.loads((ROOT/"compat/techquest-compat/techquest-compat.mixins.json").read_text())
        self.assertIn("BossTrackingRangeMixin",registered["mixins"])
        for name in MIXINS:
            self.assertIn(name,registered["mixins"])
        with zipfile.ZipFile(io.BytesIO(build_pack.compatibility_jar())) as jar:
            for name in MIXINS:
                entry="techquest/compat/mixin/"+name+".class"
                self.assertEqual(jar.namelist().count(entry),1)
                self.assertTrue(jar.read(entry).startswith(bytes.fromhex("cafebabe")))
        self.assertEqual(build_pack.load_cfg()["version"],"0.3.3.10")
    def test_incoming_damage_types_not_lost(self):
        with zipfile.ZipFile(io.BytesIO(build_pack.compatibility_jar())) as jar:
            tag=json.loads(jar.read("data/cataclysm/tags/damage_type/bypasses_hurt_time.json"))
        self.assertFalse(tag["replace"])
        self.assertTrue({"incoming:shockwave","incoming:kinetic","incoming:burn_shock","incoming:player_nuclear_blast"}.issubset(tag["values"]))
if __name__=="__main__": unittest.main()

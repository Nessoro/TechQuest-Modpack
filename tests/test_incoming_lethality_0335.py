"""Regression checks for original Incoming damage versus Cataclysm boss damage caps.

This is a *source/bytecode* integration test, NOT a Minecraft world test.
The Java harness uses type-only test stubs; actual Mixin target signatures
are also exercised by the real client-menu smoke workflow.
"""
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "compat/hotfix-src/techquest/compat/mixin/IncomingLethalCapMixin.java"
CLASS = "techquest/compat/mixin/IncomingLethalCapMixin.class"
STUBS = ROOT / "compat/hotfix-stubs"
TAG = ROOT / "compat/techquest-compat/data/cataclysm/tags/damage_type/bypasses_hurt_time.json"
INCOMING = {
    "strike", "shockwave", "kinetic",
    "nuclear_blast", "player_nuclear_blast",
    "nuclear_thermal", "player_nuclear_thermal",
    "radiation", "player_radiation", "burn_shock",
    "debris", "fragment",
}
HARNESS = """
package techquest.compat.mixin;
import java.lang.reflect.Method;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;

public final class IncomingLethalHarness {
  static final class Instance extends IncomingLethalCapMixin {}
  private static DamageSource source(String namespace, String path) {
    ResourceKey<DamageType> key = ResourceKey.create(Registries.DAMAGE_TYPE, ResourceLocation.fromNamespaceAndPath(namespace, path));
    return new DamageSource(key);
  }
  private static void eq(float expected, float actual, String label) {
    if (Float.compare(expected, actual) != 0) throw new AssertionError(label + ": expected " + expected + " received " + actual);
  }
  public static void main(String[] args) throws Exception {
    Method clamp = IncomingLethalCapMixin.class.getDeclaredMethod("techquest$incomingOriginalDamage",
        float.class, float.class, DamageSource.class, float.class);
    clamp.setAccessible(true);
    Object mixin = new Instance();
    String[] names = {"strike","shockwave","kinetic","nuclear_blast","player_nuclear_blast",
        "nuclear_thermal","player_nuclear_thermal","radiation","player_radiation","burn_shock",
        "debris","fragment"};
    for (String id : names) {
      eq(316f, (float)clamp.invoke(mixin,22f,316f,source("incoming",id),316f),id+" injury");
      eq(Float.MAX_VALUE, (float)clamp.invoke(mixin,22f,Float.MAX_VALUE,
          source("incoming",id),Float.MAX_VALUE),id+" fatal");
      eq(5f, (float)clamp.invoke(mixin,22f,5f,source("incoming",id),5f),id+" weak");
    }
    Method range = IncomingLethalCapMixin.class.getDeclaredMethod("techquest$incomingNoAttackerRangeCap",
        double.class, DamageSource.class, float.class);
    range.setAccessible(true);
    for (String id : names) {
      double distance = (double)range.invoke(mixin, 2000000.0, source("incoming", id), 15.0f);
      if (distance != -1.0) throw new AssertionError(id+" attacker distance must not reject valid airstrike");
    }
    double vanillaDistance = (double)range.invoke(mixin, 2000000.0, source("minecraft", "explosion"), 15.0f);
    if (vanillaDistance != 2000000.0) throw new AssertionError("Non-Incoming range was modified");
    for (String other : new String[]{"minecraft","cataclysm","superbwarfare","custom"}) {
      eq(22f, (float)clamp.invoke(mixin,22f,Float.MAX_VALUE,
          source(other,"shockwave"),Float.MAX_VALUE),other+" unchanged");
    }
    System.out.println("PASS: Incoming severe/fatal preserved, normal/foreign damage unchanged.");
  }
}
"""


class IncomingLethalityTests(unittest.TestCase):
    def test_policy_is_source_scoped_and_preserves_immunity(self):
        src = SOURCE.read_text()
        self.assertIn('com.github.L_Ender.cataclysm.entity.AnimationMonster.BossMonsters.LLibrary_Boss_Monster',src)
        self.assertIn('target = "Ljava/lang/Math;min(FF)F"',src)
        self.assertIn("return Math.min(perHitCap, damage)",src)
        self.assertIn('@ModifyVariable(method = "hurt(', src)
        self.assertIn('at = @At("STORE"), ordinal = 0', src)
        self.assertEqual(set(re.findall(r'type\("([a-z_]+)"\)',src)),INCOMING)
        for forbidden in ("setHealth(", "kill(", "bypasses_invulnerability",
                          "DamageTypeTags.BYPASSES_INVULNERABILITY", "LivingEntity.class"):
            self.assertNotIn(forbidden,src)
        cfg = json.loads((ROOT / "compat/techquest-compat/techquest-compat.mixins.json").read_text())
        self.assertIn("IncomingLethalCapMixin",cfg["mixins"])
        self.assertNotIn("IncomingLethalCapMixin",cfg["client"])

    def test_incoming_damage_types_bypass_only_cataclysm_internal_damage_bucket(self):
        data=json.loads(TAG.read_text())
        self.assertFalse(data["replace"])
        self.assertTrue({"incoming:"+v for v in INCOMING}.issubset(data["values"]))
        self.assertFalse(any("bypasses_invulnerability" in v for v in data["values"]))

    def test_compiled_bytecode_and_physical_hit_logic(self):
        javac,java,javap = (shutil.which(name) for name in ("javac","java","javap"))
        if not javac or not java or not javap:
            self.skipTest("JDK 21 unavailable: real CI also installs Temurin 21")
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)
            harness=dest/"IncomingLethalHarness.java"
            harness.write_text(HARNESS)
            sources=sorted(STUBS.rglob("*.java"))
            self.assertEqual(len(sources),14)
            subprocess.run([javac,"--release","21","-g:none","-d",tmp,
                            *(str(p) for p in sources),str(SOURCE),str(harness)],
                           check=True,capture_output=True,text=True)
            compiled=dest/CLASS
            with zipfile.ZipFile(io.BytesIO(build_pack.compatibility_jar())) as z:
                self.assertEqual(compiled.read_bytes(), z.read(CLASS))
            inspection=subprocess.check_output([javap,"-v","-p",str(compiled)],text=True)
            self.assertIn("RuntimeInvisibleAnnotations:",inspection)
            self.assertIn("org.spongepowered.asm.mixin.Mixin",inspection)
            self.assertIn("org.spongepowered.asm.mixin.injection.Redirect",inspection)
            self.assertIn("org.spongepowered.asm.mixin.injection.ModifyVariable",inspection)
            subprocess.run([java,"-cp",tmp,"techquest.compat.mixin.IncomingLethalHarness"],
                           check=True,capture_output=True,text=True)

    def test_client_and_server_packaging_has_one_identical_mixin(self):
        jar = build_pack.compatibility_jar()
        with zipfile.ZipFile(io.BytesIO(jar)) as z:
            self.assertTrue(z.read(CLASS).startswith(bytes.fromhex("cafebabe")))
            self.assertEqual(z.namelist().count(CLASS),1)
        with tempfile.TemporaryDirectory() as tmp:
            pack=Path(tmp)/"test.mrpack"
            build_pack.make_mrpack(build_pack.load_cfg(),[],pack)
            with zipfile.ZipFile(pack) as z:
                self.assertEqual(z.read("overrides/mods/"+build_pack.COMPAT_JAR_NAME),jar)
        self.assertEqual(build_pack.load_cfg()["version"],"0.3.3.5")


if __name__=="__main__":
    unittest.main()

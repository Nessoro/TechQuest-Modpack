"""Isolated JVM tests for the IA-branch Monstrosity bridge, not a game test."""
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
import build_pack

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "compat/hotfix-src/techquest/compat/mixin/IncomingMonstrosityMixin.java"
STUBS = ROOT / "compat/hotfix-stubs"
TARGET = "com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.NewNetherite_Monstrosity.Netherite_Monstrosity_Entity"
CLASS = "techquest/compat/mixin/IncomingMonstrosityMixin.class"

HARNESS = """
import java.lang.reflect.Method;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageSource;
import techquest.compat.mixin.IncomingMonstrosityMixin;
import com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.NewNetherite_Monstrosity.Netherite_Monstrosity_Entity;

public class MonstrosityProbe {
  static class OtherIABoss extends IncomingMonstrosityMixin {}
  static DamageSource src(String ns,String name) {
    return new DamageSource(ResourceKey.create(Registries.DAMAGE_TYPE, ResourceLocation.fromNamespaceAndPath(ns,name)));
  }
  static void check(boolean ok) { if (!ok) throw new AssertionError("unexpected damage policy"); }
  public static void main(String[] args) throws Exception {
    var cap=IncomingMonstrosityMixin.class.getDeclaredMethod("techquest$incomingOriginalDamage",float.class,float.class,DamageSource.class,float.class);
    var range=IncomingMonstrosityMixin.class.getDeclaredMethod("techquest$incomingNoAttackerRangeCap",double.class,DamageSource.class,float.class);
    cap.setAccessible(true); range.setAccessible(true);
    var target = new Netherite_Monstrosity_Entity();
    var other = new OtherIABoss();
    for (String id: new String[]{"strike","shockwave","kinetic","nuclear_blast","player_nuclear_blast","nuclear_thermal","player_nuclear_thermal","radiation","player_radiation","burn_shock","debris","fragment"}) {
      var hit=src("incoming",id);
      for (float damage:new float[]{5f,316f,Float.MAX_VALUE}) {
        check((float)cap.invoke(target,22f,damage,hit,damage)==damage);
        check((float)cap.invoke(other,22f,damage,hit,damage)==Math.min(22f,damage));
      }
      check((double)range.invoke(target,2000000.0,hit,316f)==-1.0);
      check((double)range.invoke(other,2000000.0,hit,316f)==2000000.0);
    }
    for (String ns:new String[]{"minecraft","cataclysm","superbwarfare","custom"}) {
      var hit=src(ns,"shockwave");
      check((float)cap.invoke(target,22f,316f,hit,316f)==22f);
      check((double)range.invoke(target,2000000.0,hit,316f)==2000000.0);
    }
    var unknown=src("incoming","unknown");
    check((float)cap.invoke(target,22f,316f,unknown,316f)==22f);
    check((double)range.invoke(target,2000000.0,unknown,316f)==2000000.0);
    System.out.println("PASS: concrete boss and source scoped, partial/lethal preserved");
  }
}
"""

class MonstrosityBridgeTests(unittest.TestCase):
    def test_scoped_and_packaged(self):
        source=SOURCE.read_text()
        self.assertIn("com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.IABoss_monster",source)
        self.assertIn(TARGET,source)
        for forbidden in ("setHealth(", "kill(", "remove(", "BYPASSES_INVULNERABILITY", "getAttackState(", "hurtParts("):
            self.assertNotIn(forbidden,source)
        with zipfile.ZipFile(io.BytesIO(build_pack.compatibility_jar())) as jar:
            registered=json.loads(jar.read("techquest-compat.mixins.json"))
            self.assertIn("IncomingMonstrosityMixin",registered["mixins"])
            self.assertNotIn("IncomingMonstrosityMixin",registered["client"])
            self.assertEqual(jar.namelist().count(CLASS),1)
            self.assertTrue(jar.read(CLASS).startswith(bytes.fromhex("cafebabe")))

    def test_concrete_class_and_damage_source(self):
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK 21 required")
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            target=root/"Netherite_Monstrosity_Entity.java"
            target.write_text("package com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.NewNetherite_Monstrosity; public class Netherite_Monstrosity_Entity extends techquest.compat.mixin.IncomingMonstrosityMixin {}")
            harness=root/"MonstrosityProbe.java"
            harness.write_text(HARNESS)
            subprocess.run([javac,"--release","21","-g:none","-d",tmp,*(str(p) for p in sorted(STUBS.rglob("*.java"))),str(SOURCE),str(target),str(harness)],check=True,capture_output=True,text=True)
            result=subprocess.run([java,"-cp",tmp,"MonstrosityProbe"],check=True,capture_output=True,text=True)
            self.assertIn("PASS: concrete boss",result.stdout)
            with zipfile.ZipFile(io.BytesIO(build_pack.compatibility_jar())) as jar:
                self.assertEqual(jar.read(CLASS),(root/CLASS).read_bytes())

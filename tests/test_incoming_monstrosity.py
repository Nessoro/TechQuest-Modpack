"""Isolated handler regression, not actual Minecraft Mixin weaving or gameplay."""
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
SRC = ROOT / "compat/hotfix-src/techquest/compat/mixin/IncomingMonstrosityMixin.java"
STUBS = ROOT / "compat/hotfix-stubs"
BOSS = "com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.NewNetherite_Monstrosity"
BOSS_SRC = """package """ + BOSS + """;
import techquest.compat.mixin.IncomingMonstrosityMixin;
public final class Netherite_Monstrosity_Entity extends IncomingMonstrosityMixin {
  public int state;
  public int getAttackState() { return state; }
}
"""
HARNESS = """package techquest.compat.mixin;
import java.lang.reflect.Method;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageSource;
import """ + BOSS + """.Netherite_Monstrosity_Entity;
public final class MonstrosityHarness {
  static final class OtherBoss extends IncomingMonstrosityMixin {
    public int getAttackState() { return 0; }
  }
  static DamageSource source(String ns, String id) {
    return new DamageSource(ResourceKey.create(Registries.DAMAGE_TYPE, ResourceLocation.fromNamespaceAndPath(ns,id)));
  }
  static void check(Method cap, Method range, Object boss, DamageSource src,
                    float original, float expected, double dist) throws Exception {
    float actual = (float) cap.invoke(boss,22f,original,src,original);
    double actualDist = (double) range.invoke(boss,2000000.0,src,original);
    if (Float.compare(actual,expected)!=0 || Double.compare(actualDist,dist)!=0)
      throw new AssertionError("Expected "+expected+"/"+dist+" got "+actual+"/"+actualDist);
  }
  public static void main(String[] args) throws Exception {
    Method cap = IncomingMonstrosityMixin.class.getDeclaredMethod("techquest$incomingOriginalDamage",float.class,float.class,DamageSource.class,float.class);
    Method range = IncomingMonstrosityMixin.class.getDeclaredMethod("techquest$incomingNoAttackerRangeCap",double.class,DamageSource.class,float.class);
    cap.setAccessible(true); range.setAccessible(true);
    var boss = new Netherite_Monstrosity_Entity();
    var other = new OtherBoss();
    for (String id : new String[]{"strike","shockwave","kinetic","nuclear_blast","player_nuclear_blast","nuclear_thermal","player_nuclear_thermal","radiation","player_radiation","burn_shock","debris","fragment"}) {
      DamageSource src = source("incoming",id);
      boss.state = 0;
      check(cap,range,boss,src,316f,316f,-1);
      check(cap,range,boss,src,Float.MAX_VALUE,Float.MAX_VALUE,-1);
      check(cap,range,boss,src,5f,5f,-1);
      boss.state = 4;
      check(cap,range,boss,src,316f,22f,2000000);
      check(cap,range,other,src,316f,22f,2000000);
    }
    boss.state = 0;
    for (String ns : new String[]{"minecraft","superbwarfare","cataclysm","custom"})
      check(cap,range,boss,source(ns,"shockwave"),316f,22f,2000000);
    check(cap,range,boss,source("incoming","unknown"),316f,22f,2000000);
  }
}
"""

class MonstrosityTests(unittest.TestCase):
    def test_source_and_registered_class(self):
        source = SRC.read_text()
        self.assertIn("IABossMonsters.IABoss_monster",source)
        self.assertIn("getAttackState() != 4",source)
        self.assertNotIn("setHealth(",source)
        self.assertNotIn("BYPASSES_INVULNERABILITY",source)
        config = json.loads((ROOT/"compat/techquest-compat/techquest-compat.mixins.json").read_text())
        self.assertIn("IncomingMonstrosityMixin",config["mixins"])
        with zipfile.ZipFile(io.BytesIO(build_pack.compatibility_jar())) as jar:
            name = "techquest/compat/mixin/IncomingMonstrosityMixin.class"
            self.assertEqual(jar.namelist().count(name),1)
            self.assertTrue(jar.read(name).startswith(bytes.fromhex("cafebabe")))

    def test_handler_policy(self):
        javac,java = shutil.which("javac"),shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK21 required")
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            boss=out/"Netherite_Monstrosity_Entity.java"
            boss.write_text(BOSS_SRC)
            harness=out/"MonstrosityHarness.java"
            harness.write_text(HARNESS)
            subprocess.run([javac,"--release","21","-g:none","-d",tmp,
                            *(str(p) for p in sorted(STUBS.rglob("*.java"))),
                            str(SRC),str(boss),str(harness)],check=True,capture_output=True,text=True)
            subprocess.run([java,"-cp",tmp,"techquest.compat.mixin.MonstrosityHarness"],
                           check=True,capture_output=True,text=True)

"""Isolated JVM regression for selective tracking; not a Minecraft runtime test."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "compat/hotfix-stubs"
SOURCE = ROOT / "compat/hotfix-src/techquest/compat/mixin/BossTrackingRangeMixin.java"

ENTITY = """package net.minecraft.world.entity;
import net.minecraft.resources.ResourceLocation;
import techquest.compat.mixin.BossTrackingRangeMixin;
public class EntityType<T> extends BossTrackingRangeMixin {
 private final ResourceLocation id;
 public EntityType(ResourceLocation id) { this.id=id; }
 public static ResourceLocation getKey(EntityType<?> type) { return type.id; }
 public int clientTrackingRange(){ return 0; }
}
"""
CALLBACK = """package org.spongepowered.asm.mixin.injection.callback;
public class CallbackInfoReturnable<T> {
 private T value;
 public CallbackInfoReturnable(T value) { this.value=value; }
 public int getReturnValueI() { return (Integer)value; }
 public void setReturnValue(T t) { value=t; }
}
"""
PROBE = """import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EntityType;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import techquest.compat.mixin.BossTrackingRangeMixin;
public class TrackingProbe {
 static int cases;
 static void check(String ns, String path, int before, int expected) throws Exception {
  var type = new EntityType<>(ns == null ? null : ResourceLocation.fromNamespaceAndPath(ns,path));
  var cir = new CallbackInfoReturnable<Integer>(before);
  var method = BossTrackingRangeMixin.class.getDeclaredMethod("techquest$bossTrackingRange", CallbackInfoReturnable.class);
  method.setAccessible(true); method.invoke(type,cir);
  if (cir.getReturnValueI()!=expected) throw new AssertionError(ns+":"+path+" got "+cir.getReturnValueI());
  cases++;
 }
 public static void main(String[] args) throws Exception {
  for (String id : new String[]{"ender_golem","ender_guardian","netherite_monstrosity","ignis","the_harbinger","the_leviathan","ancient_remnant","scylla","clawdian","maledictus","the_prowler"}) check("cataclysm",id,5,14);
  check("legendary_monsters","the_obliterator",5,14);
  check("legendary_monsters","the_obliterator",20,20);
  check("legendary_monsters","the_obliterator_clone",6,6);
  check("legendary_monsters","the_obliterator_clone_armed",6,6);
  check("legendary_monsters","cloud_golem",5,5);
  check("minecraft","zombie",5,5);
  check("othermod","the_obliterator",5,5);
  check("cataclysm","ender_guardian_bullet",4,4);
  check(null,null,5,5);
  System.out.println("PASS: "+cases+" isolated tracking cases");
 }
}
"""

class ObliteratorTrackingTests(unittest.TestCase):
    def test_exact_allowlist_and_preserved_ranges(self):
        javac, java = shutil.which("javac"), shutil.which("java")
        if not javac or not java:
            self.skipTest("JDK 21 required; CI installs it")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            stubs = root / "stubs"
            shutil.copytree(STUBS, stubs)
            (stubs / "net/minecraft/world/entity/EntityType.java").write_text(ENTITY)
            (stubs / "org/spongepowered/asm/mixin/injection/callback/CallbackInfoReturnable.java").write_text(CALLBACK)
            probe = root / "TrackingProbe.java"
            probe.write_text(PROBE)
            output = root / "classes"
            subprocess.run([javac, "--release", "21", "-d", str(output),
                            *(str(p) for p in sorted(stubs.rglob("*.java"))),
                            str(SOURCE), str(probe)], check=True, capture_output=True, text=True)
            result = subprocess.run([java, "-cp", str(output), "TrackingProbe"],
                                    check=True, capture_output=True, text=True)
            self.assertIn("PASS: 20 isolated tracking cases", result.stdout)

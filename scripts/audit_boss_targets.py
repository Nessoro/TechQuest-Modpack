"""Check pinned original boss JARs and their actual bytecode after assembling both sides."""
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARENT="com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.IABoss_monster"
BOSS="com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.NewNetherite_Monstrosity.Netherite_Monstrosity_Entity"
PART=BOSS.replace("_Entity","_Part")
LEG="net.miauczel.legendary_monsters"
OBL=LEG+".entity.AnimatedMonster.IAnimatedBoss.TheObliterator.TheObliteratorEntity"

def disasm(jar, name):
    return subprocess.check_output(["javap","-p","-c","-classpath",str(jar),name],text=True,stderr=subprocess.STDOUT)

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def main():
    locks=json.loads((ROOT/"modlist.json").read_text())["modrinth_lock"]
    jars={}
    for pid, version in (("46KJle7n","3.33"),("9d9Bkqva","2.2.4")):
        lock=locks[pid]
        require(lock["version"]==version, "unexpected boss pin "+pid)
        for side in ("client","server"):
            path=ROOT/"output"/side/"mods"/lock["filename"]
            require(hashlib.sha512(path.read_bytes()).hexdigest()==lock["sha512"], "pinned hash mismatch "+str(path))
        jars[pid]=ROOT/"output"/"client"/"mods"/lock["filename"]
    cat=jars["46KJle7n"]
    entity=disasm(cat,BOSS)
    parent=disasm(cat,PARENT)
    part=disasm(cat,PART)
    require("extends "+PARENT in entity,"Netherite parent mismatch")
    require("getAttackState" in entity and "hurtParts(" in entity and "isMultipartEntity(" in entity,"Netherite guard or multipart signature mismatch")
    require("hurtParts" in part,"part delegation not found")
    require("boolean hurt(net.minecraft.world.damagesource.DamageSource, float)" in parent,"parent hurt descriptor mismatch")
    require("java/lang/Math.min:(FF)F" in parent and "calculateRange" in parent,"parent cap/range instruction mismatch")
    lm=jars["9d9Bkqva"]
    registry=disasm(lm,LEG+".entity.ModEntities")
    require("String the_obliterator" in registry,"Obliterator registry path absent")
    with zipfile.ZipFile(lm) as z:
        metadata=z.read("META-INF/neoforge.mods.toml").decode("utf-8")
        require("legendary_monsters" in metadata,"Legendary Monsters namespace absent")
    for name in (OBL,LEG+".entity.AnimatedMonster.OriginClasses.IAnimatedBoss",LEG+".entity.client.Render.TheObliteratorRenderer"):
        text=disasm(lm,name)
        matches=[line.strip() for line in text.splitlines() if "shouldRender" in line or "getBoundingBoxForCulling" in line or "noCulling" in line]
        print(name,"client culling declarations/references:",matches)
    report=ROOT/"output"/"boss-target-bytecode"
    report.mkdir(exist_ok=True)
    for name, content in (("netherite.txt",entity),("ia-parent.txt",parent),("part.txt",part),("obliterator-registry.txt",registry)):
        # Preserve evidence locally only; do not redistribute third-party code.
        (report/name).write_text(content)
    print("PASS: exact pinned client/server boss hashes, IA hierarchy, cap/range bytecode, multipart delegation and Obliterator registry path")
    print("Static bytecode evidence only; actual gameplay and client culling remain open.")

if __name__=="__main__":
    main()

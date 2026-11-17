#!/usr/bin/env python3
"""Check custom biome registration/modifiers, unknown-id filtering and vanilla control."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("base","tool","baseline-tool","work"): parser.add_argument("--"+key,type=Path,required=True)
    args=parser.parse_args();work=args.work.absolute()
    if work.exists() or work.is_symlink() or any(p.is_symlink() for p in work.parents): raise ValueError("new work outside resources required")
    if work==args.base.resolve() or args.base.resolve() in work.parents: raise ValueError("work must be outside base")
    work.mkdir(parents=True,mode=0o700);module=work/"fixture";module.mkdir()
    (module/"horizon-mod.toml").write_text('id="techquest_biome_fixture"\nname="Developer biome fixture"\nversion="1"\napi="0.2"\nside="both"\ncapabilities=["registries"]\n')
    def write(name,value):
        p=module/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
    biomes=json.loads((args.base/"worldgen/biomes.json").read_text());plains=json.loads(biomes["minecraft:plains"])
    feature="minecraft:ore_debris_small"
    assert feature in json.loads((args.base/"worldgen/placed_features.json").read_text())
    assert not any(feature in step for step in plains["features"])
    write("data/techquest_biome_fixture/worldgen/biome/valid.json",plains)
    write("data/techquest_biome_fixture/tags/worldgen/biome/targets.json",{"values":["minecraft:plains","techquest_biome_fixture:valid","techquest_biome_fixture:missing"]})
    write("data/techquest_biome_fixture/neoforge/biome_modifier/ore.json",{"type":"neoforge:add_features","biomes":"#techquest_biome_fixture:targets","features":feature,"step":"underground_ores"})
    def build(tool,name,mods):
        out=work/name
        with (work/(name+".log")).open("x") as f:subprocess.run([str(tool.resolve()),"build",str(args.base.resolve()),str(out),*map(str,mods)],stdout=f,stderr=subprocess.STDOUT,check=True)
        return out
    baseline=build(args.baseline_tool,"baseline",[module]);fixed=build(args.tool,"fixed",[module]);vanilla=build(args.tool,"vanilla",[])
    old=json.loads((baseline/"worldgen/biomes.json").read_text());new=json.loads((fixed/"worldgen/biomes.json").read_text())
    assert "techquest_biome_fixture:valid" not in old
    assert "techquest_biome_fixture:valid" in new
    for name in ("minecraft:plains","techquest_biome_fixture:valid"):
        value=json.loads(new[name]);assert sum(step.count(feature) for step in value["features"])==1
    assert json.loads(new["minecraft:desert"])==json.loads(biomes["minecraft:desert"])
    tag=json.loads((fixed/"data/techquest_biome_fixture/tags/worldgen/biome/targets.json").read_text())
    assert set(tag["values"])=={"minecraft:plains","techquest_biome_fixture:valid"}
    for name in ("worldgen/biomes.json","worldgen/biome_tags.json"):
        assert (vanilla/name).read_bytes()==(args.base/name).read_bytes(),name
    report={"schema":1,"baseline_custom_biome_missing":True,"fixed_custom_biome_registered":True,
            "modifier_applies_once_to_vanilla_and_custom_target":True,"untargeted_desert_unchanged":True,
            "unknown_biome_still_filtered":True,"vanilla_without_mods_bundles_byte_identical":True,
            "baseline_tool_sha256":hashlib.sha256(args.baseline_tool.read_bytes()).hexdigest(),
            "fixed_tool_sha256":hashlib.sha256(args.tool.read_bytes()).hexdigest()}
    (work/"checked-result.json").write_text(json.dumps(report,indent=2)+"\n");print("Biome modifier controls passed")


if __name__=="__main__": main()

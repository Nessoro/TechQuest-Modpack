#!/usr/bin/env python3
"""Find naturally generated starter ores with the installed Terralith datapack.

No ore blocks/features or raw materials are injected. A small access space is
carved next to each found block; an iron pickaxe is supplied for the mining test.
This does not assert whole-world generation/RNG parity with Minecraft 1.21.1.
"""
import argparse
import json
from pathlib import Path
import shutil
from graphical_fixture import GraphicalFixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir","work"):parser.add_argument("--"+name,type=Path,required=True)
    args=parser.parse_args();g=GraphicalFixture(args.server_dir,args.work,"0.2.0","techquest-oritech-ores","TQOreMine",module="oritech",frozen=True)
    shutil.copytree(g.server/"techquest-horizon-test/datapacks",g.work/"saves"/g.world/"datapacks")
    cmd,call,settle=g.command,g.call,g.settle;found=[]
    def travel(dimension,pos):
        cmd("gamemode spectator");cmd(f"execute in {dimension} run tp @s "+" ".join(map(str,pos)))
        call("wait-ready",timeout=180);call("wait",20)
    def mine(dimension,block,raw):
        search=call("find-block",block,64);assert search["count"]>0,(block,search)
        pos=search["nearest"][0]["pos"];x,y,z=pos
        before=call("block",*pos);assert before["block"]==block,before
        if dimension=="minecraft:overworld":
            assert "Test passed" in cmd(f"execute if biome {x} {y} {z} #terralith:all_terralith_biomes")
        # Keep the naturally generated target; clear only the access cells.
        for dx,dy,dz in [(0,0,1),(0,1,1),(0,0,2),(0,1,2)]:cmd(f"setblock {x+dx} {y+dy} {z+dz} minecraft:air")
        cmd(f"setblock {x} {y-1} {z+2} minecraft:cobblestone")
        cmd(f"tp @s {x+0.5} {y} {z+2.5}");cmd("difficulty peaceful");cmd("gamemode survival")
        cmd("give @s minecraft:iron_pickaxe 1");call("select","minecraft:iron_pickaxe");settle();cmd("tick unfreeze")
        mined=call("break",*pos,"--timeout",20,timeout=30)
        cmd(f"tp @s {x+0.5} {y} {z+0.5}");call("wait",40);cmd("tick freeze")
        after=call("block",*pos);assert after["block"]=="minecraft:air",(before,after,mined)
        assert call("inventory")["counts"].get(raw,0)==1
        call("screenshot",g.work/(raw.split(":")[1]+"-mined.png"))
        found.append({"dimension":dimension,"block":block,"pos":pos,"natural_blocks_found":search["count"],"raw":raw,"mining_reply":mined})
    try:
        g.start("mine");cmd("clear @s")
        assert "techquest_terralith" in cmd("datapack list enabled")
        travel("minecraft:overworld",(-2272,-24,2272))
        assert "Test passed" in cmd("execute if biome -2272 71 2272 terralith:arid_highlands")
        mine("minecraft:overworld","oritech:nickel_ore","oritech:raw_nickel")
        travel("minecraft:the_end",(0,64,0))
        mine("minecraft:the_end","oritech:endstone_platinum_ore","oritech:raw_platinum")
        saved=call("inventory")["counts"];call("save")
    finally:g.stop()
    try:
        g.start("reopen");cmd("tick freeze")
        assert call("inventory")["counts"]==saved
        for record in found:
            travel(record["dimension"],record["pos"])
            assert call("block",*record["pos"])["block"]=="minecraft:air"
        status=call("status");assert status["server"]["joined"] and status["server"]["decode_errors"]==0
        call("save")
    finally:g.stop()
    report={"schema":1,"prototype_version":"0.2.0","terralith_datapack_enabled":True,"found":found,
            "natural_nickel_in_terralith_biome":True,"natural_end_platinum":True,"survival_mining_produced_raw_materials":True,
            "ore_blocks_or_features_injected":False,"raw_items_given":False,"raw_inventory_and_broken_blocks_survive_reopen":True,
            "overworld_deepslate_platinum_generation_verified":False,"full_worldgen_rng_parity_tested":False,
            "licensed_dedicated_join_tested":False,"published":False}
    (g.work/"checked-result.json").write_text(json.dumps(report,indent=2)+"\n");print("Natural ore mining and save/reopen passed")


if __name__=="__main__":main()

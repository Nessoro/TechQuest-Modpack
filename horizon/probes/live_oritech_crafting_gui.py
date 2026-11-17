#!/usr/bin/env python3
"""Craft the starter chain with real menu clicks, then place/assemble/power it.

Vanilla inputs and metal-ingot fixtures are supplied explicitly. Oritech
machines, coils, alloys, energy and processing output are never given/injected.
Natural mining is a separate check; this probe does not claim a gathered run.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from graphical_fixture import GraphicalFixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ("server-dir","work"):parser.add_argument("--"+key,type=Path,required=True)
    args=parser.parse_args();g=GraphicalFixture(args.server_dir,args.work,"0.2.0","techquest-oritech-crafting","TQCraftGui",module="oritech",frozen=True)
    cmd,call,settle=g.command,g.call,g.settle;crafts=[]
    def counts():return call("inventory")["counts"]
    def slots():
        reply=call("screen");return reply,{s["slot"]:s for s in reply["slots"]}
    def craft(pattern,keys,output,count=1):
        before=counts();call("interact",0,200,0);settle();reply,visible=slots()
        assert {100+i for i in range(9)} <= set(visible) and 200 in visible,reply
        required=Counter()
        for y,row in enumerate(pattern):
            for x,symbol in enumerate(row):
                if symbol==" ":continue
                ident=keys[symbol];required[ident]+=1
                reply,visible=slots();source=next(i for i,s in visible.items() if i<36 and s.get("item")==ident)
                call("click-slot",source);settle();call("click-slot",100+3*y+x,"right");settle()
                reply,visible=slots()
                if reply.get("carried"):call("click-slot",source);settle()
        reply,visible=slots();assert visible[200].get("item")==output and visible[200]["count"]==count,reply
        call("click-slot",200);settle();reply,visible=slots()
        assert reply["carried"]["item"]==output and reply["carried"]["count"]==count,reply
        destination=next(i for i,s in sorted(visible.items()) if i<36 and not s.get("item"))
        call("click-slot",destination);settle();reply,visible=slots()
        assert not reply.get("carried") and all(not visible[100+i].get("item") for i in range(9)),reply
        after=Counter(counts());expected=Counter(before);expected.subtract(required);expected[output]+=count
        assert +after==+expected,(output,before,after,expected)
        crafts.append({"output":output,"count":count,"consumed":dict(required)})
        call("screenshot",g.work/(output.split(":")[1]+"-crafted.png"));call("close");settle()
    try:
        g.start("craft")
        cmd("fill -3 199 -3 6 199 5 minecraft:stone");cmd("setblock 0 200 0 minecraft:crafting_table");cmd("tp @s 1.5 200 3.5")
        call("wait-ready",timeout=180);cmd("clear @s");cmd("gamemode survival")
        for ident,n in {"minecraft:iron_ingot":6,"minecraft:coal":6,"minecraft:gold_ingot":2,"minecraft:redstone":2,
                        "oritech:nickel_ingot":11,"oritech:platinum_ingot":2,"minecraft:copper_ingot":4,
                        "minecraft:furnace":2,"minecraft:oak_planks":8,"minecraft:crafting_table":1}.items():cmd(f"give @s {ident} {n}")
        for _ in range(3):craft(["aa ","bb "],{"a":"minecraft:iron_ingot","b":"minecraft:coal"},"oritech:steel_ingot")
        craft(["aa ","bb "],{"a":"minecraft:gold_ingot","b":"minecraft:redstone"},"oritech:electrum_ingot")
        craft(["iii","ccc","iii"],{"i":"oritech:nickel_ingot","c":"oritech:steel_ingot"},"oritech:magnetic_coil",4)
        craft(["fff","fcf","sbs"],{"f":"oritech:nickel_ingot","c":"minecraft:copper_ingot","s":"oritech:magnetic_coil","b":"minecraft:furnace"},"oritech:basic_generator_block")
        craft(["fff","mcm","sbs"],{"f":"minecraft:copper_ingot","m":"oritech:platinum_ingot","c":"oritech:electrum_ingot","s":"oritech:magnetic_coil","b":"minecraft:furnace"},"oritech:powered_furnace_block")
        craft(["sss","scs","sss"],{"s":"minecraft:oak_planks","c":"minecraft:crafting_table"},"oritech:machine_core_1")
        expected={"oritech:basic_generator_block":1,"oritech:powered_furnace_block":1,"oritech:machine_core_1":1};assert counts()==expected,counts()
        for ident,pos in [("basic_generator_block",(2,200,0)),("powered_furnace_block",(3,200,0)),("machine_core_1",(3,201,0))]:
            call("place",*pos,"--item","oritech:"+ident);settle()
            assert counts().get("oritech:"+ident,0)==0
        assert counts()=={},counts();call("select",9);settle();call("interact",3,200,0);settle()
        assert "1b" in cmd("data get block 3 200 0 techquest_assembled")
        for ident,pos in [("minecraft:raw_iron",(3,200,0)),("minecraft:coal",(2,200,0))]:
            cmd(f"give @s {ident} 2");call("select",9);settle();call("interact",*pos);settle();reply,visible=slots()
            source=next(i for i,s in visible.items() if i<36 and s.get("item")==ident)
            call("click-slot",source);settle();call("click-slot",300);settle();call("close");settle()
        cmd("tick step 201");call("wait",210)
        call("interact",3,200,0);settle();reply,visible=slots()
        assert visible[301].get("item")=="minecraft:iron_ingot" and visible[301]["count"]==2,reply
        call("click-slot",301,"shift");settle();assert counts().get("minecraft:iron_ingot")==2
        call("screenshot",g.work/"crafted-pair-output.png");call("close");call("save");status=call("status")
        assert status["server"]["joined"] and status["server"]["decode_errors"]==0
    finally:g.stop()
    report={"schema":1,"prototype_version":"0.2.0","crafts":crafts,"recipe_inputs_consumed_exactly":True,
            "machines_and_alloys_not_given":True,"crafted_blocks_placed_by_player":True,"core_assembled_by_interaction":True,
            "crafted_pair_produced_two_collected_ingots":True,"vanilla_and_nickel_platinum_ingot_fixtures_given":True,
            "natural_mining_or_full_survival_gathering_tested":False,"licensed_dedicated_join_tested":False,"published":False}
    (g.work/"checked-result.json").write_text(json.dumps(report,indent=2)+"\n");print("Crafted and operated starter Oritech chain through real menu/placement packets")


if __name__=="__main__":main()

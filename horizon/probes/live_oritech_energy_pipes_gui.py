#!/usr/bin/env python3
"""Craft/place basic energy cables, power a remote furnace and reopen physically.

Electrum, machines/core, coal/raw iron, pickaxe, bench, platform, peaceful mode,
teleports and tick control are fixtures. Cables are crafted and placed through
normal survival interactions; energy, burn progress and outputs are never seeded.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import time

from graphical_fixture import GraphicalFixture
from live_oritech_gathered_gui import GatheredChain, TABLE

GEN=(-2269,200,2272)
FURNACE=(-2263,200,2272)
CORE=(-2263,201,2272)
WIRES=[(x,200,2272) for x in range(-2268,-2263)]
coord=lambda p:" ".join(map(str,p))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir","work"):parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--wrench-controls",action="store_true",help="cut/reconnect the live network with a craftable wrench fixture")
    parser.add_argument("--waterlogged-cables",action="store_true",help="waterlog all five cables with real bucket uses before powering them")
    args=parser.parse_args()
    game=GraphicalFixture(args.server_dir,args.work,("0.6.0","0.7.0","0.8.0"),"techquest-cables-gui","TQCableGui",module="oritech",frozen=True)
    shutil.copytree(game.server/"techquest-horizon-test/datapacks",game.work/"saves"/game.world/"datapacks")
    test=GatheredChain(game);cmd,call,settle=game.command,game.call,game.settle
    if args.wrench_controls:assert game.version in ("0.7.0","0.8.0")
    if args.waterlogged_cables:assert game.version=="0.8.0"
    def number(pos,key):
        reply=cmd("data get block "+coord(pos)+" "+key)
        match=re.search(r"has the following block data:\s*(-?\d+)",reply)
        assert match,reply
        return int(match[1])
    def step(n):cmd(f"tick step {n}");call("wait",n+8)
    def approach(pos):
        if args.waterlogged_cables:
            # Keep fixture access above the water during long processing
            # waits as well as clicks; a motionless player in the current can
            # otherwise drift off the small elevated work platform.
            cmd(f"setblock {pos[0]} 200 {pos[2]+3} minecraft:glass")
        cmd(f"tp @s {pos[0]+.5} {201 if args.waterlogged_cables else 200} {pos[2]+3.0}")
    def state():
        raw=cmd("data get block "+coord(FURNACE)+" Items")
        count=0
        for entry in re.findall(r"\{([^{}]+)\}",raw):
            if '"minecraft:iron_ingot"' in entry:count+=int(re.search(r"\bcount:\s*(\d+)",entry)[1])
        result={"generator_energy":number(GEN,"energy"),"generator_progress":number(GEN,'"oritech.machine_progress"'),
                "burn":number(GEN,"storedBurn"),"furnace_energy":number(FURNACE,"energy"),
                "furnace_progress":number(FURNACE,'"oritech.machine_progress"'),"furnace_items":raw.split("block data:")[-1].strip(),
                "source_buffer":number(WIRES[0],"energy"),"far_buffer":number(WIRES[-1],"energy"),
                "output_count":count,"inventory":test.counts(),"assembled":number(FURNACE,"techquest_assembled"),
                "core_used":number(CORE,"techquest_core_used"),"wires":[call("block",*p)["state"] for p in WIRES]}
        produced=(1600-result["generator_progress"])*32
        consumed=(100*(count+result["inventory"].get("minecraft:iron_ingot",0))+result["furnace_progress"])*32
        stored=sum(result[k] for k in ("generator_energy","furnace_energy","source_buffer","far_buffer"))
        assert produced==consumed+stored,(result,produced,consumed,stored)
        result.update(generated=produced,consumed=consumed,stored=stored)
        return result
    def place(item,pos,cable=False):
        before=test.counts().get(item,0);approach(pos)
        if not any(s.get("item")==item for s in call("inventory")["hotbar"]):
            call("open-inventory");settle();_,slots=test.slots()
            source=next(i for i,s in slots.items() if 9<=i<36 and s.get("item")==item)
            call("click-slot",source);settle();call("click-slot",8);settle()
            if call("screen").get("carried"):call("click-slot",source);settle()
            call("close")
        call("look-at-block",pos[0],pos[1]-1,pos[2]);settle()
        call("place",*pos,"--item",item);settle()
        block=call("block",*pos)["block"].split("[")[0]
        assert block in ("oritech:energy_pipe","oritech:energy_pipe_connection") if cable else block==item
        assert test.counts().get(item,0)==before-1
    def open_machine(pos,count):
        approach(pos);test.empty_hand();call("interact",*pos);settle()
        screen,slots=test.slots();assert screen["screen"]=="container",screen
        assert {s for s in slots if 300<=s<500}==set(range(300,300+count)),screen
        return screen,slots
    def insert(pos,count,item,amount):
        screen,slots=open_machine(pos,count)
        source=next(i for i,s in slots.items() if i<36 and s.get("item")==item)
        assert slots[source]["count"]==amount
        call("click-slot",source);settle()
        if count==2:
            call("click-slot",301);settle();screen,slots=test.slots()
            assert screen["carried"]["item"]==item and not slots[301].get("item"),screen
        call("click-slot",300);settle();screen,slots=test.slots()
        assert slots[300].get("item")==item and slots[300]["count"]==amount and not screen.get("carried"),screen
        call("close");settle()
    def mine_and_collect(pos):
        before=test.counts().get("oritech:energy_pipe",0)
        approach(pos);call("select","minecraft:diamond_pickaxe");settle();cmd("tick unfreeze")
        result=call("break",*pos,"--timeout",20,timeout=30)
        assert result.get("drops",{}).get("oritech:energy_pipe")==1,result
        cmd(f"tp @s {pos[0]+.5} 200 {pos[2]+.5}");call("wait",35)
        for _ in range(4):
            if test.counts().get("oritech:energy_pipe",0)==before+1:break
            # Water carries the real dropped entity away from the mining
            # cell. Follow that entity, as the gathered-material GUI does.
            drops=[e for e in call("entities",32,"minecraft:item")["entities"]
                   if e.get("item",{}).get("item")=="oritech:energy_pipe"]
            assert drops,(result,test.counts())
            cmd("tp @s "+" ".join(map(str,drops[0]["pos"])));call("wait",15)
        cmd("tick freeze")
        assert test.counts().get("oritech:energy_pipe",0)==before+1,(result,test.counts())
        assert call("block",*pos)["block"]==("minecraft:water" if args.waterlogged_cables else "minecraft:air")
        return result
    def wrench_toggle(enabled):
        pos=WIRES[2]
        if args.waterlogged_cables:
            # A dry elevated access fixture keeps the real player outside
            # water currents. Both ray origins stay above the next cable and
            # miss the opposite active arm when reconnecting the center.
            cmd(f"setblock {pos[0]+3} 200 {pos[2]-1} minecraft:glass")
            cmd(f"tp @s {pos[0]+3.5} 201 {pos[2]-.31}")
            dx,dy,dz=3.0,2.18,.91
        else:
            cmd(f"setblock {pos[0]+1} 199 {pos[2]} minecraft:stone_slab[type=bottom]")
            cmd(f"tp @s {pos[0]+1.2} 199.5 {pos[2]+.05}")
            dx,dy,dz=.7,.665,.45
        # empty_hand may have moved the selected wrench out of the hotbar
        # before the screenshot. `select ITEM` only searches the hotbar.
        if not any(s.get("item")=="oritech:wrench" for s in call("inventory")["hotbar"]):
            call("open-inventory");settle();_,slots=test.slots()
            source=next(i for i,s in slots.items() if 9<=i<36 and s.get("item")=="oritech:wrench")
            destination=next(i for i in range(9) if not slots[i].get("item"))
            call("click-slot",source);settle();call("click-slot",destination);settle();call("close");settle()
        call("select","oritech:wrench");call("wait",12)
        call("look",math.degrees(math.atan2(dx,dz)),math.degrees(math.atan2(dy,math.hypot(dx,dz))));settle()
        assert call("looking-at")["block"]["pos"]==list(pos)
        call("mouse","right","click");settle()
        left,right=call("block",*pos)["state"],call("block",*WIRES[3])["state"]
        assert f"east={int(enabled)}" in left and f"west={int(enabled)}" in right,(left,right)
        if args.waterlogged_cables:assert "waterlogged=true" in left and "waterlogged=true" in right
        # Leave the half-height camera stand before replacing it with a
        # full block. Otherwise the fixture embeds the player in its floor.
        approach(pos)
        if not args.waterlogged_cables:cmd(f"setblock {pos[0]+1} 199 {pos[2]} minecraft:glass")
        return {"control":"wrench","enabled":enabled,"left":left,"right":right}
    supplied={"oritech:electrum_ingot":3,"oritech:basic_generator_block":1,"oritech:powered_furnace_block":1,
              "oritech:machine_core_1":1,"minecraft:coal":1,"minecraft:raw_iron":2,"minecraft:diamond_pickaxe":1}
    if args.wrench_controls:supplied["oritech:wrench"]=1
    try:
        game.start("craft-and-save");cmd("clear @s");cmd("difficulty peaceful");cmd("gamemode spectator")
        cmd("tp @s -2271.5 200 2275.5");call("wait-ready",timeout=180);cmd("tick freeze")
        cmd("forceload add -2288 2256 -2240 2288")
        deadline=time.monotonic()+120
        for p in ((-2275,199,2267),(-2261,199,2278)):
            while "Test passed" not in cmd("execute if loaded "+coord(p)):
                assert time.monotonic()<deadline,p
                call("wait",20)
        assert "Successfully filled" in cmd("fill -2275 199 2267 -2261 199 2278 minecraft:glass")
        cmd("setblock "+coord(TABLE)+" minecraft:crafting_table");cmd("gamemode survival")
        for item,amount in supplied.items():cmd(f"give @s {item} {amount}")
        cmd("tp @s -2271.5 200 2274.5")
        test.craft(["###"],{"#":"oritech:electrum_ingot"},"oritech:energy_pipe",6)
        place("oritech:basic_generator_block",GEN);place("oritech:powered_furnace_block",FURNACE)
        approach(FURNACE);test.empty_hand();call("interact",*FURNACE);settle()
        assert call("screen")["screen"]!="container" and number(FURNACE,"techquest_assembled")==0
        place("oritech:machine_core_1",CORE);approach(FURNACE);test.empty_hand();call("interact",*FURNACE);settle()
        assert call("screen")["screen"]!="container" and number(FURNACE,"techquest_assembled")==1
        for pos in WIRES:place("oritech:energy_pipe",pos,cable=True)
        if args.waterlogged_cables:
            for pos in WIRES:
                approach(pos);test.empty_hand();cmd("give @s minecraft:water_bucket")
                call("select","minecraft:water_bucket");call("interact",*pos);settle()
                assert "waterlogged=true" in call("block",*pos)["state"]
            supplied["minecraft:water_bucket"]=5
            assert test.counts().get("minecraft:bucket")==5 and not test.counts().get("minecraft:water_bucket")
        assert test.counts().get("oritech:energy_pipe")==1
        assert call("block",*WIRES[0])["block"]=="oritech:energy_pipe_connection"
        assert call("block",*WIRES[-1])["block"]=="oritech:energy_pipe_connection"
        for pos in WIRES[1:-1]:assert "not a block entity" in cmd("data get block "+coord(pos)).lower()
        insert(FURNACE,2,"minecraft:raw_iron",2);insert(GEN,1,"minecraft:coal",1)
        step(45);saved=state();assert saved["furnace_progress"] in (43,44,45),saved
        approach(WIRES[2]);call("look-at-block",*FURNACE);call("screenshot",game.work/"remote-working.png");call("save")
    finally:game.stop()
    try:
        game.start("reopen-and-break");cmd("tick freeze");reopened=state();assert reopened==saved,(saved,reopened)
        middle_break=wrench_toggle(False) if args.wrench_controls else mine_and_collect(WIRES[2]);step(40);paused=state();step(10);still=state()
        assert paused["furnace_progress"]==still["furnace_progress"] and still["furnace_energy"]==0,(paused,still)
        approach(WIRES[2]);call("look-at-block",*WIRES[3]);call("screenshot",game.work/"broken-cable-paused.png")
        if args.wrench_controls:wrench_toggle(True)
        else:place("oritech:energy_pipe",WIRES[2],cable=True)
        step(220);completed=state()
        assert completed["output_count"]==2 and completed["furnace_progress"]==0 and "minecraft:raw_iron" not in completed["furnace_items"],completed
        screen,slots=open_machine(FURNACE,2);assert slots[301]["item"]=="minecraft:iron_ingot" and slots[301]["count"]==2,screen
        call("screenshot",game.work/"remote-output.png");call("click-slot",301,"shift");settle();call("close");settle()
        assert test.counts().get("minecraft:iron_ingot")==2
        endpoint_break=mine_and_collect(WIRES[-1]);place("oritech:energy_pipe",WIRES[-1],cable=True)
        final=state();call("save")
    finally:game.stop()
    try:
        game.start("final-reopen");cmd("tick freeze");assert state()==final
        status=call("status");assert status["server"]["joined"] and status["server"]["decode_errors"]==0,status
        approach(WIRES[2]);test.empty_hand();call("look-at-block",*FURNACE)
        call("screenshot",game.work/"collected-iron.png");call("save")
    finally:game.stop()
    report={"schema":1,"oritech_content_version":game.version,"native_version":"0.6.0" if game.version in ("0.7.0","0.8.0") else "0.5.0","supplied_fixtures":supplied,
            "all_five_cables_waterlogged_by_bucket_use":args.waterlogged_cables,
            "dry_elevated_camera_stand_fixture":args.waterlogged_cables,
            "crafts":test.crafts,"wire_crafted_from_three_electrum":6,"five_wires_placed_by_survival_packets":True,
            "normal_wire_has_no_block_entity":True,"endpoint_is_internal_block_without_item":True,
            "coal_and_raw_iron_inserted_by_menu_packets":True,"machine_energy_progress_or_output_seeded":False,
            "middle_wire_physical_break_pauses_processing":not args.wrench_controls,"wrench_side_cut_pauses_processing":args.wrench_controls,"rejoined_network_resumes_processing":True,
            "internal_endpoint_drops_normal_cable_item":True,"middle_break":middle_break,"endpoint_break":endpoint_break,
            "two_iron_ingots_produced_and_collected":True,"two_physical_reopens_exact":True,"energy_conserved":True,
            "saved":saved,"paused":paused,"completed":completed,"final":final,"protocol_decode_errors":0,
            "licensed_account_dedicated_join_or_multiplayer_tested":False,"full_mod_ported":False,"published":False,
            "screenshots_sha256":{n:hashlib.sha256((game.work/n).read_bytes()).hexdigest() for n in
                ("remote-working.png","broken-cable-paused.png","remote-output.png","collected-iron.png")}}
    (game.work/"checked-result.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Graphical cables crafted, placed, mined/rejoined, powered remote iron and survived two reopens")


if __name__=="__main__":main()

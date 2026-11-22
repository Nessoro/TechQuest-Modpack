#!/usr/bin/env python3
"""Compare loaded native basic cable transfer with original Oritech callbacks.

Blocks and scalar-case energy are fixtures. Original rows tick just the source
interface; native steps tick the whole frozen world, whose far buffers are empty
and whose machine inventories are empty/inactive. Reopen additionally starts
with both endpoint buffers nonempty and checks total energy/capacity, not an
invented match with the original single-interface scheduler.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tomllib

from live_oritech_energy import text
from install_isolated_server import fresh_environment, verify

BASE = (129, 200, 176)
VECTORS = {"down": (0,-1,0), "up": (0,1,0), "north": (0,0,-1),
           "south": (0,0,1), "west": (-1,0,0), "east": (1,0,0)}
coord = lambda pos: " ".join(map(str,pos))
offset = lambda delta: tuple(a+b for a,b in zip(BASE,delta))
point = lambda direction,n: offset(tuple(v*n for v in VECTORS[direction]))


def operations(original):
    ops=[]
    def cmd(line): ops.append({"op":"cmd","cmd":line})
    def step(n): cmd(f"tick step {n}"); ops.append({"op":"tick","n":n+2})
    def mark(label): ops.append({"op":"menu_state","label":label})
    def fixture(direction, target, buffer, target_energy):
        cmd("fill 122 193 169 136 207 183 minecraft:air")
        cmd("setblock "+coord(BASE)+" oritech:basic_generator_block")
        cmd("setblock "+coord(point(direction,6))+" "+target+"{energy:"+str(target_energy)+"}")
        for n in range(1,6):cmd("setblock "+coord(point(direction,n))+" oritech:energy_pipe")
        cmd("data merge block "+coord(point(direction,1))+" {energy:"+str(buffer)+"}")
    def observe(direction):
        cmd("time query gametime")
        for n in (0,1,6,5):cmd("data get block "+coord(point(direction,n))+" energy")
    def check_nodes(nodes):
        for node in nodes:
            # The earlier machine port stores assembly in native NBT and
            # uses simplified models. Only cables port these eight states.
            props=",".join(k+"="+v for k,v in sorted(node["properties"].items())) if "energy_pipe" in node["block"] else ""
            cmd("execute if block "+coord(offset(node["pos"]))+" "+node["block"]+("["+props+"]" if props else ""))
            cmd("data get block "+coord(offset(node["pos"]))+" energy")
    def energy(p,n):cmd("data merge block "+coord(p)+" {energy:"+str(n)+"}")
    cmd("gamemode creative");cmd("difficulty peaceful");cmd("tick freeze")
    cmd("tp @s 128.5 201 178.5");ops.append({"op":"settle"})
    cmd("forceload add 112 160 144 192");ops.append({"op":"tick","n":100})
    cmd("setblock "+coord(BASE)+" oritech:basic_generator_block");step(1)
    for layout in original["layouts"]:
        fixture(layout["direction"],"oritech:powered_furnace_block",0,0)
        mark("layout_"+layout["direction"]);check_nodes(layout["nodes"])
    for row in original["rows"]:
        fixture(row["direction"],row["target_id"],row["initial"]["buffer"],row["initial"]["target"])
        mark(row["name"]);observe(row["direction"]);elapsed=0
        for value in row["states"]:
            step(value["ticks"]-elapsed);observe(row["direction"]);elapsed=value["ticks"]
    fixture("east","oritech:powered_furnace_block",1000,0)
    step(1);mark("before_gap");observe("east")
    cmd("setblock "+coord(point("east",3))+" minecraft:air")
    step(1);mark("broken");observe("east")
    cmd("setblock "+coord(point("east",3))+" oritech:energy_pipe")
    step(1);mark("restored");observe("east")
    energy(point("east",5),333);cmd("setblock "+coord(point("east",6))+" minecraft:air")
    mark("after_removed");check_nodes([original["lifecycle"]["after_target_removed"]])
    cmd("setblock "+coord(point("east",6))+" oritech:foundry_block")
    mark("after_replaced");check_nodes([original["lifecycle"]["after_target_replaced"]])
    step(1);mark("replacement_state");observe("east")
    for supplied in (100,1000):
        fixture("east","oritech:powered_furnace_block",supplied,0)
        cmd("setblock "+coord(offset((6,0,-1)))+" oritech:powered_furnace_block")
        cmd("setblock "+coord(offset((5,0,-1)))+" oritech:energy_pipe")
        step(1);mark("multi_target_"+str(supplied));observe("east")
        cmd("data get block "+coord(offset((6,0,-1)))+" energy")
    fixture("east","oritech:powered_furnace_block",1000,0)
    cmd("setblock "+coord(offset((5,0,-1)))+" oritech:energy_pipe")
    cmd("setblock "+coord(offset((6,0,-1)))+" oritech:energy_pipe")
    step(1);mark("two_faces");observe("east")
    fixture("east","oritech:powered_furnace_block",1000,0)
    cmd("setblock "+coord(offset((2,0,-2)))+" oritech:basic_generator_block")
    cmd("setblock "+coord(offset((2,0,-1)))+" oritech:energy_pipe")
    energy(offset((2,0,-1)),1000);step(1);mark("two_sources");observe("east")
    cmd("data get block "+coord(offset((2,0,-1)))+" energy")
    fixture("east","oritech:powered_furnace_block",1000,0)
    for x in range(1,6):cmd("setblock "+coord(offset((x,0,1)))+" oritech:energy_pipe")
    step(1);mark("loop_first");observe("east")
    cmd("setblock "+coord(point("east",3))+" minecraft:air")
    step(1);mark("loop_alternative");observe("east")
    cmd("setblock "+coord(offset((3,0,1)))+" minecraft:air")
    step(1);mark("loop_both_broken");observe("east")
    fixture("east","oritech:powered_furnace_block",1000,0)
    step(1)
    for n,properties in ((3,"east=0,west=1"),(4,"east=1,west=0")):
        cmd("setblock "+coord(point("east",n))+" oritech:energy_pipe["+properties+"]")
    step(1);mark("disabled_edge");observe("east");check_nodes(original["side_toggle"]["disabled"])
    for n in (3,4):cmd("setblock "+coord(point("east",n))+" oritech:energy_pipe[east=1,west=1,straight=true]")
    step(1);mark("enabled_edge");observe("east");check_nodes(original["side_toggle"]["enabled"])
    fixture("east","oritech:powered_furnace_block",0,0)
    cmd("setblock "+coord(point("east",6))+" minecraft:air")
    controller=offset((6,-1,0))
    cmd("setblock "+coord(controller)+" oritech:powered_furnace_block")
    cmd("setblock "+coord(point("east",6))+" oritech:machine_core_1")
    mark("inactive_core");check_nodes([original["core_delegation"]["before_assembly"]])
    cmd("tp @s 135.5 200 178.5")
    ops.extend([{"op":"use_block","pos":list(controller),"sequence":1},{"op":"tick","n":3},{"op":"close_menu"}])
    mark("active_core");check_nodes([original["core_delegation"]["after_assembly"]])
    energy(point("east",1),1000);step(1);mark("core_energy")
    for p in (controller,point("east",1)):cmd("data get block "+coord(p)+" energy")
    fixture("east","oritech:powered_furnace_block",1000,9536)
    cmd("data merge block "+coord(point("east",5))+" {energy:777}")
    mark("saved");observe("east");check_nodes(original["saved"]["nodes"])
    cmd("save-all flush")
    return ops


def reopened_operations(nodes):
    ops=[{"op":"cmd","cmd":"tick freeze"},{"op":"menu_state","label":"before"}]
    def observe():
        ops.append({"op":"cmd","cmd":"time query gametime"})
        for n in (0,1,6,5):ops.append({"op":"cmd","cmd":"data get block "+coord(point("east",n))+" energy"})
    observe()
    for node in nodes:
        props=",".join(k+"="+v for k,v in sorted(node["properties"].items())) if "energy_pipe" in node["block"] else ""
        ops.append({"op":"cmd","cmd":"execute if block "+coord(offset(node["pos"]))+" "+node["block"]+("["+props+"]" if props else "")})
    for n in (1,2):
        ops.extend([{"op":"cmd","cmd":"tick step 1"},{"op":"tick","n":3},
                    {"op":"menu_state","label":"after_"+str(n)}]);observe()
    return ops


def snapshots(records):
    clocks=[r["results"][-1][1] for r in records if r["cmd"]=="time query gametime"]
    fields=[r for r in records if r["cmd"].startswith("data get block ")][:len(clocks)*4]
    assert len(fields)==len(clocks)*4
    states=[]
    for i in range(0,len(fields),4):
        assert all(r["results"][-1][0] for r in fields[i:i+4]),fields[i:i+4]
        states.append(dict(zip(("source","buffer","target","far_buffer"),(r["results"][-1][1] for r in fields[i:i+4]))))
    return clocks,states


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir","work","original"):parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--resume-initial",action="store_true",help="recheck completed initial output against the exact script/module bytes, then reopen")
    args=parser.parse_args();server=args.server_dir.resolve();work=args.work.absolute();lock=verify(server)
    assert lock["modules"]["oritech"]["version"]=="0.6.0"
    assert work.exists()==args.resume_initial and not work.is_symlink() and not any(p.is_symlink() for p in work.parents)
    assert server not in work.parents and work not in server.parents
    original=json.loads(args.original.read_text());assert len(original["rows"])==504
    if not args.resume_initial:
        work.mkdir(parents=True,mode=0o700)
        shutil.copytree(server/"horizon-mods",work/"horizon-mods");shutil.copy2(server/"horizon-mods.txt",work/"horizon-mods.txt")
        (work/"eula.txt").write_text("eula=true\n")
    else:
        for source in (server/"horizon-mods").rglob("*"):
            if source.is_file():assert source.read_bytes()==(work/"horizon-mods"/source.relative_to(server/"horizon-mods")).read_bytes()
        # Horizon rewrites the enable list in sorted registry order at exit.
        assert sorted((server/"horizon-mods.txt").read_text().splitlines())==sorted((work/"horizon-mods.txt").read_text().splitlines())
        assert (work/"eula.txt").read_text().strip()=="eula=true"
    config=tomllib.loads((server/"server.toml").read_text())
    def run(phase,ops):
        script=work/(phase+"-operations.jsonl");output=work/(phase+"-result.jsonl")
        content="".join(json.dumps(v)+"\n" for v in ops)
        if args.resume_initial and phase=="initial":
            assert script.read_text()==content and output.is_file(),"initial script changed or output missing"
        else:
            script.write_text(content)
            env=fresh_environment(work/("homes-"+phase));env.update(HORIZON_STILL="1",HORIZON_PLAYER_NAME="TQCableParity",HORIZON_COMMAND_SCRIPT=str(script),HORIZON_COMMAND_OUTPUT=str(output))
            with (work/(phase+"-console.log")).open("x") as log:
                subprocess.run([config["engine"]["path"],"--resources",config["engine"]["resources"],"--game-dir",str(work),"--world","techquest-cable-parity","--seed","263","--radius","2"],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
        groups={};current=None
        for line in output.read_text().splitlines():
            row=json.loads(line)
            if row["cmd"].startswith(("setblock ","execute if block ")):assert row["results"][-1][0],row
            if row["cmd"].startswith("data merge "):
                assert row["results"][-1][0] or "Nothing changed. The specified properties already have these values" in text(row),row
            if row["cmd"].startswith("#menu_state "):current=row["cmd"].split()[-1];groups[current]=[]
            elif current:groups[current].append(row)
        return groups
    groups=run("initial",operations(original));checked=0
    for layout in original["layouts"]:
        data=[r for r in groups["layout_"+layout["direction"]] if r["cmd"].startswith("data get block ")][:5]
        for node,actual in zip(layout["nodes"],data):
            assert bool(actual["results"][-1][0])==node["has_energy_api"],(node,actual)
            if node["has_energy_api"]:assert actual["results"][-1][1]==node["energy"]
            else:assert "not a block entity" in text(actual).lower(),actual
    for row in original["rows"]:
        clocks,states=snapshots(groups[row["name"]])
        assert states[0]==row["initial"],(row["name"],states[0],row["initial"])
        assert [t-clocks[0] for t in clocks[1:]]==[v["ticks"] for v in row["states"]]
        for actual,expected in zip(states[1:],row["states"]):
            assert actual==expected["state"],(row["name"],expected["ticks"],actual,expected["state"]);checked+=1
    for label in ("before_gap","broken","restored","replacement_state"):
        _,actual=snapshots(groups[label]);assert actual==[original["lifecycle"][label]],(label,actual)
    for label in ("after_removed","after_replaced"):
        data=[r for r in groups[label] if r["cmd"].startswith("data get block ")][0]
        assert bool(data["results"][-1][0])==(label=="after_replaced"),data
        if label=="after_replaced":assert data["results"][-1][1]==0,data
    for supplied in (100,1000):
        records=groups["multi_target_"+str(supplied)];_,actual=snapshots(records);a=actual[0]
        data=[r for r in records if r["cmd"].startswith("data get block ")][4]
        assert data["results"][-1][0],data
        b=data["results"][-1][1]
        assert a["buffer"]+a["target"]+b==supplied
        assert (a["target"],b) in ((100,0),(0,100)) if supplied==100 else (a["target"],b,a["buffer"])==(256,256,488)
    for label,key in (("two_faces","multiple_faces"),("loop_both_broken","loop")):
        _,actual=snapshots(groups[label]);assert actual==[original[key]["state"]],(label,actual)
    _,actual=snapshots(groups["two_sources"])
    data=[r for r in groups["two_sources"] if r["cmd"].startswith("data get block ")][4]
    assert actual[0]["target"]==512 and actual[0]["buffer"]==744 and data["results"][-1]==[True,744],(actual,data)
    _,disabled=snapshots(groups["disabled_edge"]);_,enabled=snapshots(groups["enabled_edge"])
    assert disabled[0]["target"]==256 and disabled[0]["buffer"]==744,disabled
    assert enabled==[original["side_toggle"]["state"]],enabled
    data=[r for r in groups["core_energy"] if r["cmd"].startswith("data get block ")]
    assert [r["results"][-1][1] for r in data]==[original["core_delegation"]["controller"],original["core_delegation"]["buffer"]],data
    _,saved=snapshots(groups["saved"]);assert saved==[{"source":0,"buffer":1000,"target":9536,"far_buffer":777}],saved
    reopened=run("reopen",reopened_operations(original["saved"]["nodes"]))
    _,before=snapshots(reopened["before"]);assert before==saved
    after=[]
    for key in ("after_1","after_2"):
        _,states=snapshots(reopened[key]);state=states[0];after.append(state)
        assert sum(state.values())==11313 and state["target"]==10000 and state["source"]==0,state
    report={"schema":1,"oritech_content_version":"0.6.0","native_version":"0.5.0","single_target_cases":504,
            "matched_states":checked,"layout_directions":6,"ordinary_wire_has_no_block_entity":True,
            "gap_rejoin_replacement_loop_multiple_targets_faces_sources_matched":True,
            "disabled_side_properties_respected":True,"native_wrench_interaction_tested":False,
            "inactive_core_rejected_and_assembled_core_delegation_matched":True,
            "physical_reopen_before":before,"whole_world_tick_after_reopen":after,
            "reopen_energy_conserved":11313,"same_scheduler_as_single_interface_original":False,
            "scalar_energy_and_blocks_are_fixtures":True,"graphical_or_multiplayer_tested":False,"published":False}
    (work/"checked-result.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Native energy cables matched",checked,"original states, six layouts and physical reopen")


if __name__=="__main__":main()

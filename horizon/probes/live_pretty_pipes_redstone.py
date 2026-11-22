#!/usr/bin/env python3
"""Check native powered extraction against original canWork in all six directions.

Each case has explicit source, module/direction and redstone-block fixtures.
Native processing executes one extraction period; transport cargo is not seeded.
The separate dedicated/GUI probes test destination selection and in-flight work.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

from live_pretty_pipes import verify
from install_isolated_server import fresh_environment

POS=(129,200,176)
DIRECTIONS={'down':(0,-1,0),'up':(0,1,0),'north':(0,0,-1),'south':(0,0,1),'west':(-1,0,0),'east':(1,0,0)}
coord=lambda pos:' '.join(map(str,pos))

def adjacent(direction):return tuple(a+b for a,b in zip(POS,DIRECTIONS[direction]))


def operations(rows):
    ops=[]
    def cmd(line):ops.append({'op':'cmd','cmd':line})
    def step(n):cmd(f'tick step {n}');ops.append({'op':'tick','n':n+2})
    cmd('gamemode creative');cmd('tp @s 128.5 198 178.5');ops.append({'op':'settle'})
    cmd('tick freeze');cmd('fill 125 197 172 133 197 180 minecraft:stone')
    cmd('setblock 128 200 176 minecraft:chest');cmd('setblock '+coord(POS)+' prettypipes:pipe')
    step(1)
    for row in rows:
        cmd('fill 125 198 172 133 202 180 minecraft:air');cmd('kill @e[type=minecraft:item]')
        source_dir=next(d for d in ('west','east','north','south','down','up') if d!=row['direction'])
        output_dir=next(d for d in ('east','north','south','west','down','up') if d not in (row['direction'],source_dir))
        source,output=adjacent(source_dir),adjacent(output_dir)
        cmd('setblock '+coord(source)+' minecraft:chest{Items:[{Slot:0b,id:"minecraft:iron_ingot",count:64}]}')
        cmd('setblock '+coord(output)+' minecraft:chest')
        modules=['{Slot:0b,id:"prettypipes:medium_extraction_module",count:1,components:{"prettypipes:direction_selector_data":{direction:"'+source_dir+'"}}}']
        if row['redstone_module']:modules.append('{Slot:1b,id:"prettypipes:redstone_module",count:1}')
        cmd('setblock '+coord(POS)+' prettypipes:pipe{modules:{Size:3,Items:['+','.join(modules)+']}}')
        cmd('setblock '+coord(adjacent(row['direction']))+(' minecraft:redstone_block' if row['powered'] else ' minecraft:stone'))
        ops.append({'op':'menu_state','label':row['name']})
        cmd('time query gametime');cmd('data get block '+coord(source)+' Items')
        step(15)
        cmd('time query gametime');cmd('data get block '+coord(source)+' Items')
        cmd('data get block '+coord(POS)+' Items[{Slot:3b}].count');cmd('data get block '+coord(output)+' Items')
    return ops


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('server-dir','work','original'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();server=args.server_dir.resolve();work=args.work.absolute();lock=verify(server)
    assert lock['modules']['prettypipes']['version']=='0.8.0'
    assert not work.exists() and not work.is_symlink() and not any(p.is_symlink() for p in work.parents)
    assert server not in work.parents and work not in server.parents
    original=json.loads(args.original.read_text());rows=[]
    for direction in DIRECTIONS:
        for powered in (False,True):
            for redstone in (False,True):
                reference=next(row for row in original['signals'] if row['direction']==direction and row['powered']==powered and len(row['layout'])==(2 if redstone else 1) and 'prettypipes:low_extraction_module' in row['layout'])
                rows.append({'name':'case_'+str(len(rows)),'direction':direction,'powered':powered,'redstone_module':redstone,'can_work':reference['can_work']})
    assert len(rows)==24
    work.mkdir(parents=True,mode=0o700);shutil.copytree(server/'horizon-mods',work/'horizon-mods');shutil.copy2(server/'horizon-mods.txt',work/'horizon-mods.txt');(work/'eula.txt').write_text('eula=true\n')
    script=work/'operations.jsonl';script.write_text(''.join(json.dumps(op)+'\n' for op in operations(rows)))
    config=tomllib.loads((server/'server.toml').read_text());env=fresh_environment(work/'homes')
    env.update(HORIZON_STILL='1',HORIZON_PLAYER_NAME='TQRedstone',HORIZON_COMMAND_SCRIPT=str(script),HORIZON_COMMAND_OUTPUT=str(work/'result.jsonl'))
    with (work/'console.log').open('x') as log:
        subprocess.run([config['engine']['path'],'--resources',config['engine']['resources'],'--game-dir',str(work),'--world','techquest-redstone-parity','--seed','263','--radius','2'],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    records=[json.loads(line) for line in (work/'result.jsonl').read_text().splitlines()];grouped={};current=None
    for row in records:
        if row['cmd'].startswith(('setblock ','data merge ')):assert row['results'][-1][0],row
        if row['cmd'].startswith('#menu_state case_'):current=row['cmd'].split()[-1];grouped[current]=[]
        elif current:grouped[current].append(row)
    def text(row):return ''.join(span[0] for msg in row['messages'] for span in msg)
    checks=[]
    for expected in rows:
        data=grouped[expected['name']];clocks=[row['results'][-1][1] for row in data if row['cmd']=='time query gametime']
        assert clocks[1]-clocks[0]==15,(expected,clocks)
        inventories=[row for row in data if row['cmd'].endswith(' Items')]
        def count(row):
            value=text(row)
            assert row['results'][-1][0] or 'Found no elements matching Items' in value,value
            return sum(map(int,re.findall(r'\bcount:\s*(\d+)',value)))
        before,after,target=map(count,inventories)
        queued=next(row for row in data if row['cmd'].endswith('Items[{Slot:3b}].count'))['results'][-1][1]
        wanted=8 if expected['can_work'] else 0
        assert before==64 and before-after==queued==wanted and target==0,(expected,before,after,queued,target)
        checks.append({**expected,'extracted':before-after,'queued':queued,'destination_before_arrival':target})
    report={'schema':1,'content_and_native_version':'0.8.0','original_can_work_cases_matched':len(checks),'checks':checks,
            'actual_extraction_ticks_executed':True,'all_six_power_directions_checked':True,'signal_strengths':[0,15],
            'medium_tier_amount_used_to_observe_original_tier_independent_gate':True,
            'source_module_direction_and_power_fixtures_injected':True,'transport_cargo_seeded':False,'licensed_join_tested':False,'published':False}
    (work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n');print('Native redstone extraction matched all 24 original canWork cases')


if __name__=='__main__':main()

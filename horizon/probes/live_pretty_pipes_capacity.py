#!/usr/bin/env python3
"""Compare actual Horizon extraction ticks with the original capacity oracle.

Uses the stock integrated-server command harness, a fresh local synthetic owner
and injected long-lived queue entries. No GUI, account login or dedicated join.
The isolated public-method reference tests capacity, not complete RNG/timing.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from install_isolated_server import fresh_environment,verify


def operations(rows):
    ops=[]
    def cmd(line):ops.append({'op':'cmd','cmd':line})
    def item(ident,count,slot,marker=0):
        extra=',components:{"minecraft:custom_data":{tq_marker:48}}' if marker else ''
        return f'{{Slot:{slot}b,id:"{ident}",count:{count}{extra}}}'
    cmd('gamemode creative');cmd('tp @s 128.5 200 178.5');ops.append({'op':'settle'})
    cmd('clear @s');cmd('tick freeze');cmd('fill 124 199 172 136 199 180 minecraft:stone')
    cmd('setblock 128 200 176 minecraft:chest');cmd('setblock 129 200 176 prettypipes:pipe')
    ops.append({'op':'use_block','pos':[129,200,176],'sequence':1})
    ops.append({'op':'tick','n':2});ops.append({'op':'menu_state','label':'capacity_bootstrap'})
    ops.append({'op':'close_menu'});ops.append({'op':'tick','n':2})
    for row in rows:
        cmd('fill 128 200 176 132 200 176 minecraft:air')
        cmd('kill @e[type=minecraft:item]')
        cmd('setblock 128 200 176 minecraft:chest{Items:['+item(row['input_item'],64,0,row['input_marker'])+']}')
        size={'minecraft:chest':27,'minecraft:hopper':5,'minecraft:furnace':3}[row['block']]
        filled=[]
        for slot in range(size):
            ident,count,marker=('minecraft:cobblestone',64,0)
            if slot==row['slot']:ident,count,marker=row['existing_item'],row['existing_count'],row['destination_marker']
            if count:filled.append(item(ident,count,slot,marker))
        cmd('setblock 132 200 176 '+row['block']+'{Items:['+','.join(filled)+']}')
        for x in (129,130,131):cmd(f'setblock {x} 200 176 prettypipes:pipe')
        cmd('data merge block 129 200 176 {modules:{Size:3,Items:['+item('prettypipes:'+row['tier']+'_extraction_module',1,0)+']}}')
        if row['reserved']:
            cmd('data merge block 130 200 176 {Items:['+item(row['reserved_item'],row['reserved'],3)+'],techquest_pending_3:{destination:[I;132,200,176],remaining:10000}}')
        ops.append({'op':'menu_state','label':row['name']})
        cmd('data get block 128 200 176 Items')
        cmd('data get block 132 200 176 Items')
        cmd('time query gametime')
        period={'low':20,'medium':15,'high':10}[row['tier']]
        cmd(f'tick step {period}')
        ops.append({'op':'tick','n':period+2})
        cmd('time query gametime')
        cmd('data get block 128 200 176 Items')
        cmd('data get block 129 200 176 Items[{Slot:3b}].count')
        cmd('data get block 132 200 176 Items')
    cmd('fill 128 200 176 132 200 176 minecraft:air');cmd('kill @e[type=minecraft:item]')
    return ops


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('server-dir','work','original'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args();server=args.server_dir.resolve();work=args.work.absolute();lock=verify(server)
    if lock['modules'].get('prettypipes',{}).get('version') not in (('0.4.0',) if args.baseline else ('0.5.0','0.6.0','0.7.0','0.8.0')):raise ValueError('requires the selected reviewed capacity installation')
    if work.exists() or work.is_symlink() or any(p.is_symlink() for p in work.parents) or server in work.parents or work in server.parents:raise ValueError('work must be new and separate')
    original=json.loads(args.original.read_text());rows=original['rows']
    assert original['original_destination_capacity_executed'] and len(rows)==126
    work.mkdir(mode=0o700,parents=True);shutil.copytree(server/'horizon-mods',work/'horizon-mods');shutil.copy2(server/'horizon-mods.txt',work/'horizon-mods.txt')
    (work/'eula.txt').write_text('eula=true\n');script=work/'operations.jsonl';script.write_text(''.join(json.dumps(op)+'\n' for op in operations(rows)))
    config=tomllib.loads((server/'server.toml').read_text());env=fresh_environment(work/'homes')
    env.update(HORIZON_PLAYER_NAME='TQCapacity',HORIZON_COMMAND_SCRIPT=str(script),HORIZON_COMMAND_OUTPUT=str(work/'result.jsonl'))
    with (work/'console.log').open('x') as log:
        (work/'console.log').chmod(0o600)
        subprocess.run([config['engine']['path'],'--resources',config['engine']['resources'],'--game-dir',str(work),
                        '--world','techquest-capacity','--seed','263','--radius','2'],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    output=[json.loads(line) for line in (work/'result.jsonl').read_text().splitlines()]
    grouped={};current=None
    for record in output:
        if record['cmd'].startswith('#menu_state case_'):current=record['cmd'].split()[-1];grouped[current]=[]
        elif current:grouped[current].append(record)
    def text(row):return ''.join(span[0] for message in row['messages'] for span in message)
    checked=[];mismatches=[]
    for expected in rows:
        records=grouped[expected['name']]
        snapshots=[r for r in records if r['cmd']=='data get block 128 200 176 Items']
        assert len(snapshots)==2
        targets=[r for r in records if r['cmd']=='data get block 132 200 176 Items']
        assert len(targets)==2 and text(targets[0])==text(targets[1]),(expected,'destination changed before arrival')
        values=[]
        for snapshot in snapshots:
            value=text(snapshot);assert 'has the following block data:' in value,value
            values.append(sum(map(int,re.findall(r'\bcount:\s*(\d+)',value))))
        assert values[0]==64,(expected,values)
        accepted=values[0]-values[1]
        clocks=[r['results'][-1][1] for r in records if r['cmd']=='time query gametime']
        period={'low':20,'medium':15,'high':10}[expected['tier']]
        assert len(clocks)==2 and clocks[1]-clocks[0]==period,(expected,clocks)
        queue=next(r for r in records if r['cmd']=='data get block 129 200 176 Items[{Slot:3b}].count')['results'][-1][1]
        assert queue==accepted,(expected,accepted,queue)
        if accepted!=expected['accepted']:mismatches.append({'name':expected['name'],'expected':expected['accepted'],'actual':accepted})
        checked.append({'name':expected['name'],'tier':expected['tier'],'accepted':accepted,'queued':queue})
    report={'schema':1,'minecraft':'26.3','prototype_version':lock['modules']['prettypipes']['version'],'cases_match_original':len(checked)-len(mismatches),'mismatches':mismatches,
            'actual_game_extraction_ticks_executed':True,'synthetic_local_owner':True,'queue_fixtures_injected':True,
            'source_delta_equals_new_queue':True,'destination_unchanged_before_arrival':True,'one_extraction_period_per_case':True,'containers':['chest','hopper','furnace'],
            'real_graphical_or_dedicated_join_tested':False,'full_mod_ported':False,'published':False,'cases':checked}
    assert (bool(mismatches) if args.baseline else not mismatches),mismatches[:3]
    (work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('baseline capacity mismatches:',len(mismatches)) if args.baseline else print('native extraction ticks matched all',len(checked),'original capacity cases')


if __name__=='__main__':main()

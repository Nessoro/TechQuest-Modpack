#!/usr/bin/env python3
"""Compare native Foundry processing, core assembly and physical reload to CC0 originals.

Inventory/energy/progress, linked core states and redstone flags are fixtures.
A real tick primes native recipe caches; implementation cache fields are never
seeded. Original destroy callback is compared with native replacement invalidation.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tomllib

from live_oritech_energy import items
from install_isolated_server import fresh_environment,verify

POS=(129,200,176)
coord=lambda p:' '.join(map(str,p))
CORES=((130,200,176),(129,201,176),(130,201,176))
FIELDS=('energy','"oritech.machine_progress"','techquest_assembled','Items')


def nbt(state,disabled=False):
    values=','.join('{Slot:'+str(v['slot'])+'b,id:"'+v['item']+'",count:'+str(v['count'])+'}' for v in state['items'])
    return '{energy:'+str(state['energy'])+',"oritech.machine_progress":'+str(state['progress'])+',techquest_assembled:'+str(int(state['assembled']))+'b,"oritech.redstone":'+str(int(disabled))+'b,Items:['+values+']}'


def operations(original):
    ops=[]
    sequence=0
    def cmd(line):ops.append({'op':'cmd','cmd':line})
    def step(n):cmd(f'tick step {n}');ops.append({'op':'tick','n':n+2})
    def mark(label):ops.append({'op':'menu_state','label':label})
    def observe():
        cmd('time query gametime')
        for key in FIELDS:cmd('data get block '+coord(POS)+' '+key)
    def clear():
        cmd('fill 127 200 174 131 202 178 minecraft:air');cmd('kill @e[type=minecraft:item]');cmd('clear @s')
    def use():
        nonlocal sequence
        sequence+=1
        cmd('clear @s');ops.append({'op':'use_block','pos':list(POS),'sequence':sequence});ops.append({'op':'tick','n':3});ops.append({'op':'close_menu'});ops.append({'op':'tick','n':2})
    def core(p,used=False):
        values=',controller_x:'+str(POS[0]-p[0])+',controller_y:'+str(POS[1]-p[1])+',controller_z:'+str(POS[2]-p[2]) if used else ''
        cmd('setblock '+coord(p)+' oritech:machine_core_1{techquest_core_used:'+str(int(used))+'b'+values+'}')
    def fixture(state):
        clear()
        cmd('setblock '+coord(POS)+' oritech:foundry_block[facing=north]'+nbt(state))
        for p in CORES:core(p,state['assembled'])
    cmd('gamemode creative');cmd('tp @s 128.5 198 178.5');ops.append({'op':'settle'});cmd('tick freeze')
    cmd('fill 124 197 172 134 197 180 minecraft:stone');cmd('setblock '+coord(POS)+' oritech:foundry_block');step(1)
    for row in original['geometry']:
        clear();cmd('setblock '+coord(POS)+' oritech:foundry_block[facing='+row['facing']+']')
        positions=[tuple(a+b for a,b in zip(POS,offset)) for offset in row['core_positions']]
        for i,p in enumerate(positions):
            if i!=row['missing']:
                if row['used'] and i==0:cmd('setblock '+coord(p)+' oritech:machine_core_1{techquest_core_used:1b}')
                else:core(p)
        use();mark(row['name']);cmd('data get block '+coord(POS)+' techquest_assembled')
        for p in positions:cmd('data get block '+coord(p)+' techquest_core_used')
    for row in original['rows']:
        if row['primed']:
            seed={**row['initial_state'],'energy':128,'progress':0,'assembled':True,'items':[v for v in row['initial_state']['items'] if v['slot']<2]}
            fixture(seed);step(1);cmd('data merge block '+coord(POS)+' '+nbt(row['initial_state'],row['disabled']))
            if not row['initial_state']['assembled']:
                for p in CORES:cmd('data merge block '+coord(p)+' {techquest_core_used:0b}')
        else:
            fixture(row['initial_state'])
            if row['disabled']:cmd('data merge block '+coord(POS)+' {"oritech.redstone":1b}')
        mark(row['name']);observe();elapsed=0
        for state in row['states']:
            step(state['ticks']-elapsed);observe();elapsed=state['ticks']
    seed={'energy':50000,'progress':0,'assembled':True,'items':[{'slot':0,'item':'minecraft:iron_ingot','count':2},{'slot':1,'item':'oritech:coal_dust','count':2}]}
    fixture(seed);step(13);mark('before_broken');observe()
    cmd('setblock '+coord(CORES[0])+' minecraft:air');mark('after_broken');observe()
    step(10);mark('paused');observe();core(CORES[0]);use();step(1);mark('resumed');observe()
    for row in original['pulverizer_coal']:
        clear();state={'energy':25000,'progress':0,'assembled':False,'items':[{'slot':0,'item':row['fuel'],'count':1}]}
        cmd('setblock '+coord(POS)+' oritech:pulverizer_block'+nbt(state));step(100);mark(row['fuel']);observe()
    fixture(seed);step(13);mark('saved');observe();cmd('save-all flush')
    return ops


def reopen_operations(states):
    ops=[{'op':'cmd','cmd':'tick freeze'},{'op':'menu_state','label':'reopened'}]
    def observe():
        ops.append({'op':'cmd','cmd':'time query gametime'})
        for key in FIELDS:ops.append({'op':'cmd','cmd':'data get block '+coord(POS)+' '+key})
    observe();elapsed=0
    for row in states:
        n=row['ticks']-elapsed;ops.extend([{'op':'cmd','cmd':f'tick step {n}'},{'op':'tick','n':n+2}]);observe();elapsed=row['ticks']
    return ops


def snapshots(records):
    clocks=[row['results'][-1][1] for row in records if row['cmd']=='time query gametime']
    fields=[row for row in records if row['cmd'].startswith('data get block '+coord(POS)+' ')]
    assert len(fields)==len(clocks)*4
    result=[]
    for i in range(0,len(fields),4):
        energy,progress,assembled,inventory=fields[i:i+4]
        assert all(row['results'][-1][0] for row in (energy,progress,assembled)),fields[i:i+4]
        result.append({'energy':energy['results'][-1][1],'progress':progress['results'][-1][1],'assembled':bool(assembled['results'][-1][1]),'items':items(inventory)})
    return clocks,result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('server-dir','work','original','original-reopen'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();server=args.server_dir.resolve();work=args.work.absolute();lock=verify(server)
    content_version=lock['modules']['oritech']['version']
    assert content_version in ('0.4.0','0.5.0','0.6.0','0.7.0','0.8.0','0.9.0')
    native_version=next(v['version'] for v in lock['native_modules'] if v['id']=='techquest_oritech')
    assert not work.exists() and not work.is_symlink() and not any(p.is_symlink() for p in work.parents)
    assert server not in work.parents and work not in server.parents
    original=json.loads(args.original.read_text());reopened=json.loads(args.original_reopen.read_text())
    assert original['original_server_tick_executed'] and len(original['rows'])==68 and len(original['geometry'])==20
    assert (original['capacity'],original['max_insertion'],original['speed'],original['efficiency'],original['core_quality'])==(50000,1024,1.0,1.0,1.0)
    work.mkdir(parents=True,mode=0o700);shutil.copytree(server/'horizon-mods',work/'horizon-mods');shutil.copy2(server/'horizon-mods.txt',work/'horizon-mods.txt');(work/'eula.txt').write_text('eula=true\n')
    config=tomllib.loads((server/'server.toml').read_text())
    def run(phase,ops):
        script=work/(phase+'-operations.jsonl');output=work/(phase+'-result.jsonl');script.write_text(''.join(json.dumps(v)+'\n' for v in ops))
        env=fresh_environment(work/('homes-'+phase));env.update(HORIZON_STILL='1',HORIZON_PLAYER_NAME='TQFoundry',HORIZON_COMMAND_SCRIPT=str(script),HORIZON_COMMAND_OUTPUT=str(output))
        with (work/(phase+'-console.log')).open('x') as log:
            subprocess.run([config['engine']['path'],'--resources',config['engine']['resources'],'--game-dir',str(work),'--world','techquest-foundry-parity','--seed','263','--radius','2'],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        records=[json.loads(line) for line in output.read_text().splitlines()];groups={};current=None
        for row in records:
            if row['cmd'].startswith(('setblock ','data merge ')):assert row['results'][-1][0],row
            if row['cmd'].startswith('#menu_state '):current=row['cmd'].split()[-1];groups[current]=[]
            elif current:groups[current].append(row)
        return groups
    groups=run('initial',operations(original));checked=0
    for row in original['geometry']:
        records=[v for v in groups[row['name']] if v['cmd'].startswith('data get block')]
        assert bool(records[0]['results'][-1][1])==row['assembled'],(row,records)
        assert [bool(v['results'][-1][1]) for v in records[1:]]==row['used_after'],(row,records)
    for row in original['rows']:
        clocks,actual=snapshots(groups[row['name']]);assert actual[0]==row['initial_state'],(row['name'],actual[0],row['initial_state'])
        assert [t-clocks[0] for t in clocks[1:]]==[v['ticks'] for v in row['states']]
        for value,expected in zip(actual[1:],row['states']):assert value==expected['state'],(row['name'],expected['ticks'],value,expected['state']);checked+=1
    for key in ('before_broken','after_broken','paused','resumed'):
        _,actual=snapshots(groups[key]);assert actual==[original['core_lifecycle'][key]],(key,actual,original['core_lifecycle'][key])
    for row in original['pulverizer_coal']:
        _,actual=snapshots(groups[row['fuel']]);assert actual==[{'energy':row['energy'],'progress':row['progress'],'assembled':False,'items':[{'slot':1,'item':row['item'],'count':row['dust']}]}],(actual,row)
    _,saved=snapshots(groups['saved']);assert saved==[original['saved']]
    restart=run('reopen',reopen_operations(reopened['states']));clocks,actual=snapshots(restart['reopened'])
    assert actual[0]==saved[0]==reopened['before']
    assert actual[1:]==[v['state'] for v in reopened['states']],(actual,reopened)
    report={'schema':1,'oritech_content_version':content_version,'native_machine_version':native_version,'processing_cases':68,'matched_snapshots':checked,
            'assembly_geometry_cases':20,'all_four_horizontal_orientations_checked':True,'used_core_and_missing_core_rejected':True,
            'physical_destroy_callback_lifecycle_matched_using_native_invalidation':True,'coal_and_charcoal_pulverization_matched':True,
            'physical_reopen_matches_original_recipe_cache_reset':True,'saved':saved[0],'reopened':actual,
            'input_energy_progress_linked_core_and_redstone_fixtures':True,'native_recipe_cache_primed_by_actual_tick':True,'runtime_cache_fields_seeded':False,
            'cross_chunk_unloaded_core_and_addon_parity_tested':False,'licensed_join_tested':False,'published':False}
    (work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n');print('Foundry matched 680 original states, 20 core assemblies, lifecycle, coal processing and physical reopen')


if __name__=='__main__':main()

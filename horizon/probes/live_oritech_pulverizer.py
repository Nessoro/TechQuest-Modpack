#!/usr/bin/env python3
"""Compare actual native processing ticks with the original Pulverizer oracle.

Inventory, output, energy, progress and redstone fixtures are explicit. A real
prewarm tick primes the native recipe cache; no cache implementation fields are
injected. A second process checks original save/reopen recipe-reset behavior.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tomllib

from live_oritech_energy import items, text
from install_isolated_server import fresh_environment, verify

POS = "129 200 176"
FIELDS = ("energy", '"oritech.machine_progress"', "Items")


def nbt(state, disabled=False):
    stacks = ','.join('{Slot:' + str(item['slot']) + 'b,id:"' + item['item'] + '",count:' + str(item['count']) + '}' for item in state['items'])
    return '{energy:' + str(state['energy']) + ',"oritech.machine_progress":' + str(state['progress']) + ',"oritech.redstone":' + str(int(disabled)) + 'b,Items:[' + stacks + ']}'


def operations(rows):
    ops = []
    def cmd(line): ops.append({"op": "cmd", "cmd": line})
    def step(ticks):
        cmd(f"tick step {ticks}")
        ops.append({"op": "tick", "n": ticks+2})
    def observe():
        cmd("time query gametime")
        for field in FIELDS: cmd(f"data get block {POS} {field}")
    cmd("tick freeze")
    cmd("gamemode creative")
    cmd("tp @s 128.5 200 178.5")
    ops.append({"op": "settle"})
    cmd("fill 124 199 172 136 199 180 minecraft:stone")
    cmd(f"setblock {POS} oritech:pulverizer_block")
    step(1)
    for row in rows:
        cmd(f"setblock {POS} minecraft:air")
        cmd("kill @e[type=minecraft:item]")
        if row['recipe_primed']:
            # The original oracle primes via its own getRecipe/setCurrentRecipe.
            # The native port primes by actually processing one quartz tick.
            seed = {"energy":32,"progress":0,"items":[{"slot":0,"item":"minecraft:quartz","count":2}]}
            cmd(f"setblock {POS} oritech:pulverizer_block" + nbt(seed))
            step(1)
            cmd(f"data merge block {POS} " + nbt(row['initial_state'], row['disabled']))
        else:
            cmd(f"setblock {POS} oritech:pulverizer_block" + nbt(row['initial_state'], row['disabled']))
        ops.append({"op":"menu_state","label":row['name']})
        observe()
        elapsed = 0
        for state in row['states']:
            step(state['ticks']-elapsed)
            observe()
            elapsed = state['ticks']
    cmd(f"setblock {POS} minecraft:air")
    seed={"energy":25000,"progress":0,"items":[{"slot":0,"item":"minecraft:quartz","count":2}]}
    cmd(f"setblock {POS} oritech:pulverizer_block" + nbt(seed))
    step(45)
    ops.append({"op":"menu_state","label":"saved"})
    observe()
    cmd("save-all flush")
    return ops


def reopen_operations(states):
    ops=[{"op":"cmd","cmd":"tick freeze"},{"op":"menu_state","label":"reopened"}]
    def observe():
        ops.append({"op":"cmd","cmd":"time query gametime"})
        for field in FIELDS:ops.append({"op":"cmd","cmd":f"data get block {POS} {field}"})
    observe()
    elapsed=0
    for state in states:
        delta=state['ticks']-elapsed
        ops.extend([{"op":"cmd","cmd":f"tick step {delta}"},{"op":"tick","n":delta+2}])
        observe()
        elapsed=state['ticks']
    return ops


def snapshots(records):
    clocks=[row['results'][-1][1] for row in records if row['cmd']=='time query gametime']
    data=[row for row in records if row['cmd'].startswith(f'data get block {POS} ')]
    assert len(data)==len(clocks)*3
    states=[]
    for offset in range(0,len(data),3):
        energy,progress,inventory=data[offset:offset+3]
        assert energy['results'][-1][0] and progress['results'][-1][0]
        states.append({'energy':energy['results'][-1][1],'progress':progress['results'][-1][1],'items':items(inventory)})
    return clocks,states


def comparable(state):
    return {key:state[key] for key in ('energy','progress','items')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('server-dir','work','original','original-reopen'):
        parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();server=args.server_dir.resolve();work=args.work.absolute();lock=verify(server)
    assert lock['modules']['oritech']['version']=='0.3.0'
    assert not work.exists() and not work.is_symlink() and not any(p.is_symlink() for p in work.parents)
    assert server not in work.parents and work not in server.parents
    original=json.loads(args.original.read_text());reopened=json.loads(args.original_reopen.read_text());rows=original['rows']
    assert original['original_server_tick_executed'] and len(rows)==67
    assert original['configured_capacity']==25000 and original['configured_energy_per_tick']==32 and original['configured_max_insertion']==256
    assert all(state['state']['burst_ticks']==0 for row in rows for state in row['states'])
    work.mkdir(parents=True,mode=0o700);shutil.copytree(server/'horizon-mods',work/'horizon-mods');shutil.copy2(server/'horizon-mods.txt',work/'horizon-mods.txt')
    (work/'eula.txt').write_text('eula=true\n')
    config=tomllib.loads((server/'server.toml').read_text())
    def run(phase,ops):
        script=work/(phase+'-operations.jsonl');script.write_text(''.join(json.dumps(op)+'\n' for op in ops))
        output=work/(phase+'-result.jsonl');env=fresh_environment(work/('homes-'+phase))
        env.update(HORIZON_STILL='1',HORIZON_PLAYER_NAME='TQPulvProbe',HORIZON_COMMAND_SCRIPT=str(script),HORIZON_COMMAND_OUTPUT=str(output))
        with (work/(phase+'-console.log')).open('x') as log:
            subprocess.run([config['engine']['path'],'--resources',config['engine']['resources'],'--game-dir',str(work),'--world','techquest-pulverizer-parity','--seed','263','--radius','2'],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        records=[json.loads(line) for line in output.read_text().splitlines()]
        for row in records:
            if row['cmd'].startswith(('setblock ', 'data merge ')):
                assert row['results'][-1][0], row
        grouped={};current=None
        for row in records:
            if row['cmd'].startswith('#menu_state '):
                current=row['cmd'].split()[-1];grouped[current]=[]
            elif current:grouped[current].append(row)
        return grouped
    grouped=run('initial',operations(rows));mismatches=[];checked=0
    for row in rows:
        clocks,actual=snapshots(grouped[row['name']])
        assert actual[0]==comparable(row['initial_state']),(row['name'],actual[0],row['initial_state'])
        assert [clock-clocks[0] for clock in clocks[1:]]==[state['ticks'] for state in row['states']]
        for native,expected in zip(actual[1:],row['states']):
            checked+=1
            if native!=comparable(expected['state']):mismatches.append({'case':row['name'],'tick':expected['ticks'],'expected':comparable(expected['state']),'actual':native})
    _,saved=snapshots(grouped['saved']);assert saved==[comparable(original['saved'])],(saved,original['saved'])
    assert not mismatches,mismatches[:4]
    restart=run('reopen',reopen_operations(reopened['states']))
    clocks,states=snapshots(restart['reopened'])
    assert states[0]==saved[0]==comparable(reopened['before'])
    assert [clock-clocks[0] for clock in clocks[1:]]==[state['ticks'] for state in reopened['states']]
    assert states[1:]==[comparable(state['state']) for state in reopened['states']],(states,reopened['states'])
    report={'schema':1,'oritech_content_version':'0.3.0','native_machine_version':'0.2.0','cases':len(rows),'snapshots':checked,'mismatches':mismatches,'actual_processing_ticks_executed':True,
            'original_saved_state':comparable(original['saved']),'native_saved_state':saved[0],'physical_reopen_matches_original':True,'reopen_states':states,
            'original_transient_recipe_reset_after_load_matched':True,'recipe_cache_primed_by_actual_tick':True,'no_runtime_cache_fields_injected':True,
            'inventory_energy_progress_redstone_and_output_fixtures_injected':True,'addons_tested':False,'source_original_burst_without_addons_zero':True,
            'full_pulverizer_recipe_set_ported':False,'licensed_join_tested':False,'published':False}
    (work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Native Pulverizer matched',checked,'original states in',len(rows),'cases and physical reopen')


if __name__=='__main__':main()

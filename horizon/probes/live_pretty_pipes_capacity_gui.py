#!/usr/bin/env python3
"""Check real competing/own in-flight reservations and save/reopen in local GUI.

No injected queue entries: modules are installed by hand and extract real stacks.
Fresh synthetic world/owner only; no licensed login or dedicated-server join.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from graphical_fixture import GraphicalFixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('server-dir','work'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();game=GraphicalFixture(args.server_dir,args.work,'0.5.0','techquest-capacity-gui','TQCapacityGui')
    call,cmd,settle=game.call,game.command,game.settle
    def count(pos):
        text=cmd('data get block '+' '.join(map(str,pos))+' Items')
        assert 'has the following block data:' in text,text
        return sum(int(m[1]) for m in re.finditer(r'\{(?=[^{}]*\bcount:\s*(\d+))(?=[^{}]*\bid:\s*"minecraft:iron_ingot")[^{}]*\}',text))
    def target(iron):
        items=[f'{{Slot:{i}b,id:"minecraft:cobblestone",count:64}}' for i in range(1,27)]
        items.insert(0,f'{{Slot:0b,id:"minecraft:iron_ingot",count:{iron}}}')
        cmd('data merge block 3 200 1 {Items:['+','.join(items)+']}')
    def install(pos,tier):
        cmd(f'give @s prettypipes:{tier}_extraction_module 1')
        call('select',f'prettypipes:{tier}_extraction_module');settle()
        call('interact',*pos);settle()
        assert 'prettypipes:'+tier+'_extraction_module' in cmd('data get block '+' '.join(map(str,pos))+' modules')
    def step(n):cmd(f'tick step {n}');call('wait',n+8)
    try:
        game.start('prepare')
        cmd('fill -3 199 -3 6 199 6 minecraft:stone')
        for pos in [(-1,200,0),(-1,200,2),(3,200,1)]:cmd('setblock '+' '.join(map(str,pos))+' minecraft:chest')
        for pos in [(0,200,0),(0,200,2),(1,200,0),(1,200,1),(1,200,2),(2,200,1)]:cmd('setblock '+' '.join(map(str,pos))+' prettypipes:pipe')
        cmd('tp @s 0.5 200 2.5');call('wait-ready',timeout=180);cmd('clear @s');cmd('tick freeze')
        install((0,200,0),'high')
        cmd('tp @s 0.5 200 4.5');call('wait-ready',timeout=180);install((0,200,2),'high')
        for z in (0,2):cmd(f'item replace block -1 200 {z} container.0 with minecraft:iron_ingot 64')
        target(61);step(20)
        sources=count((-1,200,0))+count((-1,200,2));destination=count((3,200,1))
        assert sources==125 and destination==61,(sources,destination)
        call('screenshot',game.work/'competing-inflight.png');call('save')
        print('two real high extractors reserved exactly three free spaces',flush=True)
    finally:game.stop()
    try:
        game.start('reopen-competing');cmd('tick freeze')
        assert count((-1,200,0))+count((-1,200,2))==125
        assert count((3,200,1)) in (61,64)
        cmd('tick unfreeze');call('wait',220);cmd('tick freeze')
        assert count((3,200,1))==64 and count((-1,200,0))+count((-1,200,2))==125
        # A medium module must count its own earlier batch while ticking out
        # of the world's block-entity map, before its delivery can arrive.
        cmd('setblock 0 200 0 minecraft:air');cmd('setblock 0 200 2 minecraft:air')
        cmd('setblock 0 200 0 prettypipes:pipe')
        cmd('tp @s 0.5 200 2.5');call('wait-ready',timeout=180);install((0,200,0),'medium')
        cmd('item replace block -1 200 0 container.0 with minecraft:iron_ingot 64')
        target(54);step(45)
        assert count((-1,200,0))==54 and count((3,200,1))==54
        call('screenshot',game.work/'own-reservation.png');call('save')
        print('medium extractor reserved 8 + 2 items and stopped before oversending',flush=True)
    finally:game.stop()
    try:
        game.start('reopen-own');cmd('tick freeze')
        assert count((-1,200,0))==54 and 54<=count((3,200,1))<=64
        cmd('tick unfreeze');call('wait',220);cmd('tick freeze')
        assert count((-1,200,0))==54 and count((3,200,1))==64
        status=call('status');assert status['server']['joined'] and status['server']['decode_errors']==0
        call('screenshot',game.work/'delivered.png');call('save')
    finally:game.stop()
    report={'schema':1,'minecraft':'26.3','prototype_version':'0.5.0','connected_local_graphical_client':True,
            'modules_installed_by_hand':True,'competing_extractors_respect_three_free_spaces':True,
            'own_inflight_reservations_counted':True,'medium_batches_8_then_2_then_zero':True,
            'both_real_inflight_worlds_saved_reopened_delivered':True,'source_target_totals_conserved':True,
            'synthetic_queue_entries_injected':False,'protocol_decode_errors':0,'device_type':status['renderer']['device_type'],
            'licensed_account_or_dedicated_join_tested':False,'published':False,
            'screenshots_sha256':{n:hashlib.sha256((game.work/n).read_bytes()).hexdigest() for n in ('competing-inflight.png','own-reservation.png','delivered.png')}}
    (game.work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n');print('real graphical capacity reservations passed')


if __name__=='__main__':main()

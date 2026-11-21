#!/usr/bin/env python3
"""Render/edit the first and last ghost samples of each extraction tier."""
import argparse
import hashlib
import json
from pathlib import Path
from graphical_fixture import GraphicalFixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args()
    game=GraphicalFixture(args.server_dir,args.work,('0.4.0','0.5.0','0.6.0'),'techquest-filter-layout','TQFilterLayout')
    call,cmd,settle=game.call,game.command,game.settle
    checked=[]
    try:
        game.start('layout')
        cmd('fill -3 199 -3 5 199 5 minecraft:stone')
        for x in (0,2):cmd(f'setblock {x} 200 0 minecraft:chest')
        cmd('setblock 1 200 0 prettypipes:pipe')
        cmd('tp @s 0.5 200 3.5');call('wait-ready',timeout=180)
        cmd('clear @s');cmd('tick freeze')
        cmd('give @s minecraft:iron_ingot 64');cmd('give @s minecraft:gold_ingot 8')
        for tier,n in [('low',3),('medium',6),('high',9)]:
            ident=f'prettypipes:{tier}_extraction_module'
            cmd(f'give @s {ident} 1');call('select',ident);settle()
            call('interact',1,200,0);settle();call('interact',1,200,0);settle()
            screen=call('screen');assert screen['screen']=='container'
            assert {s['slot'] for s in screen['slots'] if 300<=s['slot']<500}=={300,301,302}
            status=call('status');w,h=status['renderer']['size'];ox,oy=(w//2-176)//2,(h//2-203)//2
            def sample(i):
                x=(176-n*18)//2+1+i*18+8
                call('click-at',ox+x,oy+86);settle()
            for i,inventory_slot in [(0,0),(n-1,1)]:
                call('click-slot',inventory_slot);settle();sample(i);call('click-slot',inventory_slot);settle()
            text=cmd('data get block 1 200 0 modules')
            assert f'size: {n}' in text and 'id: "minecraft:iron_ingot"' in text and 'id: "minecraft:gold_ingot"' in text
            call('screenshot',game.work/f'{tier}-filter.png')
            sample(n-1)
            text=cmd('data get block 1 200 0 modules')
            assert 'id: "minecraft:iron_ingot"' in text and 'id: "minecraft:gold_ingot"' not in text
            counts=call('inventory')['counts'];assert counts['minecraft:iron_ingot']==64 and counts['minecraft:gold_ingot']==8
            call('click-slot',300,'shift');settle()
            counts=call('inventory')['counts'];assert counts[ident]==1
            call('close');settle()
            # Use the empty hotbar slot for the next hand installation.
            inventory=call('inventory');slot=next(s['slot'] for s in inventory['hotbar'] if s.get('item') is None)
            call('select',slot+1);settle()
            checked.append({'tier':tier,'sample_slots':n,'first_and_last_slot_edited':True,
                            'last_sample_cleared':True,'inventory_counts_preserved':True})
        counts=call('inventory')['counts'];assert counts=={'minecraft:iron_ingot':64,'minecraft:gold_ingot':8,
            **{f'prettypipes:{t}_extraction_module':1 for t in ('low','medium','high')}}
        assert call('status')['server']['decode_errors']==0
        call('save')
    finally:game.stop()
    report={'schema':1,'graphical_tiers':checked,'wire_component_roundtrip_tested':True,
            'no_ghost_items_returned_with_modules':True,'protocol_decode_errors':0,
            'licensed_account_or_dedicated_join_tested':False,'published':False,
            'screenshots_sha256':{f'{t}-filter.png':hashlib.sha256((game.work/f'{t}-filter.png').read_bytes()).hexdigest() for t in ('low','medium','high')}}
    (game.work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('all three graphical filter layouts and ghost boundaries passed')


if __name__=='__main__':main()

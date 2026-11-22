#!/usr/bin/env python3
"""Craft pipes/modules and operate redstone routing with real GUI/lever packets.

Basic ingredients, iron for transport, an initial bench/chests/levers and glass
platform are fixtures. Pipes, modules and transport cargo are never seeded.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import re
import time

from graphical_fixture import GraphicalFixture
from live_oritech_gathered_gui import GatheredChain,TABLE
import live_pretty_pipes_redstone_server as fixture
from reference_pretty_pipes import sprint

# The scenario runs far from spawn in its own graphical world. Its reused
# dedicated assertions resolve these positions in this separate process only.
fixture.SOURCE='-2270 200 2272';fixture.FIRST='-2269 200 2272';fixture.MID='-2268 200 2272'
fixture.END='-2267 200 2272';fixture.OUTPUT='-2266 200 2272';fixture.SIDE='-2268 200 2271'
fixture.POWER={fixture.FIRST:'-2269 200 2273',fixture.MID:'-2268 200 2273',fixture.END:'-2267 200 2273'}
xyz=lambda pos:tuple(map(int,pos.split()))


class Graphical(fixture.Redstone):
    def __init__(self,game):self.game=game;self.test=GatheredChain(game);self.rows=[];self.installed=[]
    def command(self,line):
        reply=self.game.command(line);self.rows.append({'command':line,'reply':reply});return reply
    def items(self,pos):
        if pos not in (fixture.FIRST,fixture.MID,fixture.END):return super().items(pos)
        result=Counter()
        for item in (fixture.IRON,fixture.RED,fixture.HIGH):
            # Match root owned inventory entries. Recursing over SNBT text
            # would incorrectly count the extractor's iron ghost as cargo.
            reply=self.command('data get block '+pos+' Items[{id:"'+item+'"}].count')
            match=re.search(r'has the following block data:\s*(\d+)',reply)
            if match:result[item]=int(match[1])
            else:assert 'Found no elements matching' in reply,reply
        return result
    def front(self,pos,z_offset=3.5):
        x,y,z=xyz(pos);self.command(f'tp @s {x+0.5} {y} {z+z_offset}')
    def hotbar(self,item):
        call,settle=self.game.call,self.game.settle
        inv=call('inventory')
        if not any(s.get('item')==item for s in inv['hotbar']):
            call('open-inventory');settle();_,slots=self.test.slots()
            source=next(i for i,s in slots.items() if 9<=i<36 and s.get('item')==item)
            call('click-slot',source);settle();call('click-slot',8);settle()
            if call('screen').get('carried'):call('click-slot',source);settle()
            call('close')
        call('select',item);settle()
    def modules(self,pos,ids):
        self.front(pos)
        for item in ids:
            before=self.test.counts().get(item,0);self.hotbar(item)
            self.game.call('interact',*xyz(pos));self.game.settle()
            assert self.test.counts().get(item,0)==before-1,(pos,item,self.test.counts())
            self.installed.append({'pos':pos,'item':item})
    def source(self):
        self.front(fixture.SOURCE);self.test.empty_hand();self.game.call('interact',*xyz(fixture.SOURCE));self.game.settle()
        before=self.test.counts().get(fixture.IRON,0);self.test.put(fixture.IRON,8,300)
        self.game.call('close');self.game.settle()
        assert self.test.counts().get(fixture.IRON,0)==before-8 and self.items(fixture.SOURCE)[fixture.IRON]==8
    def powered(self,pos):return 'powered=true' in self.game.call('block',*xyz(fixture.POWER[pos]))['state']
    def power(self,pos,on):
        assert self.powered(pos)!=on,(pos,on)
        self.front(fixture.POWER[pos],2.5);self.test.empty_hand()
        self.game.call('interact',*xyz(fixture.POWER[pos]));self.game.settle()
        assert self.powered(pos)==on,(pos,on)
    def snapshot(self):
        return {'source':self.items(fixture.SOURCE)[fixture.IRON],'destination':self.items(fixture.OUTPUT)[fixture.IRON],
                'side_destination':self.items(fixture.SIDE)[fixture.IRON],
                'cargo':sum(self.items(p)[fixture.IRON] for p in (fixture.FIRST,fixture.MID,fixture.END)),
                'redstone_modules':sum(self.items(p)[fixture.RED] for p in (fixture.FIRST,fixture.MID,fixture.END)),
                'extractors':sum(self.items(p)[fixture.HIGH] for p in (fixture.FIRST,fixture.MID,fixture.END)),
                'powered':{p:self.powered(p) for p in (fixture.FIRST,fixture.MID,fixture.END)}}
    def menu_checks(self):
        call,settle=self.game.call,self.game.settle
        self.front(fixture.FIRST);self.test.empty_hand();call('interact',*xyz(fixture.FIRST));settle()
        screen,slots=self.test.slots()
        assert slots[300].get('item')==fixture.RED and slots[301].get('item')==fixture.HIGH and not slots[302].get('item'),screen
        spare=next(i for i,s in slots.items() if i<36 and s.get('item')==fixture.RED)
        call('click-slot',spare);settle();call('click-slot',302);settle()
        screen,slots=self.test.slots();assert screen['carried']['item']==fixture.RED and not slots[302].get('item'),screen
        call('click-slot',spare);settle()
        def click(x,y):
            status=call('status');w,h=status['renderer']['size']
            call('click-at',(w//2-176)//2+x,(h//2-203)//2+y);settle()
        _,slots=self.test.slots();iron=next(i for i,s in slots.items() if i<36 and s.get('item')==fixture.IRON)
        before=self.test.counts()[fixture.IRON]
        call('click-slot',iron);settle();click(16,86);call('click-slot',iron);settle();click(155,104)
        assert self.test.counts()[fixture.IRON]==before
        saved=self.command('data get block '+fixture.FIRST+' modules')
        assert 'prettypipes:item_filter_data' in saved and 'whitelist: 1b' in saved,saved
        call('click-slot',300,'shift');settle()
        assert self.test.counts()[fixture.RED]==2
        _,slots=self.test.slots();red=next(i for i,s in slots.items() if i<36 and s.get('item')==fixture.RED)
        call('click-slot',red,'shift');settle()
        assert self.test.counts()[fixture.RED]==1
        assert self.command('data get block '+fixture.FIRST+' modules')==saved
        call('screenshot',self.game.work/'redstone-extractor-filter-menu.png');call('close');settle()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('server-dir','work'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();game=GraphicalFixture(args.server_dir,args.work,'0.8.0','techquest-redstone-gui','TQRedstoneGui',frozen=True)
    shutil.copytree(game.server/'techquest-horizon-test/datapacks',game.work/'saves'/game.world/'datapacks')
    p=Graphical(game);t=p.test;cmd,call=game.command,game.call
    supplied={'minecraft:redstone':31,'minecraft:iron_bars':4,'minecraft:glass':2,'minecraft:copper_ingot':2,
              'minecraft:quartz':20,'minecraft:stone_slab':10,'minecraft:piston':1,'minecraft:iron_ingot':20,
              'minecraft:gold_ingot':7,'minecraft:diamond':1,'minecraft:stick':4}
    try:
        game.start('craft-and-prepare');cmd('clear @s');cmd('gamemode spectator');cmd('tp @s -2272 200 2275')
        call('wait-ready',timeout=180);cmd('tick freeze');cmd('forceload add -2288 2256 -2256 2288')
        deadline=time.monotonic()+120
        for corner in ('-2275 199 2268','-2262 199 2277'):
            while 'Test passed' not in cmd('execute if loaded '+corner):
                assert time.monotonic()<deadline;call('wait',20)
        assert 'Successfully filled' in cmd('fill -2275 199 2268 -2262 199 2277 minecraft:glass')
        cmd('setblock '+' '.join(map(str,TABLE))+' minecraft:crafting_table');cmd('tp @s -2271.5 200 2275.5');cmd('gamemode survival')
        assert 'techquest_terralith' in cmd('datapack list enabled')
        for item,count in supplied.items():cmd(f'give @s {item} {count}')
        for _ in range(4):t.craft(['r','s'],{'r':'minecraft:redstone','s':'minecraft:stick'},'minecraft:redstone_torch',inventory=True)
        for _ in range(2):t.craft([' R ','IGI',' C '],{'R':'minecraft:redstone','I':'minecraft:iron_bars','G':'minecraft:glass','C':'minecraft:copper_ingot'},'prettypipes:pipe',4)
        for _ in range(5):t.craft(['QRQ','SPS','QRQ'],{'Q':'minecraft:quartz','R':'minecraft:redstone','S':'minecraft:stone_slab','P':'prettypipes:pipe'},'prettypipes:blank_module')
        t.craft([' P ','RMR',' R '],{'P':'minecraft:piston','R':'minecraft:redstone','M':'prettypipes:blank_module'},'prettypipes:low_extraction_module')
        t.craft([' I ','IMI',' I '],{'I':'minecraft:iron_ingot','M':'prettypipes:low_extraction_module'},'prettypipes:medium_extraction_module')
        t.craft(['GDG','GMG','GGG'],{'G':'minecraft:gold_ingot','D':'minecraft:diamond','M':'prettypipes:medium_extraction_module'},'prettypipes:high_extraction_module')
        for _ in range(4):t.craft([' S ','RMR',' R '],{'S':'minecraft:redstone_torch','R':'minecraft:redstone','M':'prettypipes:blank_module'},fixture.RED)
        for pos in (fixture.SOURCE,fixture.OUTPUT,fixture.SIDE):cmd('setblock '+pos+' minecraft:chest')
        for pos in (fixture.FIRST,fixture.MID,fixture.END):
            p.front(pos,2.5);t.place('prettypipes:pipe',xyz(pos))
        # Place floor controls after the pipes so their hitboxes cannot
        # intercept the player's initial placement clicks on the floor.
        for pos in fixture.POWER.values():cmd('setblock '+pos+' minecraft:lever[face=floor,facing=north,powered=false]')
        p.modules(fixture.FIRST,[fixture.RED,fixture.HIGH]);p.modules(fixture.MID,[fixture.RED]);p.modules(fixture.END,[fixture.RED])
        p.menu_checks();prepared=p.prepare_flow();call('screenshot',game.work/'powered-route-saved.png');call('save')
    finally:game.stop()
    try:
        game.start('verify');completed=p.finish({'checks':prepared});call('screenshot',game.work/'redstone-two-batches-delivered.png');call('save')
    finally:game.stop()
    try:
        game.start('final-reopen');assert p.snapshot()==completed['final']
        status=call('status');assert status['server']['joined'] and status['server']['decode_errors']==0
        final_inventory=t.counts();assert final_inventory.get(fixture.RED)==1 and final_inventory.get(fixture.IRON,0)==0,final_inventory
        call('save')
    finally:game.stop()
    commands=[row['args'][1] for row in game.rows if row['args'][0]=='command']
    assert not any(line.startswith('give @s prettypipes:') or line.startswith(('data merge','data modify','item replace','loot ')) for line in commands)
    assert not any(line.startswith('setblock ') and 'prettypipes:' in line for line in commands)
    assert len(t.crafts)==18
    report={'schema':1,'pretty_pipes_content_and_native':'0.8.0','crafts':t.crafts,'prepared':prepared,'completed':completed,
            'installed_by_player':p.installed,'coinstalled_extractor_in_second_slot_filter_edited':True,'ghost_sample_keeps_actual_iron':True,
            'duplicate_redstone_module_rejected':True,'shift_removal_and_reinstallation_preserve_filter':True,
            'all_six_source_recipes_crafted_through_menus':True,'pipes_and_modules_player_crafted_and_placed':True,
            'power_toggled_through_lever_interaction':True,'two_batches_16_items_delivered':True,
            'two_physical_reopens_passed':True,'final_inventory':final_inventory,'basic_ingredient_fixtures':supplied,
            'bench_chest_lever_glass_platform_travel_and_tick_fixtures':True,'transport_cargo_seeded':False,
            'protocol_decode_errors':0,'licensed_account_or_dedicated_join_tested':False,'published':False}
    (game.work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n');print('Crafted redstone modules, lever routing, coinstalled filter and physical reopens passed',flush=True)


if __name__=='__main__':main()

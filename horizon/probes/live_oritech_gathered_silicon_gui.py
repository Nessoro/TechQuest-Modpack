#!/usr/bin/env python3
"""Gather every silicon-route ingredient and operate crafted machines in one world.

Only the iron pickaxe is given. Travel, carved access/glass supports, peaceful
mode and tick control are fixtures; ores, fuel, sand, metals, alloys, crafting
stations, motors, machines, processing intermediates and output are not seeded.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import time

from graphical_fixture import GraphicalFixture
from live_oritech_gathered_gui import GatheredChain, DEEP, UPPER, TABLE, SMELTER, GENERATOR, audit_commands, resume_gather

PULVERIZER=(-2269,200,2272)
FURNACE=(-2268,200,2271)
CORE=(-2268,201,2271)


class SiliconChain(GatheredChain):
    def __init__(self,game):
        super().__init__(game)
        self.full_call=self.call
        self.call=self.nearby_call

    def nearby_call(self,*args,**kwargs):
        # A whole radius-64 scan repeatedly reads over two million blocks.
        # Prefer the nearby vein, keeping the original full search as fallback.
        # Both actual searches remain in GraphicalFixture's action evidence.
        if len(args)==3 and args[0]=='find-block' and args[2]==64:
            nearby=self.full_call('find-block',args[1],16,**kwargs)
            if nearby['count']>0:
                # Nickel is required to originate inside a Terralith biome.
                # A nearer vanilla-biome vein must not hide the eligible
                # target that the original radius-64 search could find.
                if args[1]!='oritech:deepslate_nickel_ore' or any(
                    'Test passed' in self.cmd('execute if biome '+' '.join(map(str,row['pos']))+' #terralith:all_terralith_biomes')
                    for row in nearby['nearest']):
                    return nearby
        try:
            return self.full_call(*args,**kwargs)
        except RuntimeError as error:
            if not args or args[0]!='break' or 'no face of block' not in str(error):raise
            # Approach the exposed front face from one block away. The first
            # failed aim starts no mining task; do not replace the ore itself.
            x,y,z=map(int,args[1:4])
            self.cmd('tick freeze')
            self.cmd(f'fill {x-1} {y} {z+1} {x+1} {y+2} {z+2} minecraft:air')
            self.cmd(f'fill {x-1} {y+3} {z+1} {x+1} {y+3} {z+2} minecraft:glass')
            self.cmd(f'setblock {x} {y-1} {z+1} minecraft:glass')
            self.cmd(f'tp @s {x+0.5} {y} {z+1.5}')
            self.cmd('tick unfreeze')
            self.full_call('wait-ready',timeout=180)
            return self.full_call(*args,**kwargs)

    def gather(self,block,item,count,center,*,terralith=False):
        origins=[tuple(row['pos']) for row in reversed(self.mined) if row['item']==item][:1]
        origins += [tuple(center)]
        origins += [(center[0]+dx,center[1],center[2]+dz)
                    for dx,dz in ((48,0),(-48,0),(0,48),(0,-48),(48,48),(-48,-48))]
        for origin in dict.fromkeys(origins):
            if self.counts().get(item,0)>=count:return
            try:
                return super().gather(block,item,count,origin,terralith=terralith)
            except AssertionError as error:
                reason=error.args[0] if error.args else None
                # Search exhaustion is a reason to scout the next natural
                # area. Mining/drop/menu/conservation failures remain fatal.
                empty=isinstance(reason,tuple) and len(reason)==2 and (
                    reason==('no eligible natural target',block) or
                    (reason[0]==block and isinstance(reason[1],dict) and reason[1].get('count')==0))
                if not empty:raise
                print('scouting next area for',item,'after',origin,flush=True)
        raise AssertionError(('natural search areas exhausted',item,self.counts().get(item,0),count))

    def state(self):
        result={}
        for label,pos in (('generator',GENERATOR),('pulverizer',PULVERIZER),('furnace',FURNACE)):
            for key in ('energy','"oritech.machine_progress"','Items'):
                result[label+':'+key]=self.cmd('data get block '+' '.join(map(str,pos))+' '+key).split('block data:')[-1].strip()
        return result

    def open_machine(self,pos):
        self.empty_hand();self.call('interact',*pos);self.settle()
        screen,slots=self.slots();assert screen['screen']=='container',screen
        return screen,slots

    def step(self,ticks):
        before=self.clock()
        self.cmd(f'tick step {ticks}');self.call('wait',ticks+8)
        assert self.clock()-before==ticks

    def clock(self):
        reply=self.cmd('time query gametime')
        match=re.search(r'The (?:game )?time is (\d+)',reply)
        assert match,reply
        return int(match[1])

    def bench(self):
        self.cmd('tp @s -2271.5 200 2275.5')

    def prepare(self):
        self.travel((-2272,200,2275));self.cmd('tick freeze')
        self.cmd('forceload add -2288 2256 -2256 2288')
        deadline=time.monotonic()+120
        for pos in ('-2275 199 2267','-2265 199 2278'):
            while 'Test passed' not in self.cmd('execute if loaded '+pos):
                assert time.monotonic()<deadline,('work platform not loaded',pos)
                self.call('wait',20)
        assert 'Successfully filled' in self.cmd('fill -2275 199 2267 -2265 199 2278 minecraft:glass')
        self.bench();self.cmd('gamemode survival')
        for _ in range(4):self.craft(['l'],{'l':'minecraft:acacia_log'},'minecraft:acacia_planks',4,inventory=True)
        for _ in range(2):self.craft(['pp','pp'],{'p':'minecraft:acacia_planks'},'minecraft:crafting_table',inventory=True)
        self.place('minecraft:crafting_table',TABLE)
        for _ in range(3):self.craft(['ccc','c c','ccc'],{'c':'minecraft:cobblestone'},'minecraft:furnace')
        self.place('minecraft:furnace',SMELTER)
        for item,count,output,fuel in (('oritech:raw_nickel',20,'oritech:nickel_ingot',3),
                                       ('minecraft:raw_iron',33,'minecraft:iron_ingot',5),
                                       ('minecraft:raw_gold',2,'minecraft:gold_ingot',1),
                                       ('minecraft:raw_copper',13,'minecraft:copper_ingot',2)):
            self.smelt(item,count,output,fuel)
        for _ in range(14):self.craft(['aa ','bb '],{'a':'minecraft:iron_ingot','b':'minecraft:coal'},'oritech:steel_ingot')
        self.craft(['aa ','bb '],{'a':'minecraft:gold_ingot','b':'minecraft:redstone'},'oritech:electrum_ingot')
        for _ in range(2):self.craft(['iii','ccc','iii'],{'i':'oritech:nickel_ingot','c':'oritech:steel_ingot'},'oritech:magnetic_coil',4)
        self.craft(['ccc','ccc','ccc'],{'c':'minecraft:copper_ingot'},'minecraft:copper_block')
        for _ in range(2):self.craft([' s ','wcw','wcw'],{'s':'oritech:nickel_ingot','w':'oritech:steel_ingot','c':'oritech:magnetic_coil'},'oritech:motor')
        self.craft(['fff','fcf','sbs'],{'f':'minecraft:iron_ingot','c':'oritech:nickel_ingot','s':'oritech:motor','b':'minecraft:copper_block'},'oritech:pulverizer_block')
        self.craft(['fff','fcf','sbs'],{'f':'oritech:nickel_ingot','c':'minecraft:copper_ingot','s':'oritech:magnetic_coil','b':'minecraft:furnace'},'oritech:basic_generator_block')
        self.cmd('tp @s -2267.5 200 2275.5')
        self.place('oritech:pulverizer_block',PULVERIZER);self.place('oritech:basic_generator_block',GENERATOR)
        assert self.call('block',PULVERIZER[0],PULVERIZER[1]+1,PULVERIZER[2])['block']=='minecraft:air'
        for item,count,pos in (('minecraft:quartz',2,PULVERIZER),('minecraft:coal',2,GENERATOR)):
            self.open_machine(pos);self.put(item,count,300);self.call('close')
        self.step(45)
        assert self.state()['pulverizer:"oritech.machine_progress"'] in ('44','45')
        self.call('screenshot',self.g.work/'gathered-active-pulverizer.png')

    def finish_silicon(self):
        self.step(1)
        assert self.state()['pulverizer:"oritech.machine_progress"'] in ('0','1')
        self.step(240)
        _,slots=self.open_machine(PULVERIZER)
        assert slots[301].get('item')=='oritech:quartz_dust' and slots[301]['count']==2,slots
        self.call('click-slot',301,'shift');self.settle();self.call('close')
        self.bench()
        self.craft(['aa ','bb '],{'a':'oritech:quartz_dust','b':'minecraft:sand'},'oritech:raw_silicon',3)
        self.smelt('oritech:raw_silicon',3,'oritech:silicon',1)
        self.craft(['fff','mcm','sbs'],{'f':'minecraft:copper_ingot','m':'oritech:silicon','c':'oritech:electrum_ingot','s':'oritech:magnetic_coil','b':'minecraft:furnace'},'oritech:powered_furnace_block')
        self.craft(['sss','scs','sss'],{'s':'minecraft:acacia_planks','c':'minecraft:crafting_table'},'oritech:machine_core_1')
        self.cmd('tp @s -2267.5 200 2268.5')
        self.place('oritech:powered_furnace_block',FURNACE);self.place('oritech:machine_core_1',CORE)
        self.empty_hand();self.call('interact',*FURNACE);self.settle()
        assert '1b' in self.cmd('data get block '+' '.join(map(str,FURNACE))+' techquest_assembled')
        self.open_machine(FURNACE);self.put('minecraft:raw_iron',2,300);self.call('close')
        self.step(45)
        assert self.state()['furnace:"oritech.machine_progress"'] in ('44','45')
        self.call('screenshot',self.g.work/'gathered-active-silicon-furnace.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('server-dir','work'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--resume-from',type=Path,help='own previous gather-only checkpoint; retain complete action provenance')
    args=parser.parse_args()
    game=GraphicalFixture(args.server_dir,args.work,'0.3.0','techquest-gathered-silicon','TQGatherSilicon',module='oritech',frozen=True)
    test=SiliconChain(game);cmd,call=game.command,game.call
    if args.resume_from:resumed=resume_gather(game,test,args.resume_from)
    else:shutil.copytree(game.server/'techquest-horizon-test/datapacks',game.work/'saves'/game.world/'datapacks')
    try:
        game.start('gather')
        if args.resume_from:assert test.counts()==resumed
        else:cmd('clear @s');cmd('give @s minecraft:iron_pickaxe 1')
        cmd('difficulty peaceful')
        assert 'techquest_terralith' in cmd('datapack list enabled')
        for block,item,count,center,terra in (
            ('oritech:deepslate_nickel_ore','oritech:raw_nickel',20,DEEP,True),
            ('minecraft:deepslate_iron_ore','minecraft:raw_iron',35,DEEP,False),
            ('minecraft:deepslate_gold_ore','minecraft:raw_gold',2,DEEP,False),
            ('minecraft:deepslate_redstone_ore','minecraft:redstone',2,DEEP,False),
            ('minecraft:copper_ore','minecraft:raw_copper',13,UPPER,False),
            ('minecraft:coal_ore','minecraft:coal',44,UPPER,False),
            ('minecraft:stone','minecraft:cobblestone',24,UPPER,False),
            ('minecraft:acacia_log','minecraft:acacia_log',4,UPPER,False),
            ('minecraft:sand','minecraft:sand',2,UPPER,False)):
            test.gather(block,item,count,center,terralith=terra)
        cmd('gamemode spectator');cmd('execute in minecraft:the_nether run tp @s 0 80 0')
        call('wait-ready',timeout=180)
        test.gather('minecraft:nether_quartz_ore','minecraft:quartz',2,(0,80,0))
        cmd('gamemode spectator');cmd('execute in minecraft:overworld run tp @s -2272 200 2275')
        call('wait-ready',timeout=180);cmd('tick freeze')
        raw_counts=test.counts();call('save')
    finally:game.stop()
    checkpoint=game.work/'raw-checkpoint'
    shutil.copytree(game.work/'saves'/game.world,checkpoint/'saves'/game.world)
    shutil.copytree(game.work/'horizon-mods',checkpoint/'horizon-mods')
    shutil.copy2(game.work/'actions.json',checkpoint/'actions.json')
    try:
        game.start('craft');assert test.counts()==raw_counts
        test.prepare();pulv_counts,pulv_state=test.counts(),test.state();call('save')
    finally:game.stop()
    try:
        game.start('silicon');assert test.counts()==pulv_counts and test.state()==pulv_state
        test.finish_silicon();furnace_counts,furnace_state=test.counts(),test.state();call('save')
    finally:game.stop()
    try:
        game.start('output');assert test.counts()==furnace_counts and test.state()==furnace_state
        test.step(156)
        _,slots=test.open_machine(FURNACE)
        assert slots[301].get('item')=='minecraft:iron_ingot' and slots[301]['count']==2,slots
        call('click-slot',301,'shift');game.settle();call('close')
        final_counts,final_state=test.counts(),test.state()
        assert final_counts.get('minecraft:iron_ingot')==2 and final_counts.get('oritech:silicon')==1,final_counts
        call('screenshot',game.work/'gathered-silicon-output.png');call('save')
    finally:game.stop()
    try:
        game.start('final-reopen');assert test.counts()==final_counts and test.state()==final_state
        status=call('status');assert status['server']['joined'] and status['server']['decode_errors']==0
        call('save')
    finally:game.stop()
    audit_commands(game.rows)
    report={'schema':1,'oritech_content_version':'0.3.0','same_world_for_all_phases':True,
            'all_recipe_inputs_mined_by_survival_player':True,'only_given_item':'minecraft:iron_pickaxe',
            'mined':test.mined,'crafts':test.crafts,'smelts':test.smelts,'recipe_inputs_consumed_exactly':True,
            'raw_inventory_survives_reopen':True,'active_pulverizer_survives_exact_reopen':True,
            'active_silicon_furnace_survives_exact_reopen':True,'final_items_and_machines_survive_exact_reopen':True,
            'physical_reopens':4,'final_inventory':final_counts,'final_machine_state':final_state,
            'all_processing_machines_motors_and_core_crafted_and_placed':True,'collected_processed_iron_ingots':2,
            'ore_fuel_raw_materials_metals_machines_energy_or_outputs_injected':False,
            'fixtures':['iron pickaxe','teleports','spectator travel','carved access/glass supports and platform','peaceful difficulty','tick control','work platform forceload'],
            'unassisted_survival_from_spawn_tested':False,'licensed_dedicated_join_tested':False,
            'resumed_gather_save':str(args.resume_from.resolve()) if args.resume_from else None,
            'protocol_decode_errors':0,'full_modpack_ported':False,'published':False}
    (game.work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('All silicon-route inputs mined, machines crafted and operated; four physical reopens passed',flush=True)


if __name__=='__main__':main()

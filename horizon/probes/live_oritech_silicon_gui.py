#!/usr/bin/env python3
"""Mine quartz, craft/run a Pulverizer, then craft/run the silicon-route furnace.

Metal/alloy/coil/sand/fuel/cobblestone/wood inputs and an initial crafting bench
are fixtures. Quartz is naturally mined; motors, all machines, quartz dust,
raw silicon, silicon and processing output are never given or injected.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import time

from graphical_fixture import GraphicalFixture
from live_oritech_gathered_gui import GatheredChain, TABLE, SMELTER, GENERATOR

PULVERIZER = (-2269, 200, 2272)
FURNACE = (-2268, 200, 2271)
CORE = (-2268, 201, 2271)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('server-dir', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    game = GraphicalFixture(args.server_dir, args.work, '0.3.0', 'techquest-silicon-route', 'TQSilicon', module='oritech', frozen=True)
    shutil.copytree(game.server / 'techquest-horizon-test/datapacks', game.work / 'saves' / game.world / 'datapacks')
    test = GatheredChain(game)
    cmd, call, settle = game.command, game.call, game.settle
    def number(pos, key):
        reply = cmd('data get block ' + ' '.join(map(str, pos)) + ' ' + key)
        match = re.search(r'has the following block data:\s*(-?\d+)', reply)
        assert match, reply
        return int(match[1])
    def state(pos):
        return {key: cmd('data get block ' + ' '.join(map(str, pos)) + ' ' + key).split('block data:')[-1].strip()
                for key in ('energy', '"oritech.machine_progress"', 'Items')}
    def step(n):
        cmd(f'tick step {n}')
        call('wait', n+8)
    def open_machine(pos):
        test.empty_hand()
        call('interact', *pos)
        settle()
        screen, visible = test.slots()
        assert screen['screen'] == 'container', screen
        return screen, visible
    try:
        game.start('quartz-and-craft')
        cmd('clear @s')
        cmd('difficulty peaceful')
        cmd('give @s minecraft:iron_pickaxe 1')
        assert 'techquest_terralith' in cmd('datapack list enabled')
        cmd('gamemode spectator')
        cmd('execute in minecraft:the_nether run tp @s 0 80 0')
        call('wait-ready', timeout=180)
        test.gather('minecraft:nether_quartz_ore', 'minecraft:quartz', 2, (0, 80, 0))
        cmd('gamemode spectator')
        cmd('execute in minecraft:overworld run tp @s -2272 200 2275')
        call('wait-ready', timeout=180)
        cmd('tick freeze')
        cmd('forceload add -2288 2256 -2256 2288')
        deadline = time.monotonic() + 120
        for pos in ('-2275 199 2267', '-2265 199 2278'):
            while 'Test passed' not in cmd('execute if loaded ' + pos):
                assert time.monotonic() < deadline, ('work platform chunk not loaded', pos)
                call('wait', 20)
        assert 'Successfully filled' in cmd('fill -2275 199 2267 -2265 199 2278 minecraft:glass')
        cmd('setblock ' + ' '.join(map(str, TABLE)) + ' minecraft:crafting_table')
        cmd('tp @s -2271.5 200 2275.5')
        cmd('gamemode survival')
        supplied = {'minecraft:iron_ingot': 5, 'oritech:nickel_ingot': 8, 'oritech:steel_ingot': 8,
                    'oritech:magnetic_coil': 8, 'minecraft:copper_block': 1, 'minecraft:copper_ingot': 4,
                    'oritech:electrum_ingot': 1, 'minecraft:coal': 2, 'minecraft:sand': 2,
                    'minecraft:cobblestone': 24, 'minecraft:oak_planks': 8, 'minecraft:crafting_table': 1,
                    'minecraft:raw_iron': 2}
        for item, count in supplied.items():
            cmd(f'give @s {item} {count}')
        for _ in range(3):
            test.craft(['ccc', 'c c', 'ccc'], {'c': 'minecraft:cobblestone'}, 'minecraft:furnace')
        test.place('minecraft:furnace', SMELTER)
        for _ in range(2):
            test.craft([' s ', 'wcw', 'wcw'], {'s': 'oritech:nickel_ingot', 'w': 'oritech:steel_ingot', 'c': 'oritech:magnetic_coil'}, 'oritech:motor')
        test.craft(['fff', 'fcf', 'sbs'], {'f': 'minecraft:iron_ingot', 'c': 'oritech:nickel_ingot', 's': 'oritech:motor', 'b': 'minecraft:copper_block'}, 'oritech:pulverizer_block')
        test.craft(['fff', 'fcf', 'sbs'], {'f': 'oritech:nickel_ingot', 'c': 'minecraft:copper_ingot', 's': 'oritech:magnetic_coil', 'b': 'minecraft:furnace'}, 'oritech:basic_generator_block')
        cmd('tp @s -2267.5 200 2275.5')
        test.place('oritech:pulverizer_block', PULVERIZER)
        test.place('oritech:basic_generator_block', GENERATOR)
        assert call('block', PULVERIZER[0], PULVERIZER[1]+1, PULVERIZER[2])['block'] == 'minecraft:air'
        screen, slots = open_machine(PULVERIZER)
        assert {slot for slot in slots if 300 <= slot < 500} == {300, 301, 302}, screen
        source = next(i for i, slot in slots.items() if i < 36 and slot.get('item') == 'minecraft:quartz')
        call('click-slot', source)
        settle()
        for output in (301, 302):
            call('click-slot', output)
            settle()
            screen, slots = test.slots()
            assert screen['carried']['item'] == 'minecraft:quartz' and not slots[output].get('item'), screen
        call('click-slot', 300)
        settle()
        screen, slots = test.slots()
        assert not screen.get('carried') and slots[300]['count'] == 2, screen
        call('screenshot', game.work / 'pulverizer-input-menu.png')
        call('close')
        open_machine(GENERATOR)
        test.put('minecraft:coal', 1, 300)
        call('close')
        step(45)
        saved = {'generator': state(GENERATOR), 'pulverizer': state(PULVERIZER), 'inventory': test.counts()}
        assert 0 < number(PULVERIZER, '"oritech.machine_progress"') < 100
        call('screenshot', game.work / 'powered-pulverizer.png')
        call('save')
    finally:
        game.stop()
    try:
        game.start('silicon-and-furnace')
        assert state(GENERATOR) == saved['generator'] and state(PULVERIZER) == saved['pulverizer']
        assert test.counts() == saved['inventory']
        step(1)
        first_tick_progress = number(PULVERIZER, '"oritech.machine_progress"')
        assert first_tick_progress in (0, 1), first_tick_progress
        step(240)
        screen, slots = open_machine(PULVERIZER)
        assert not slots[300].get('item') and not slots[302].get('item'), screen
        assert slots[301].get('item') == 'oritech:quartz_dust' and slots[301]['count'] == 2, screen
        call('click-slot', 301, 'shift')
        settle()
        assert test.counts().get('oritech:quartz_dust') == 2
        call('screenshot', game.work / 'quartz-dust-output.png')
        call('close')
        cmd('tp @s -2271.5 200 2275.5')
        test.craft(['aa ', 'bb '], {'a': 'oritech:quartz_dust', 'b': 'minecraft:sand'}, 'oritech:raw_silicon', 3)
        test.smelt('oritech:raw_silicon', 3, 'oritech:silicon', 1)
        test.craft(['fff', 'mcm', 'sbs'], {'f': 'minecraft:copper_ingot', 'm': 'oritech:silicon', 'c': 'oritech:electrum_ingot', 's': 'oritech:magnetic_coil', 'b': 'minecraft:furnace'}, 'oritech:powered_furnace_block')
        test.craft(['sss', 'scs', 'sss'], {'s': 'minecraft:oak_planks', 'c': 'minecraft:crafting_table'}, 'oritech:machine_core_1')
        assert test.counts().get('oritech:silicon') == 1
        # Approach from the north so the generator cannot obscure placement.
        cmd('tp @s -2267.5 200 2268.5')
        test.place('oritech:powered_furnace_block', FURNACE)
        test.place('oritech:machine_core_1', CORE)
        test.empty_hand()
        call('interact', *FURNACE)
        settle()
        assert number(FURNACE, 'techquest_assembled') == 1
        open_machine(FURNACE)
        test.put('minecraft:raw_iron', 2, 300)
        call('close')
        step(240)
        screen, slots = open_machine(FURNACE)
        assert slots[301].get('item') == 'minecraft:iron_ingot' and slots[301]['count'] == 2, screen
        call('click-slot', 301, 'shift')
        settle()
        call('close')
        assert test.counts().get('minecraft:iron_ingot') == 2
        final = {'generator': state(GENERATOR), 'pulverizer': state(PULVERIZER), 'furnace': state(FURNACE), 'inventory': test.counts()}
        call('screenshot', game.work / 'silicon-route-working.png')
        call('save')
    finally:
        game.stop()
    try:
        game.start('final-reopen')
        assert state(GENERATOR) == final['generator'] and state(PULVERIZER) == final['pulverizer']
        assert state(FURNACE) == final['furnace'] and test.counts() == final['inventory']
        status = call('status')
        assert status['server']['joined'] and status['server']['decode_errors'] == 0
        call('save')
    finally:
        game.stop()
    commands = [row['args'][1] for row in game.rows if row['args'][0] == 'command']
    forbidden = ['minecraft:quartz', 'oritech:quartz_dust', 'oritech:raw_silicon', 'oritech:silicon', 'oritech:motor', 'oritech:pulverizer_block', 'oritech:basic_generator_block', 'oritech:powered_furnace_block', 'oritech:machine_core_1']
    assert not any(line.startswith('give @s '+item+' ') for line in commands for item in forbidden)
    assert not any(line.startswith(('data merge', 'data modify', 'item replace', 'loot ')) for line in commands)
    report = {'schema': 1, 'oritech_content_version': '0.3.0', 'native_machine_version': '0.2.0',
              'natural_nether_quartz_mined': test.mined, 'crafts': test.crafts, 'smelts': test.smelts,
              'recipe_inputs_consumed_exactly': True, 'motors_and_all_processing_machines_crafted_and_player_placed': True,
              'pulverizer_works_without_core': True, 'both_output_slots_refuse_input': True,
              'quartz_dust_raw_silicon_and_silicon_not_given': True, 'three_silicon_ingots_smelted_from_natural_quartz_route': True,
              'default_silicon_furnace_recipe_crafted': True, 'crafted_furnace_assembled_and_produced_two_collected_iron_ingots': True,
              'source_transient_recipe_reset_after_load_observed': True, 'first_reopen_tick_progress': first_tick_progress,
              'saved': saved, 'final': final, 'final_inventory_and_machine_state_physically_reopened_exactly': True,
              'base_materials_and_initial_bench_fixtures': supplied, 'synthetic_local_player': True,
              'unassisted_survival_or_licensed_join_tested': False, 'protocol_decode_errors': 0, 'published': False}
    (game.work / 'checked-result.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Natural quartz -> crafted Pulverizer -> silicon -> crafted working furnace and physical reopens passed')


if __name__ == '__main__':
    main()

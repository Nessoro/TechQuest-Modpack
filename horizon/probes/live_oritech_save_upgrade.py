#!/usr/bin/env python3
"""Read and reopen a verified own Foundry 0.4 GUI save with content 0.5.

The original save is copied and hashed; it is never opened in place. No items,
energy, machine state or block fixtures are inserted. Tests IDs/counts, energy,
progress, facing and core offsets, not arbitrary component or world conversion.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

from live_oritech_energy import items, text
from install_isolated_server import checked_path, fresh_environment, tree_files, verify

WORLD = 'techquest-assembler-upgrade'
OLD_WORLD = 'techquest-foundry-gui'
FIELDS = ('energy', '"oritech.machine_progress"', 'Items')
coord = lambda p: ' '.join(map(str, p))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('server-dir', 'source-work', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    server, source, work = checked_path(args.server_dir), checked_path(args.source_work), args.work.absolute()
    lock = verify(server)
    assert lock['modules']['oritech']['version'] == '0.5.0'
    assert not work.exists() and not work.is_symlink() and not any(p.is_symlink() for p in work.parents)
    assert source not in work.parents and work not in source.parents and server not in work.parents
    proof = json.loads((Path(__file__).resolve().parents[1] / 'ORITECH_FOUNDRY_RESULT.json').read_text())
    old_report = source / 'checked-result.json'
    assert sha(old_report) == proof['proof_files_sha256'][source.name + '/checked-result.json']
    old = json.loads(old_report.read_text())
    assert old['oritech_content_version'] == '0.4.0' and old['two_physical_reopens_exact']
    old_lock = verify(source.parent / proof['installation']['profile'])
    for ident, spec in old_lock['modules'].items():
        assert sha(source / 'horizon-mods' / (ident + '.hmod')) == spec['sha256']
    positions = {}
    for row in json.loads((source / 'actions.json').read_text()):
        args_ = row['args']
        if args_[0] == 'place' and args_[-1] in ('oritech:basic_generator_block', 'oritech:pulverizer_block', 'oritech:foundry_block') and row['reply'].get('changed'):
            positions[args_[-1]] = tuple(map(int, args_[1:4]))
    names = {'generator': 'oritech:basic_generator_block', 'pulverizer': 'oritech:pulverizer_block', 'foundry': 'oritech:foundry_block'}
    assert set(positions) == set(names.values())
    cores = old['core_positions']
    original_world = source / 'saves' / OLD_WORLD
    before_hashes = {name: sha(p) for name, p in tree_files(original_world).items()}
    work.mkdir(mode=0o700)
    shutil.copytree(server / 'horizon-mods', work / 'horizon-mods')
    shutil.copy2(server / 'horizon-mods.txt', work / 'horizon-mods.txt')
    shutil.copytree(original_world, work / 'saves' / WORLD)
    (work / 'eula.txt').write_text('eula=true\n')
    config = tomllib.loads((server / 'server.toml').read_text())

    def observe():
        ops = []
        for ident, pos in positions.items():
            state = '[facing=' + old['placed_facing'] + ']' if ident == names['foundry'] else ''
            ops.append({'op': 'cmd', 'cmd': 'execute if block ' + coord(pos) + ' ' + ident + state})
            for key in FIELDS:
                ops.append({'op': 'cmd', 'cmd': 'data get block ' + coord(pos) + ' ' + key})
        ops.append({'op': 'cmd', 'cmd': 'data get block ' + coord(positions[names['foundry']]) + ' techquest_assembled'})
        for pos in cores:
            for key in ('techquest_core_used', 'controller_x', 'controller_y', 'controller_z'):
                ops.append({'op': 'cmd', 'cmd': 'data get block ' + coord(pos) + ' ' + key})
        ops.append({'op': 'cmd', 'cmd': 'data get entity @s Inventory'})
        return ops

    def run(phase, tick):
        ops = [{'op': 'cmd', 'cmd': 'tick freeze'}, {'op': 'cmd', 'cmd': 'tp @s -2270 200 2272.5'},
               {'op': 'cmd', 'cmd': 'forceload add -2288 2256 -2256 2288'}, {'op': 'settle'}]
        if tick:
            ops += [{'op': 'cmd', 'cmd': 'tick step 1'}, {'op': 'tick', 'n': 3}]
        ops += observe() + [{'op': 'cmd', 'cmd': 'save-all flush'}]
        script, output = work / (phase + '-operations.jsonl'), work / (phase + '-result.jsonl')
        script.write_text(''.join(json.dumps(v) + '\n' for v in ops))
        env = fresh_environment(work / ('homes-' + phase))
        env.update(HORIZON_STILL='1', HORIZON_PLAYER_NAME='TQFoundryGui', HORIZON_COMMAND_SCRIPT=str(script), HORIZON_COMMAND_OUTPUT=str(output))
        with (work / (phase + '-console.log')).open('x') as log:
            subprocess.run([config['engine']['path'], '--resources', config['engine']['resources'], '--game-dir', str(work), '--world', WORLD, '--seed', '263', '--radius', '2'], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        by_cmd = {row['cmd']: row for row in rows}
        for row in rows:
            if row['cmd'].startswith('execute if block '): assert row['results'][-1][0], row
        for name, ident in names.items():
            pos = positions[ident]
            for key in FIELDS[:2]:
                row = by_cmd['data get block ' + coord(pos) + ' ' + key]
                assert row['results'][-1][0] and row['results'][-1][1] == int(old['final'][name][key]), (phase, name, key, row)
            row = by_cmd['data get block ' + coord(pos) + ' Items']
            assert not items(row) and old['final'][name]['Items'] == 'Found no elements matching Items', (phase, name, row)
        row = by_cmd['data get block ' + coord(positions[names['foundry']]) + ' techquest_assembled']
        assert row['results'][-1] == [True, old['final']['assembled']], row
        for i, pos in enumerate(cores):
            for key, expected in [('techquest_core_used', old['final']['core_used'][i]), *zip(('controller_x', 'controller_y', 'controller_z'), (a-b for a, b in zip(positions[names['foundry']], pos)))]:
                row = by_cmd['data get block ' + coord(pos) + ' ' + key]
                assert row['results'][-1] == [True, expected], (phase, key, row, expected)
        row = by_cmd['data get entity @s Inventory']
        assert row['results'][-1][0], row
        # This checked fixture has only plain ingots and a damaged pickaxe;
        # nested default item components are not an inventory migration claim.
        value = text(row)
        ids = re.findall(r'\bid:\s*"([^"]+)"', value)
        counts = list(map(int, re.findall(r'\bcount:\s*(\d+)', value)))
        assert len(ids) == len(counts) == len(old['final']['inventory']), row
        inventory = Counter()
        for ident, count in zip(ids, counts): inventory[ident] += count
        assert dict(inventory) == old['final']['inventory'], (phase, inventory, old['final']['inventory'])
        return {'machine_energy_progress_and_empty_inventories_preserved': True, 'inventory': dict(inventory),
                'facing_assembly_and_all_core_offsets_preserved': True, 'one_normal_tick_executed': tick}

    initial = run('upgrade', True)
    reopened = run('reopen', False)
    assert {name: sha(p) for name, p in tree_files(original_world).items()} == before_hashes
    report = {'schema': 1, 'source_content_version': '0.4.0', 'target_content_version': '0.5.0',
              'source_checked_result_sha256': sha(old_report), 'source_world_files_sha256': before_hashes,
              'own_legacy_gui_world_copied': True, 'original_world_unmodified': True,
              'new_assembler_registry_entry_present_in_target_content': True,
              'old_three_machine_ids_and_facing_preserved': True, 'checks': {'upgrade': initial, 'reopen': reopened},
              'items_energy_machine_state_or_blocks_injected': False, 'synthetic_local_player': True,
              'general_component_fidelity_or_neoforge_world_import_tested': False, 'licensed_join_tested': False, 'published': False}
    (work / 'checked-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Own content 0.4 world retained machines, inventory and core links under 0.5 and physical reopen')


if __name__ == '__main__':
    main()

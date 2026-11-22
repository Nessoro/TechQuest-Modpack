#!/usr/bin/env python3
"""Dedicated raw metals -> six coils -> two motors, with physical restarts.

Generator, two assemblers, linked cores, pipes/modules, chests and raw source
inventories are fixtures. Energy, machine inventories, outputs and transport
cargo are never seeded. Start the server before each phase; each phase stops it.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from live_oritech_pipes import Probe
from install_isolated_server import verify
from reference_pretty_pipes import sprint

GEN = '143 200 176'
COILER = '143 200 175'
MOTOR = '144 200 176'
FUEL = '135 201 176'
COIL_SOURCE = '135 200 175'
MOTOR_SOURCE = '145 200 184'
OUTPUT = '135 199 177'
FUEL_MODULE = '136 201 176'
COIL_INPUT_MODULE = '136 200 175'
MOTOR_INPUT_MODULE = '145 200 183'
COIL_BRIDGE_MODULE = '143 200 174'
OUTPUT_MODULE = '144 199 176'
CORES = {
    COILER: ('144 200 175', '143 201 175', '144 201 175'),
    MOTOR: ('144 200 177', '144 201 176', '144 201 177'),
}
COAL = 'minecraft:coal'
NICKEL = 'oritech:nickel_ingot'
STEEL = 'oritech:steel_ingot'
COPPER = 'minecraft:copper_ingot'
COIL = 'oritech:magnetic_coil'
PRODUCT = 'oritech:motor'


def pipes():
    return ([(x, 201, 176) for x in range(136, 144)]
            + [(x, 200, 175) for x in range(136, 143)]
            + [(143, 200, 174), (144, 200, 174), (145, 200, 174), (145, 200, 175), (145, 200, 176)]
            + [(145, 200, z) for z in range(177, 184)]
            + [(144, 199, 176), (144, 199, 177)]
            + [(x, 199, 177) for x in range(136, 144)])


class Factory(Probe):
    def load(self):
        self.command('tick freeze')
        self.command('forceload add 128 160 159 191')
        deadline = time.monotonic() + 45
        targets = (FUEL, COIL_SOURCE, MOTOR_SOURCE, OUTPUT, *[p for group in CORES.values() for p in group])
        chunks = {(int(pos.split()[0]) >> 4, int(pos.split()[2]) >> 4) for pos in targets}
        for x, z in sorted(chunks):
            pos = f'{x*16} 200 {z*16}'
            while 'Test passed' not in self.command('execute if loaded ' + pos):
                assert time.monotonic() < deadline, ('fixture chunk not loaded', pos)
                time.sleep(.1)

    def source(self, pos, stacks):
        assert pos in (FUEL, COIL_SOURCE, MOTOR_SOURCE)
        values = ','.join('{Slot:' + str(i) + 'b,id:"' + item + '",count:' + str(count) + '}' for i, (item, count) in enumerate(stacks))
        assert 'Modified block data' in self.command('data merge block ' + pos + ' {Items:[' + values + ']}')
        assert dict(self.items(pos)) == dict(stacks)

    def extraction(self, pos, direction=None):
        component = ',components:{"prettypipes:direction_selector_data":{direction:"' + direction + '"}}' if direction else ''
        nbt = '{modules:{Size:3,Items:[{Slot:0b,id:"prettypipes:high_extraction_module",count:1' + component + '}]}}'
        assert 'Modified block data' in self.command('data merge block ' + pos + ' ' + nbt)

    def snapshot(self):
        cargo = [self.items(' '.join(map(str, pos))) for pos in pipes()]
        return {
            'sources': {pos: dict(self.items(pos)) for pos in (FUEL, COIL_SOURCE, MOTOR_SOURCE)},
            'generator': dict(self.items(GEN)), 'coiler': dict(self.items(COILER)), 'motor': dict(self.items(MOTOR)),
            'delivered_motors': self.items(OUTPUT)[PRODUCT],
            'destination_other_items': {k: v for k, v in self.items(OUTPUT).items() if k != PRODUCT},
            'cargo': {item: sum(v[item] for v in cargo) for item in (COAL, NICKEL, STEEL, COPPER, COIL, PRODUCT)},
            'energy': {pos: self.number(pos, 'energy') for pos in (GEN, COILER, MOTOR)},
            'progress': {pos: self.number(pos, '"oritech.machine_progress"') for pos in (GEN, COILER, MOTOR)},
            'assembled': {pos: self.number(pos, 'techquest_assembled') for pos in (COILER, MOTOR)},
            'core_used': {pos: self.number(pos, 'techquest_core_used') for positions in CORES.values() for pos in positions},
        }

    def setup(self):
        self.command('fill 133 198 164 147 203 186 minecraft:air')
        self.command('kill @e[type=minecraft:item]')
        self.setblock(GEN, 'oritech:basic_generator_block')
        for pos, facing in ((COILER, 'north'), (MOTOR, 'east')):
            self.setblock(pos, 'oritech:assembler_block[facing=' + facing + ']{techquest_assembled:1b}')
            for core in CORES[pos]:
                offset = [a-b for a, b in zip(map(int, pos.split()), map(int, core.split()))]
                self.setblock(core, 'oritech:machine_core_1{techquest_core_used:1b,controller_x:' + str(offset[0]) + ',controller_y:' + str(offset[1]) + ',controller_z:' + str(offset[2]) + '}')
        for pos in (FUEL, COIL_SOURCE, MOTOR_SOURCE, OUTPUT):
            self.setblock(pos, 'minecraft:chest')
        for pos in pipes():
            self.setblock(' '.join(map(str, pos)), 'prettypipes:pipe')
        self.source(FUEL, [(COAL, 2)])
        self.source(COIL_SOURCE, [(NICKEL, 2), (STEEL, 1), (COPPER, 1)])
        self.source(MOTOR_SOURCE, [(NICKEL, 1), (STEEL, 1)])

    def prepare(self):
        self.setup()
        sprint(self, 200)
        baseline = self.snapshot()
        assert sum(baseline['energy'].values()) == sum(baseline['cargo'].values()) == 0, baseline
        assert not baseline['coiler'] and not baseline['motor'] and not baseline['generator'], baseline
        assert baseline['sources'][COIL_SOURCE] == {NICKEL: 2, STEEL: 1, COPPER: 1}, baseline
        for pos in (FUEL_MODULE, COIL_INPUT_MODULE, MOTOR_INPUT_MODULE):
            self.extraction(pos)
        self.extraction(COIL_BRIDGE_MODULE, 'south')
        sprint(self, 5000)
        produced = self.snapshot()
        assert not any(produced['sources'].values()) and not produced['generator'] and not produced['coiler'], produced
        assert produced['motor'] == {COIL: 4, PRODUCT: 2}, produced
        assert produced['delivered_motors'] == 0 and not produced['destination_other_items'] and not any(produced['cargo'].values()), produced
        assert not any(produced['progress'].values()) and all(produced['core_used'].values()), produced
        assert sum(produced['energy'].values()) == 2*51200 - 2*48*128, produced
        self.extraction(OUTPUT_MODULE, 'up')
        sprint(self, 10)
        pending = self.snapshot()
        assert pending['motor'] == {COIL: 4} and pending['cargo'][PRODUCT] == 2 and pending['delivered_motors'] == 0, pending
        assert pending['cargo'][COIL] == 0, pending
        return {'without_extractors': baseline, 'automatically_processed': produced, 'saved_in_flight': pending}

    def finish(self, prior):
        reopened = self.snapshot()
        saved = prior['checks']['saved_in_flight']
        for key in saved.keys() - {'cargo', 'delivered_motors'}:
            assert reopened[key] == saved[key], (key, reopened, saved)
        assert reopened['cargo'][PRODUCT] + reopened['delivered_motors'] == 2, reopened
        assert all(reopened['cargo'][item] == 0 for item in (COAL, NICKEL, STEEL, COPPER, COIL)), reopened
        sprint(self, 400)
        delivered = self.snapshot()
        assert delivered['delivered_motors'] == 2 and not delivered['destination_other_items'] and not any(delivered['cargo'].values()), delivered
        assert delivered['motor'] == {COIL: 4} and delivered['energy'] == reopened['energy'], delivered
        return {'immediately_after_reopen': reopened, 'final': delivered}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--phase', choices=('prepare', 'verify', 'final'), required=True)
    parser.add_argument('--prior', type=Path)
    args = parser.parse_args()
    assert not args.output.exists() and not args.output.with_suffix('.commands.json').exists()
    lock = verify(args.server_dir)
    assert lock['modules']['oritech']['version'] == '0.5.0' and lock['modules']['prettypipes']['version'] == '0.10.0'
    if args.phase != 'prepare' and args.prior is None:
        parser.error('previous phase report required')
    probe = Factory(args.server_dir, Path(lock['server_binary']))
    try:
        probe.load()
        if args.phase == 'prepare':
            checks = probe.prepare()
        else:
            prior = json.loads(args.prior.read_text())
            assert prior['phase'] == ('prepare' if args.phase == 'verify' else 'verify')
            if args.phase == 'verify': checks = probe.finish(prior)
            else:
                final = probe.snapshot()
                assert final == prior['checks']['final'], (final, prior)
                checks = {'final': final}
        assert 'Saved the game' in probe.command('save-all flush')
    finally:
        try:
            subprocess.run([str(probe.binary), '--dir', str(probe.server), 'stop'], check=True, capture_output=True, text=True, timeout=90)
        finally:
            args.output.with_suffix('.commands.json').write_text(json.dumps(probe.rows, indent=2)+'\n')
    args.output.write_text(json.dumps({'schema': 1, 'phase': args.phase, 'checks': checks,
                                     'oritech_content_version': '0.5.0', 'oritech_native_version': '0.4.0', 'pretty_pipes_version': '0.10.0',
                                     'machine_linked_core_pipe_chest_module_and_raw_source_fixtures': True,
                                     'energy_machine_inventory_outputs_or_transport_cargo_seeded': False,
                                     'normal_startup_ticks_may_deliver_cargo_before_console_freeze': True,
                                     'gui_or_licensed_join_tested': False, 'server_stopped': True, 'published': False}, indent=2)+'\n')
    print('Dedicated Assembler', args.phase, 'passed', flush=True)


if __name__ == '__main__':
    main()

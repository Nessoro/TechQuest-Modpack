#!/usr/bin/env python3
"""Dedicated quartz processing through real Pretty Pipes queues and restarts.

Machine/pipe/module/chest placement and source quartz/coal are fixtures. Machine
inventories, energy, progress, output and transported cargo are never seeded.
Start the server before each phase; each phase saves and stops it.
"""
import argparse
import json
from pathlib import Path
import subprocess

from live_oritech_pipes import Probe, GEN, FURNACE, CORE, FUEL_CHEST, RAW_CHEST, FUEL_MODULE, RAW_MODULE, OUT_MODULE, OUT_CHEST, COAL
from reference_pretty_pipes import sprint
from install_isolated_server import verify

QUARTZ = 'minecraft:quartz'
DUST = 'oritech:quartz_dust'


class PulverizerPipes(Probe):
    def snapshot(self):
        return {'quartz_source': self.items(RAW_CHEST)[QUARTZ], 'coal_source': self.items(FUEL_CHEST)[COAL],
                'generator_coal': self.items(GEN)[COAL], 'pulverizer_quartz': self.items(FURNACE)[QUARTZ],
                'pulverizer_dust': self.items(FURNACE)[DUST], 'output_chest': self.items(OUT_CHEST)[DUST],
                'output_in_flight': self.items(OUT_MODULE)[DUST],
                'generator_energy': self.number(GEN, 'energy'), 'pulverizer_energy': self.number(FURNACE, 'energy'),
                'generator_progress': self.number(GEN, '"oritech.machine_progress"'),
                'pulverizer_progress': self.number(FURNACE, '"oritech.machine_progress"')}

    def setup(self):
        self.command('fill 126 198 170 148 203 182 minecraft:air')
        self.setblock(GEN, 'oritech:basic_generator_block')
        self.setblock(FURNACE, 'oritech:pulverizer_block')
        assert 'Test passed' in self.command(f'execute if block {CORE} minecraft:air')
        for pos in (FUEL_CHEST, RAW_CHEST, OUT_CHEST): self.setblock(pos, 'minecraft:chest')
        pipes = [(x,200,172) for x in range(129,137)] + [(136,200,z) for z in range(173,176)]
        pipes += [(x,200,180) for x in range(129,138)] + [(137,200,z) for z in range(177,180)]
        pipes += [(x,200,176) for x in range(138,146)]
        for pos in pipes: self.setblock(' '.join(map(str,pos)), 'prettypipes:pipe')
        self.input(RAW_CHEST, QUARTZ, 2)
        self.input(FUEL_CHEST, COAL, 1)

    def prepare(self):
        self.setup()
        sprint(self,200)
        baseline = self.snapshot()
        assert baseline['quartz_source']==2 and baseline['coal_source']==1, baseline
        assert all(baseline[key]==0 for key in baseline if key not in ('quartz_source','coal_source')), baseline
        self.module(FUEL_MODULE); self.module(RAW_MODULE)
        sprint(self,2400)
        produced=self.snapshot()
        expected={key:0 for key in produced}
        expected.update(pulverizer_dust=2,generator_energy=19800,pulverizer_energy=25000)
        assert produced==expected, (produced,expected)
        self.module(OUT_MODULE)
        sprint(self,10)
        pending=self.snapshot()
        expected.update(pulverizer_dust=0,output_in_flight=2)
        assert pending==expected, (pending,expected)
        return {'without_modules':baseline,'automatically_processed':produced,'saved_in_flight':pending}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',choices=('prepare','verify','final'),required=True)
    parser.add_argument('--prior',type=Path)
    args=parser.parse_args()
    assert not args.output.exists() and not args.output.with_suffix('.commands.json').exists()
    lock=verify(args.server_dir)
    assert lock['modules']['oritech']['version']=='0.3.0' and lock['modules']['prettypipes']['version']=='0.7.0'
    if args.phase!='prepare' and args.prior is None: parser.error('verify/final need the previous report')
    probe=PulverizerPipes(args.server_dir,Path(lock['server_binary']))
    try:
        probe.load()
        if args.phase=='prepare': checks=probe.prepare()
        else:
            prior=json.loads(args.prior.read_text())
            assert prior['phase']==('prepare' if args.phase=='verify' else 'verify')
            reopened=probe.snapshot()
            expected=prior['checks']['saved_in_flight' if args.phase=='verify' else 'delivered']
            assert reopened==expected,(reopened,expected)
            if args.phase=='verify':
                sprint(probe,400);delivered=probe.snapshot()
                expected=dict(expected,pulverizer_dust=0,output_in_flight=0,output_chest=2)
                assert delivered==expected,(delivered,expected)
                checks={'immediately_after_reopen':reopened,'delivered':delivered}
            else: checks={'physically_reopened_final':reopened}
        assert 'Saved the game' in probe.command('save-all flush')
    finally:
        try: subprocess.run([str(probe.binary),'--dir',str(probe.server),'stop'],check=True,capture_output=True,text=True,timeout=90)
        finally: args.output.with_suffix('.commands.json').write_text(json.dumps(probe.rows,indent=2)+'\n')
    report={'schema':1,'phase':args.phase,'checks':checks,'minecraft':'26.3',
            'content_versions':{name:lock['modules'][name]['version'] for name in ('oritech','prettypipes')},
            'machine_pipe_module_chest_and_source_quartz_coal_fixtures':True,
            'machine_inventory_energy_progress_output_or_cargo_injected':False,
            'pulverizer_core_required':False,'server_stopped':True,'licensed_join_tested':False,'published':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Pulverizer/Pretty Pipes',args.phase,'passed',flush=True)


if __name__=='__main__':main()

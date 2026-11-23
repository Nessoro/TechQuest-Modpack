#!/usr/bin/env python3
"""Dedicated Pretty Pipes input -> cabled core-powered smelting -> output/restarts.

Machines, linked core, cables, chests, pipes/modules and source coal/raw iron are
fixtures. No machine inventory, energy, output or transport cargo is seeded.
Start the server before each phase; every phase stops it.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from live_oritech_pipes import Probe
from install_isolated_server import verify
from reference_pretty_pipes import sprint

GEN='143 201 176'
FURNACE='149 200 176'
CORE='149 201 176'
FUEL='135 201 176'
RAW='149 200 184'
OUTPUT='136 199 176'
SOURCE_ENDPOINT='144 201 176'
FAR_ENDPOINT='148 201 176'
FUEL_MODULE='136 201 176'
RAW_MODULE='149 200 183'
OUTPUT_MODULE='149 199 176'
COAL='minecraft:coal'
RAW_IRON='minecraft:raw_iron'
IRON='minecraft:iron_ingot'
WIRES=[f'{x} 201 176' for x in range(144,149)]
PIPES=([f'{x} 201 176' for x in range(136,143)]
       +[f'149 200 {z}' for z in range(177,184)]
       +[f'{x} 199 176' for x in range(137,150)])


class Factory(Probe):
    waterlogged_cables=False
    def load(self):
        self.command('tick freeze');self.command('forceload add 128 160 159 191')
        deadline=time.monotonic()+45
        for pos in ('128 200 160','128 200 176','144 200 160','144 200 176'):
            while 'Test passed' not in self.command('execute if loaded '+pos):
                assert time.monotonic()<deadline,('fixture chunk not loaded',pos)
                time.sleep(.1)

    def snapshot(self):
        cargo={item:sum(self.items(pos)[item] for pos in PIPES) for item in (COAL,RAW_IRON,IRON)}
        result={'fuel_source':dict(self.items(FUEL)),'raw_source':dict(self.items(RAW)),
                'generator':dict(self.items(GEN)),'furnace':dict(self.items(FURNACE)),
                'output':dict(self.items(OUTPUT)),'cargo':cargo,
                'energy':{pos:self.number(pos,'energy') for pos in (GEN,FURNACE,SOURCE_ENDPOINT,FAR_ENDPOINT)},
                'progress':{pos:self.number(pos,'"oritech.machine_progress"') for pos in (GEN,FURNACE)},
                'assembled':self.number(FURNACE,'techquest_assembled'),'core_used':self.number(CORE,'techquest_core_used'),
                **({'all_cables_wet':all('Test passed' in self.command('execute if block '+pos+' oritech:energy_pipe'+('_connection' if pos in (SOURCE_ENDPOINT,FAR_ENDPOINT) else '')+'[waterlogged=true]') for pos in WIRES)} if self.waterlogged_cables else {})}
        if self.waterlogged_cables:assert result['all_cables_wet'],result
        return result

    def source(self,pos,item,count):
        assert pos in (FUEL,RAW)
        nbt='{Items:[{Slot:0b,id:"'+item+'",count:'+str(count)+'}]}'
        assert 'Modified block data' in self.command('data merge block '+pos+' '+nbt)

    def output_module(self):
        nbt='{modules:{Size:3,Items:[{Slot:0b,id:"prettypipes:high_extraction_module",count:1,components:{"prettypipes:direction_selector_data":{direction:"up"}}}]}}'
        assert 'Modified block data' in self.command('data merge block '+OUTPUT_MODULE+' '+nbt)

    def setup(self):
        self.command('fill 133 198 172 151 203 186 minecraft:air');self.command('kill @e[type=minecraft:item]')
        self.setblock(GEN,'oritech:basic_generator_block')
        self.setblock(FURNACE,'oritech:powered_furnace_block{techquest_assembled:1b}')
        self.setblock(CORE,'oritech:machine_core_1{techquest_core_used:1b,controller_x:0,controller_y:-1,controller_z:0}')
        if self.waterlogged_cables:
            # Explicit glass trough fixture isolates this test from Pretty
            # Pipes' still-unported fluid interaction outside the cable line.
            for x in range(144,149):
                for y,z in ((200,176),(201,175),(201,177)):
                    self.setblock(f'{x} {y} {z}','minecraft:glass')
        for pos in WIRES:self.setblock(pos,'oritech:energy_pipe'+('[waterlogged=true]' if self.waterlogged_cables else ''))
        for pos in (FUEL,RAW,OUTPUT):self.setblock(pos,'minecraft:chest')
        for pos in PIPES:self.setblock(pos,'prettypipes:pipe')
        self.source(FUEL,COAL,1);self.source(RAW,RAW_IRON,2)
        for pos in (SOURCE_ENDPOINT,FAR_ENDPOINT):
            assert 'Test passed' in self.command('execute if block '+pos+' oritech:energy_pipe_connection')
        for pos in WIRES[1:-1]:
            assert 'Test passed' in self.command('execute if block '+pos+' oritech:energy_pipe')
            assert 'not a block entity' in self.command('data get block '+pos).lower()

    def prepare(self):
        self.setup();sprint(self,200);baseline=self.snapshot()
        assert baseline['fuel_source']=={COAL:1} and baseline['raw_source']=={RAW_IRON:2},baseline
        assert not baseline['generator'] and not baseline['furnace'] and not any(baseline['cargo'].values()),baseline
        assert sum(baseline['energy'].values())==0,baseline
        for pos in (FUEL_MODULE,RAW_MODULE):self.module(pos)
        sprint(self,5000);processed=self.snapshot()
        assert not processed['fuel_source'] and not processed['raw_source'] and not processed['generator'],processed
        assert processed['furnace']=={IRON:2} and not processed['output'] and not any(processed['cargo'].values()),processed
        assert sum(processed['energy'].values())==51200-6400,processed
        assert processed['energy'][SOURCE_ENDPOINT]==10000 and processed['energy'][FAR_ENDPOINT]==0,processed
        assert not any(processed['progress'].values()) and processed['assembled']==processed['core_used']==1,processed
        self.output_module();sprint(self,10);pending=self.snapshot()
        assert not pending['furnace'] and pending['cargo'][IRON]==2 and not pending['output'],pending
        assert pending['energy']==processed['energy'],pending
        return {'without_extractors':baseline,'automatically_processed':processed,'saved_in_flight':pending}

    def finish(self,prior):
        reopened=self.snapshot();saved=prior['checks']['saved_in_flight']
        for key in saved.keys()-{'cargo','output'}:assert reopened[key]==saved[key],(key,reopened,saved)
        assert reopened['cargo'][IRON]+reopened['output'].get(IRON,0)==2,reopened
        assert reopened['cargo'][COAL]==reopened['cargo'][RAW_IRON]==0,reopened
        sprint(self,1200);final=self.snapshot()
        assert final['output']=={IRON:2} and not any(final['cargo'].values()) and not final['furnace'],final
        assert final['energy']==saved['energy'] and final['assembled']==final['core_used']==1,final
        return {'immediately_after_reopen':reopened,'final':final}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('server-dir','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--phase',choices=('prepare','verify','final'),required=True)
    parser.add_argument('--prior',type=Path)
    parser.add_argument('--waterlogged-cables',action='store_true')
    args=parser.parse_args();assert not args.output.exists() and not args.output.with_suffix('.commands.json').exists()
    lock=verify(args.server_dir);assert lock['modules']['oritech']['version'] in ('0.6.0','0.7.0','0.8.0')
    if args.waterlogged_cables:assert lock['modules']['oritech']['version']=='0.8.0'
    if args.phase!='prepare' and args.prior is None:parser.error('prior phase report required')
    probe=Factory(args.server_dir,Path(lock['server_binary']))
    probe.waterlogged_cables=args.waterlogged_cables
    try:
        probe.load()
        if args.phase=='prepare':checks=probe.prepare()
        else:
            prior=json.loads(args.prior.read_text());assert prior['phase']==('prepare' if args.phase=='verify' else 'verify')
            assert prior.get('waterlogged_cables',False)==args.waterlogged_cables
            if args.phase=='verify':checks=probe.finish(prior)
            else:
                final=probe.snapshot();assert final==prior['checks']['final'],(final,prior)
                checks={'final':final}
        assert 'Saved the game' in probe.command('save-all flush')
    finally:
        try:subprocess.run([str(probe.binary),'--dir',str(probe.server),'stop'],check=True,capture_output=True,text=True,timeout=90)
        finally:args.output.with_suffix('.commands.json').write_text(json.dumps(probe.rows,indent=2)+'\n')
    report={'schema':1,'phase':args.phase,'checks':checks,'oritech_content_version':lock['modules']['oritech']['version'],
            'waterlogged_cables':args.waterlogged_cables,'glass_trough_fixture':args.waterlogged_cables,
            'oritech_native_version':next(m['version'] for m in lock['native_modules'] if m['id']=='techquest_oritech'),
            'pretty_pipes_version':'0.10.0','generator_and_source_interface_cross_chunk_boundary':True,
            'energy_enters_furnace_through_assembled_core':True,'fixture_source_inputs':{COAL:1,RAW_IRON:2},
            'energy_machine_inventory_outputs_or_cargo_seeded':False,'normal_startup_ticks_may_deliver_cargo_before_console_freeze':True,
            'licensed_join_or_multiplayer_tested':False,'server_stopped':True,'published':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Dedicated energy cables',args.phase,'passed',flush=True)


if __name__=='__main__':main()

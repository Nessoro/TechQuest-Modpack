#!/usr/bin/env python3
"""Dedicated redstone routing, transit and already-routed delivery with restarts.

Chests, pipes/modules, power blocks and two source iron stacks are fixtures.
No transport cargo is seeded. Start the server before each of the three phases.
"""
import argparse
import json
from pathlib import Path
import subprocess

from live_oritech_pipes import Probe
from reference_pretty_pipes import sprint
from install_isolated_server import verify

SOURCE='128 200 176';FIRST='129 200 176';MID='130 200 176';END='131 200 176';OUTPUT='132 200 176';SIDE='130 200 175'
POWER={FIRST:'129 199 176',MID:'130 199 176',END:'131 199 176'}
IRON='minecraft:iron_ingot';RED='prettypipes:redstone_module';HIGH='prettypipes:high_extraction_module'


class Redstone(Probe):
    def source(self):
        assert 'Modified block data' in self.command('data merge block '+SOURCE+' {Items:[{Slot:0b,id:"minecraft:iron_ingot",count:8}]}')
        assert self.items(SOURCE)[IRON]==8

    def modules(self,pos,ids):
        values=','.join('{Slot:'+str(i)+'b,id:"'+item+'",count:1}' for i,item in enumerate(ids))
        assert 'Modified block data' in self.command('data merge block '+pos+' {modules:{Size:3,Items:['+values+']}}')

    def power(self,pos,on):self.setblock(POWER[pos],'minecraft:redstone_block' if on else 'minecraft:air')

    def snapshot(self):
        return {'source':self.items(SOURCE)[IRON],'destination':self.items(OUTPUT)[IRON],'side_destination':self.items(SIDE)[IRON],
                'cargo':sum(self.items(pos)[IRON] for pos in (FIRST,MID,END)),
                'redstone_modules':sum(self.items(pos)[RED] for pos in (FIRST,MID,END)),
                'extractors':sum(self.items(pos)[HIGH] for pos in (FIRST,MID,END)),
                'powered':{pos:'Test passed' in self.command('execute if block '+POWER[pos]+' minecraft:redstone_block') for pos in (FIRST,MID,END)}}

    def prepare(self):
        self.command('fill 126 198 172 134 202 180 minecraft:air')
        for pos in (SOURCE,OUTPUT,SIDE):self.setblock(pos,'minecraft:chest')
        for pos in (FIRST,MID,END):self.setblock(pos,'prettypipes:pipe')
        self.modules(FIRST,[HIGH,RED]);self.modules(MID,[RED]);self.modules(END,[RED])
        return self.prepare_flow()

    def prepare_flow(self):
        self.source()
        for pos in (FIRST,MID,END):self.power(pos,True)
        sprint(self,200);blocked_source=self.snapshot()
        assert blocked_source['source']==8 and blocked_source['destination']==blocked_source['side_destination']==blocked_source['cargo']==0,blocked_source
        self.power(FIRST,False)
        sprint(self,200);blocked_destination=self.snapshot()
        assert blocked_destination['source']==8 and blocked_destination['destination']==blocked_destination['side_destination']==blocked_destination['cargo']==0,blocked_destination
        self.power(END,False)
        sprint(self,10);routed=self.snapshot()
        assert routed['source']==routed['destination']==routed['side_destination']==0 and routed['cargo']==8,routed
        # Re-power after a genuine route was chosen: original store does not
        # re-run canWork. The intermediate pipe stays powered throughout.
        self.power(FIRST,True);self.power(END,True)
        pending=self.snapshot()
        assert pending['cargo']==8 and pending['redstone_modules']==3 and pending['extractors']==1,pending
        return {'powered_source_blocks_extraction':blocked_source,'powered_destinations_block_new_route':blocked_destination,'powered_intermediate_allows_transit':routed,'saved_in_flight_with_source_and_destination_powered':pending}

    def finish(self,prior):
        reopened=self.snapshot();assert reopened==prior['checks']['saved_in_flight_with_source_and_destination_powered']
        sprint(self,400);delivered=self.snapshot()
        assert delivered['source']==delivered['cargo']==delivered['side_destination']==0 and delivered['destination']==8,delivered
        self.source();self.power(FIRST,False)
        sprint(self,200);new_blocked=self.snapshot()
        assert new_blocked['source']==8 and new_blocked['destination']==8 and new_blocked['cargo']==new_blocked['side_destination']==0,new_blocked
        self.power(END,False);sprint(self,400);second=self.snapshot()
        assert second['source']==second['cargo']==second['side_destination']==0 and second['destination']==16,second
        assert second['redstone_modules']==3 and second['extractors']==1,second
        return {'immediately_after_reopen':reopened,'already_routed_delivery_ignores_power':delivered,'new_route_still_blocked_while_powered':new_blocked,'final':second}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',choices=('prepare','verify','final'),required=True);parser.add_argument('--prior',type=Path)
    args=parser.parse_args();assert not args.output.exists() and not args.output.with_suffix('.commands.json').exists()
    lock=verify(args.server_dir);assert lock['modules']['prettypipes']['version']=='0.8.0'
    if args.phase!='prepare' and args.prior is None:parser.error('previous phase report required')
    probe=Redstone(args.server_dir,Path(lock['server_binary']))
    try:
        probe.load()
        if args.phase=='prepare':checks=probe.prepare()
        else:
            prior=json.loads(args.prior.read_text());assert prior['phase']==('prepare' if args.phase=='verify' else 'verify')
            if args.phase=='verify':checks=probe.finish(prior)
            else:
                final=probe.snapshot();assert final==prior['checks']['final'],(final,prior['checks']['final']);checks={'final':final}
        assert 'Saved the game' in probe.command('save-all flush')
    finally:
        try:subprocess.run([str(probe.binary),'--dir',str(probe.server),'stop'],check=True,capture_output=True,text=True,timeout=90)
        finally:args.output.with_suffix('.commands.json').write_text(json.dumps(probe.rows,indent=2)+'\n')
    args.output.write_text(json.dumps({'schema':1,'phase':args.phase,'checks':checks,'pretty_pipes_content_and_native':'0.8.0',
                                      'source_iron_chests_modules_pipes_and_power_fixtures':True,'transport_cargo_seeded':False,
                                      'server_stopped':True,'licensed_join_tested':False,'published':False},indent=2)+'\n')
    print('Dedicated redstone',args.phase,'passed',flush=True)


if __name__=='__main__':main()

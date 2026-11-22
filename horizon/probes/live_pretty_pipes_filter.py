#!/usr/bin/env python3
"""Exercise ghost filters and direction routing through a real local graphical client.

Requires X11 and graphics driver; copies only content into a fresh scratch world.
No account login, real player profile or dedicated-server join is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from graphical_fixture import GraphicalFixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    game = GraphicalFixture(args.server_dir,args.work,("0.4.0","0.5.0","0.6.0","0.7.0","0.8.0","0.9.0"),"techquest-pipe-filter","TQFilterProbe")
    call, command, settle = game.call, game.command, game.settle
    def items(x):
        text = command(f"data get block {x} 200 0 Items")
        assert "has the following block data:" in text, text
        counts = {}
        for match in re.finditer(r'\{(?=[^{}]*\bcount:\s*(\d+))(?=[^{}]*\bid:\s*"([^"]+)")[^{}]*\}',text):
            counts[match[2]] = counts.get(match[2],0)+int(match[1])
        return counts
    def inv(): return call("inventory")["counts"]
    def gui():
        screen = call("screen")
        assert screen["screen"] == "container", screen
        assert {s['slot'] for s in screen['slots'] if 300<=s['slot']<500} == {300,301,302}
        return screen
    def point(x,y):
        status = call("status"); w,h=status["renderer"]["size"]
        return (w//2-176)//2+x,(h//2-203)//2+y
    def click(x,y): call("click-at",*point(x,y));settle()
    def modules():
        text = command("data get block 1 200 0 modules")
        assert "has the following block data:" in text
        return text
    def filter_sample(slot):
        call("click-slot",slot);settle();click(70,86);call("click-slot",slot);settle()
    try:
        game.start("prepare")
        command("fill -3 199 -3 6 199 5 minecraft:stone")
        for x in (0,4): command(f"setblock {x} 200 0 minecraft:chest")
        for x in (1,2,3):command(f"setblock {x} 200 0 prettypipes:pipe")
        command("tp @s 0.5 200 3.5");call("wait-ready",timeout=180)
        command("gamemode survival");command("clear @s")
        command("tick freeze")
        command("give @s prettypipes:low_extraction_module 1")
        command("give @s minecraft:iron_ingot 64");command("give @s minecraft:gold_ingot 8")
        call("select",1);settle();call("interact",1,200,0);settle()
        assert inv() == {"minecraft:iron_ingot":64,"minecraft:gold_ingot":8}
        call("interact",1,200,0);settle();gui()
        filter_sample(1)
        text=modules();assert 'prettypipes:item_filter_data' in text and 'whitelist: 0b' in text and 'id: "minecraft:iron_ingot"' in text
        assert inv() == {"minecraft:iron_ingot":64,"minecraft:gold_ingot":8}
        call("screenshot",game.work/"blacklist.png")
        command("item replace block 0 200 0 container.0 with minecraft:iron_ingot 3")
        command("item replace block 0 200 0 container.1 with minecraft:gold_ingot 3")
        command("tick unfreeze");call("wait",220)
        assert items(0)=={"minecraft:iron_ingot":3}
        assert items(4)=={"minecraft:gold_ingot":3}
        command("tick freeze");click(155,104)
        assert 'whitelist: 1b' in modules()
        command("tick unfreeze");call("wait",220)
        assert items(0)=={} and items(4)=={"minecraft:gold_ingot":3,"minecraft:iron_ingot":3}
        command("tick freeze")
        # One directional pipe can use the other side as a destination.
        command("setblock 2 200 0 minecraft:chest")
        command("setblock 3 200 0 minecraft:air")
        click(50,104)
        assert 'direction: "west"' in modules()
        command("item replace block 0 200 0 container.0 with minecraft:iron_ingot 3")
        command("item replace block 2 200 0 container.0 with minecraft:gold_ingot 3")
        command("tick unfreeze");call("wait",160)
        assert items(0)=={} and items(2)=={"minecraft:iron_ingot":3,"minecraft:gold_ingot":3}
        command("tick freeze");click(50,104)
        assert 'direction: "east"' in modules()
        filter_sample(2)
        text=modules();assert 'id: "minecraft:gold_ingot"' in text and 'id: "minecraft:iron_ingot"' not in text
        command("tick unfreeze");call("wait",160)
        assert items(0)=={"minecraft:gold_ingot":3} and items(2)=={"minecraft:iron_ingot":3}
        command("tick freeze")
        call("screenshot",game.work/"whitelist-east.png")
        saved=modules();assert inv()=={"minecraft:iron_ingot":64,"minecraft:gold_ingot":8}
        call("close");settle();call("save")
        print('prepare: sample edits, allow/deny and single-pipe west/east routing passed',flush=True)
    finally: game.stop()
    try:
        game.start("reopen")
        call("interact",1,200,0);settle();gui()
        assert modules()==saved
        assert inv()=={"minecraft:iron_ingot":64,"minecraft:gold_ingot":8}
        assert items(0)=={"minecraft:gold_ingot":3} and items(2)=={"minecraft:iron_ingot":3}
        call("screenshot",game.work/"reopened.png")
        call("click-slot",300,"shift");settle()
        inventory=call("inventory")
        assert inventory['counts']['prettypipes:low_extraction_module']==1
        slot=next(s['slot'] for s in inventory['hotbar']+inventory['main'] if s.get('item')=='prettypipes:low_extraction_module')
        call("click-slot",slot,"shift");settle();assert modules()==saved
        status=call("status");assert status['server']['decode_errors']==0 and status['server']['joined']
        call("close");call("save")
        report={"schema":1,"minecraft":"26.3","prototype_version":game.version,
                "connected_local_graphical_client":True,"ghost_sample_edits_via_menu_button_packet":True,
                "cursor_and_inventory_counts_preserved":True,"blacklist_blocks_only_sample_item":True,
                "whitelist_allows_only_sample_item":True,"single_pipe_west_to_east_route":True,
                "single_pipe_east_to_west_route":True,"extraction_side_excluded_as_destination":True,
                "sample_replaced_without_duplication":True,"settings_persist_after_restart":True,
                "settings_persist_after_module_remove_reinstall":True,"own_module_slots":3,"hidden_queue_slots":64,
                "protocol_decode_errors":0,"renderer":status['renderer']['backend'],
                "device_type":status['renderer']['device_type'],"licensed_account_or_dedicated_join_tested":False,
                "full_pretty_pipes_ported":False,"published":False}
    finally: game.stop()
    report['screenshots_sha256']={n:hashlib.sha256((game.work/n).read_bytes()).hexdigest() for n in ('blacklist.png','whitelist-east.png','reopened.png')}
    (game.work/'checked-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('graphical filter and direction tests passed')


if __name__=='__main__':main()

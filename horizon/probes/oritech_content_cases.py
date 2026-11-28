#!/usr/bin/env python3
"""Generate original public recipe inputs and selected block loot for an oracle."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from stage_oritech_progression import ORES
from stage_terralith_content import read_checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("jar", "stage-report", "output"): parser.add_argument("--"+name, type=Path, required=True)
    args = parser.parse_args(); raw = read_checked(args.jar); stage = json.loads(read_checked(args.stage_report))
    assert hashlib.sha512(raw).hexdigest() == stage["source_jar_sha512"]
    tags = stage["progression_subset"]["resolved_common_tags"]; cases = []
    with zipfile.ZipFile(args.jar) as z:
        for name in stage["progression_subset"]["recipes"]:
            recipe = json.loads(z.read(f"data/oritech/recipe/{name}.json"))
            if recipe["type"] != "minecraft:crafting_shaped": continue
            symbols = sorted(recipe["key"]); choices = []
            for symbol in symbols:
                ingredient = recipe["key"][symbol]
                if "item" in ingredient: choices.append([ingredient["item"]])
                elif ingredient["tag"] == "minecraft:planks": choices.append(["minecraft:oak_planks", "minecraft:spruce_planks", "minecraft:birch_planks"])
                elif ingredient["tag"] == "minecraft:coals": choices.append(["minecraft:coal", "minecraft:charcoal"])
                elif ingredient["tag"] == "minecraft:sand": choices.append(["minecraft:sand", "minecraft:red_sand"])
                else: choices.append(tags[ingredient["tag"]])
            # ShapedRecipePattern shrinks empty borders, including energy's
            # entirely blank first row. Exercise every legal translated row.
            raw_pattern = recipe["pattern"]
            occupied = [(x,y) for y,row in enumerate(raw_pattern) for x,symbol in enumerate(row) if symbol != " "]
            assert occupied, name
            left,right=min(x for x,y in occupied),max(x for x,y in occupied)
            top,bottom=min(y for x,y in occupied),max(y for x,y in occupied)
            pattern=[row[left:right+1] for row in raw_pattern[top:bottom+1]]
            width,height=right-left+1,bottom-top+1
            for picked in itertools.product(*choices):
                ingredients = dict(zip(symbols,picked))
                for mirror in (False,True):
                    for ox in range(4-width):
                        for oy in range(4-height):
                            grid = [None]*9
                            for y,row in enumerate(pattern):
                                for x,symbol in enumerate(row[:width]):
                                    if symbol != " ": grid[(oy+y)*3+ox+(width-1-x if mirror else x)] = ingredients[symbol]
                            title=f"{name}:{len(cases)}"
                            base={"recipe":"oritech:"+name,"item":recipe["result"]["id"],"count":recipe["result"].get("count",1)}
                            cases.append({**base,"name":title,"valid":True,"grid":grid})
                            for slot,value in enumerate(grid):
                                if value is None: continue
                                for kind,replacement in (("missing",None),("wrong","minecraft:dirt")):
                                    changed=grid.copy();changed[slot]=replacement
                                    cases.append({**base,"name":f"{title}:{slot}:{kind}","valid":False,"grid":changed})
        loot={block:json.loads(z.read(f"data/oritech/loot_table/blocks/{block}.json"))
              for block in (*ORES,*stage.get("energy_pipe_blocks",[]))}
    result={"schema":1,"source_jar_sha512":stage["source_jar_sha512"],"crafting":cases,"loot_tables":loot,"seeds":[1,2,42,263,9001]}
    with args.output.open("x") as f: json.dump(result,f,indent=2);f.write("\n")
    print("Generated",len(cases),"crafting cases and",len(loot)*3*len(result["seeds"]),"block loot rolls")


if __name__ == "__main__": main()

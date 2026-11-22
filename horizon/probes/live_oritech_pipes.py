#!/usr/bin/env python3
"""Dedicated Oritech/Pretty Pipes composition with explicit synthetic fixtures.

Machines/core, chests, pipes/modules and source raw iron/coal are fixtures.
Machine fuel/input, processing output, energy and transport cargo are not
injected. Every phase stops the server; start it separately before the next.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import time

from live_pretty_pipes import Native
from reference_pretty_pipes import sprint
from install_isolated_server import verify

GEN = "136 200 176"
FURNACE = "137 200 176"
CORE = "137 201 176"
FUEL_CHEST = "128 200 172"
RAW_CHEST = "128 200 180"
FUEL_MODULE = "129 200 172"
RAW_MODULE = "129 200 180"
OUT_MODULE = "138 200 176"
OUT_CHEST = "146 200 176"
BLOCKED_BARREL = "145 200 176"
IRON = "minecraft:iron_ingot"
RAW = "minecraft:raw_iron"
COAL = "minecraft:coal"


class Probe(Native):
    def __init__(self, server, binary):
        super().__init__(server, binary)
        self.rows = []

    def command(self, line):
        reply = super().command(line)
        self.rows.append({"command": line, "reply": reply})
        return reply

    def number(self, pos, key):
        reply = self.command(f"data get block {pos} {key}")
        match = re.search(r"has the following block data:\s*(-?\d+)", reply)
        assert match, (pos, key, reply)
        return int(match[1])

    def items(self, pos):
        reply = self.command(f"data get block {pos} Items")
        if "Found no elements matching Items" in reply:
            return Counter()
        assert f"{pos.replace(' ', ', ')} has the following block data:" in reply, reply
        ids = re.findall(r'id: "([a-z0-9_:/.\-]+)"', reply)
        counts = list(map(int, re.findall(r'\bcount: (\d+)', reply)))
        assert len(ids) == len(counts), reply
        assert ids or reply.rstrip().endswith("[]"), reply
        result = Counter()
        for item, count in zip(ids, counts):
            result[item] += count
        return result

    def setblock(self, pos, block):
        reply = self.command(f"setblock {pos} {block}")
        assert "Changed the block" in reply, (pos, block, reply)

    def module(self, pos):
        nbt = '{modules:{Size:3,Items:[{Slot:0b,id:"prettypipes:high_extraction_module",count:1}]}}'
        assert "Modified block data" in self.command(f"data merge block {pos} {nbt}")

    def input(self, pos, item, count):
        assert pos in (RAW_CHEST, FUEL_CHEST), "source inventory fixtures only"
        nbt = '{Items:[{Slot:0b,id:"' + item + '",count:' + str(count) + '}]}'
        assert "Modified block data" in self.command(f"data merge block {pos} {nbt}")
        assert self.items(pos)[item] == count

    def snapshot(self):
        return {"raw_source": self.items(RAW_CHEST)[RAW], "fuel_source": self.items(FUEL_CHEST)[COAL],
                "generator_coal": self.items(GEN)[COAL], "furnace_raw": self.items(FURNACE)[RAW],
                "furnace_iron": self.items(FURNACE)[IRON], "output_chest": self.items(OUT_CHEST)[IRON],
                "output_in_flight": self.items(OUT_MODULE)[IRON],
                "generator_energy": self.number(GEN, "energy"), "furnace_energy": self.number(FURNACE, "energy"),
                "generator_progress": self.number(GEN, '"oritech.machine_progress"'),
                "furnace_progress": self.number(FURNACE, '"oritech.machine_progress"')}

    def load(self):
        self.command("tick freeze")
        self.command("forceload add 128 160 144 192")
        deadline = time.monotonic() + 45
        while "Test passed" not in self.command(f"execute if loaded {GEN}"):
            assert time.monotonic() < deadline, "fixture chunk not loaded"
            time.sleep(.1)

    def setup(self):
        self.command("fill 126 198 170 148 203 182 minecraft:air")
        self.setblock(GEN, "oritech:basic_generator_block")
        self.setblock(CORE, "oritech:machine_core_1{techquest_core_used:1b,controller_x:0,controller_y:-1,controller_z:0}")
        self.setblock(FURNACE, "oritech:powered_furnace_block{techquest_assembled:1b}")
        for pos in (FUEL_CHEST, RAW_CHEST, OUT_CHEST):
            self.setblock(pos, "minecraft:chest")
        pipes = [(x, 200, 172) for x in range(129, 137)]
        pipes += [(136, 200, z) for z in range(173, 176)]
        pipes += [(x, 200, 180) for x in range(129, 138)]
        pipes += [(137, 200, z) for z in range(177, 180)]
        pipes += [(x, 200, 176) for x in range(138, 146)]
        for pos in pipes:
            self.setblock(" ".join(map(str, pos)), "prettypipes:pipe")
        self.input(RAW_CHEST, RAW, 8)
        self.input(FUEL_CHEST, COAL, 1)

    def prepare(self):
        self.setup()
        sprint(self, 200)
        baseline = self.snapshot()
        assert baseline["raw_source"] == 8 and baseline["fuel_source"] == 1, baseline
        assert baseline["generator_energy"] == baseline["furnace_energy"] == 0, baseline
        assert baseline["furnace_raw"] == baseline["furnace_iron"] == baseline["output_chest"] == 0, baseline
        self.module(FUEL_MODULE)
        self.module(RAW_MODULE)
        sprint(self, 2400)
        produced = self.snapshot()
        assert all(produced[key] == 0 for key in ("raw_source", "fuel_source", "generator_coal", "furnace_raw", "output_chest")), produced
        assert produced["furnace_iron"] == 8 and produced["generator_progress"] == produced["furnace_progress"] == 0, produced
        assert produced["generator_energy"] + produced["furnace_energy"] == 25600, produced
        self.module(OUT_MODULE)
        sprint(self, 10)
        pending = self.snapshot()
        assert pending["furnace_iron"] == pending["output_chest"] == 0 and pending["output_in_flight"] == 8, pending
        return {"without_modules": baseline, "automatically_processed": produced, "saved_in_flight": pending}

    def finish(self):
        reopened = self.snapshot()
        assert reopened["furnace_iron"] + reopened["output_in_flight"] + reopened["output_chest"] == 8, reopened
        sprint(self, 400)
        delivered = self.snapshot()
        assert delivered["output_chest"] == 8 and delivered["output_in_flight"] == delivered["furnace_iron"] == 0, delivered
        # An output extractor must leave the machine's input slot alone.
        self.setblock(CORE, "minecraft:air")
        self.input(RAW_CHEST, RAW, 8)
        sprint(self, 500)
        protected = self.snapshot()
        assert protected["furnace_raw"] == 8 and protected["output_chest"] == 8, protected
        assert protected["raw_source"] == protected["output_in_flight"] == protected["furnace_iron"] == 0, protected
        # Isolate a full barrel from the original chest, preserving its eight
        # genuine ingots. Only the barrel's stone filler is synthetic.
        self.setblock(BLOCKED_BARREL, "minecraft:barrel")
        filler = ','.join('{Slot:' + str(i) + 'b,id:"minecraft:stone",count:64}' for i in range(27))
        assert "Modified block data" in self.command(f"data merge block {BLOCKED_BARREL} {{Items:[{filler}]}}")
        self.setblock(CORE, "oritech:machine_core_1{techquest_core_used:1b,controller_x:0,controller_y:-1,controller_z:0}")
        assert "Modified block data" in self.command(f"data merge block {FURNACE} {{techquest_assembled:1b}}")
        sprint(self, 1200)
        blocked = self.snapshot()
        assert blocked["furnace_iron"] == 8 and blocked["output_in_flight"] == blocked["furnace_raw"] == 0, blocked
        assert blocked["output_chest"] == 8 and self.items(BLOCKED_BARREL)[IRON] == 0, blocked
        assert blocked["generator_energy"] == blocked["furnace_energy"] == 0, blocked
        assert "Modified block data" in self.command(f"data remove block {BLOCKED_BARREL} Items[{{Slot:0b}}]")
        sprint(self, 400)
        final = self.snapshot()
        barrel = self.items(BLOCKED_BARREL)
        assert final["output_chest"] == barrel[IRON] == 8, (final, barrel)
        assert all(final[key] == 0 for key in ("raw_source", "fuel_source", "generator_coal", "furnace_raw", "furnace_iron", "output_in_flight", "generator_energy", "furnace_energy")), final
        assert barrel["minecraft:stone"] == 26*64, barrel
        return {"immediately_after_reopen": reopened, "first_batch_delivered": delivered,
                "input_not_extracted_without_core": protected, "full_barrel_backpressure": blocked,
                "final": final, "barrel": dict(barrel)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("prepare", "verify", "final"), required=True)
    parser.add_argument("--prior", type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix(".commands.json").exists():
        parser.error("output and commands path must be new")
    lock = verify(args.server_dir)
    assert lock["modules"]["oritech"]["version"] in ("0.2.0", "0.3.0", "0.4.0")
    assert lock["modules"]["prettypipes"]["version"] in ("0.5.0", "0.6.0", "0.7.0", "0.8.0", "0.9.0")
    if args.phase != "prepare" and args.prior is None:
        parser.error("verify/final need the prior phase report")
    probe = Probe(args.server_dir, Path(lock["server_binary"]))
    try:
        probe.load()
        if args.phase == "prepare":
            checks = probe.prepare()
        elif args.phase == "verify":
            prior = json.loads(args.prior.read_text())
            assert prior["phase"] == "prepare" and prior["checks"]["saved_in_flight"]["output_in_flight"] == 8
            checks = probe.finish()
        else:
            prior = json.loads(args.prior.read_text())
            assert prior["phase"] == "verify"
            checks = {"final": probe.snapshot(), "barrel": dict(probe.items(BLOCKED_BARREL))}
            assert checks["final"] == prior["checks"]["final"] and checks["barrel"] == prior["checks"]["barrel"], (checks, prior["checks"])
        assert "Saved the game" in probe.command("save-all flush")
    finally:
        try:
            subprocess.run([str(probe.binary), "--dir", str(probe.server), "stop"], check=True, capture_output=True, text=True, timeout=90)
        finally:
            args.output.with_suffix(".commands.json").write_text(json.dumps(probe.rows, indent=2) + "\n")
    report = {"schema": 1, "phase": args.phase, "checks": checks, "minecraft": "26.3",
              "module_versions": {name: spec["version"] for name, spec in lock["modules"].items()},
              "synthetic_machine_core_pipe_module_and_chest_fixtures": True, "source_raw_iron_and_coal_inventory_fixtures": True,
              "destination_stone_filler_fixture": args.phase == "verify", "machine_inventory_energy_progress_outputs_or_cargo_injected": False,
              "gui_or_licensed_join_tested": False, "full_original_capability_parity_tested": False,
              "server_stopped": True, "full_modpack_ported": False, "published": False}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print("Oritech/Pretty Pipes", args.phase, "checks passed", flush=True)


if __name__ == "__main__":
    main()

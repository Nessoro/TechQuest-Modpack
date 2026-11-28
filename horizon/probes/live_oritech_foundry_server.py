#!/usr/bin/env python3
"""Dedicated coal -> dust -> steel automation with physical server restarts.

Machines, linked cores, pipes/modules, chests and source coal/iron are fixtures.
Machine inventory, energy, processing output and transport cargo are not seeded.
Start the verified isolated server before each phase. Every phase stops it.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from live_oritech_pipes import Probe
from install_isolated_server import verify
from reference_pretty_pipes import sprint

GEN = "143 200 176"
PULV = "143 200 175"
FOUNDRY = "144 200 176"
CORES = ("145 200 176", "144 201 176", "145 201 176")
FUEL = "135 200 176"
COAL_SOURCE = "143 200 166"
IRON_SOURCE = "144 200 184"
OUTPUT = "152 199 176"
FUEL_MODULE = "136 200 176"
COAL_MODULE = "143 200 167"
IRON_MODULE = "144 200 183"
DUST_MODULE = "144 200 175"
OUTPUT_MODULE = "144 199 176"
COAL = "minecraft:coal"
IRON = "minecraft:iron_ingot"
DUST = "oritech:coal_dust"
STEEL = "oritech:steel_ingot"


def positions():
    return ([(x, 200, 176) for x in range(136, 143)]
            + [(143, 200, z) for z in range(167, 175)]
            + [(144, 200, z) for z in range(177, 184)]
            + [(x, 199, 176) for x in range(144, 152)]
            + [(144, 200, 175)])


class Factory(Probe):
    def load(self):
        self.command("tick freeze")
        self.command("forceload add 128 160 159 191")
        deadline = time.monotonic() + 45
        for pos in (FUEL, COAL_SOURCE, IRON_SOURCE, OUTPUT):
            while "Test passed" not in self.command("execute if loaded " + pos):
                assert time.monotonic() < deadline, ("fixture chunk not loaded", pos)
                time.sleep(.1)

    def source(self, pos, item, count):
        assert pos in (FUEL, COAL_SOURCE, IRON_SOURCE)
        nbt = '{Items:[{Slot:0b,id:"' + item + '",count:' + str(count) + '}]}'
        assert "Modified block data" in self.command("data merge block " + pos + " " + nbt)
        assert self.items(pos)[item] == count

    def extraction(self, pos, direction=None):
        component = ',components:{"prettypipes:direction_selector_data":{direction:"' + direction + '"}}' if direction else ''
        nbt = '{modules:{Size:3,Items:[{Slot:0b,id:"prettypipes:high_extraction_module",count:1' + component + '}]}}'
        assert "Modified block data" in self.command("data merge block " + pos + " " + nbt)

    def snapshot(self):
        cargo = [self.items(" ".join(map(str, pos))) for pos in positions()]
        return {"fuel_source": self.items(FUEL)[COAL], "coal_source": self.items(COAL_SOURCE)[COAL],
                "iron_source": self.items(IRON_SOURCE)[IRON], "generator_coal": self.items(GEN)[COAL],
                "pulverizer_coal": self.items(PULV)[COAL], "pulverizer_dust": self.items(PULV)[DUST],
                "foundry_iron": self.items(FOUNDRY)[IRON], "foundry_dust": self.items(FOUNDRY)[DUST],
                "foundry_steel": self.items(FOUNDRY)[STEEL], "output_steel": self.items(OUTPUT)[STEEL],
                "cargo": {item: sum(inventory[item] for inventory in cargo)
                          for item in (COAL, IRON, DUST, STEEL)},
                "energy": {pos: self.number(pos, "energy") for pos in (GEN, PULV, FOUNDRY)},
                "progress": {pos: self.number(pos, '"oritech.machine_progress"') for pos in (GEN, PULV, FOUNDRY)},
                "assembled": self.number(FOUNDRY, "techquest_assembled"),
                "core_used": [self.number(pos, "techquest_core_used") for pos in CORES]}

    def setup(self):
        self.command("fill 133 198 164 154 203 186 minecraft:air")
        self.command("kill @e[type=minecraft:item]")
        self.setblock(GEN, "oritech:basic_generator_block")
        self.setblock(PULV, "oritech:pulverizer_block")
        self.setblock(FOUNDRY, "oritech:foundry_block[facing=north]{techquest_assembled:1b}")
        for pos in CORES:
            offset = [a - b for a, b in zip(map(int, FOUNDRY.split()), map(int, pos.split()))]
            self.setblock(pos, "oritech:machine_core_1{techquest_core_used:1b,controller_x:"
                          + str(offset[0]) + ",controller_y:" + str(offset[1]) + ",controller_z:" + str(offset[2]) + "}")
        for pos in (FUEL, COAL_SOURCE, IRON_SOURCE, OUTPUT):
            self.setblock(pos, "minecraft:chest")
        for pos in positions():
            self.setblock(" ".join(map(str, pos)), "prettypipes:pipe")
        self.source(FUEL, COAL, 1)
        self.source(COAL_SOURCE, COAL, 4)
        self.source(IRON_SOURCE, IRON, 4)

    def prepare(self):
        self.setup()
        sprint(self, 200)
        baseline = self.snapshot()
        assert [baseline[k] for k in ("fuel_source", "coal_source", "iron_source")] == [1, 4, 4], baseline
        assert sum(baseline["energy"].values()) == sum(baseline["cargo"].values()) == 0, baseline
        assert baseline["foundry_steel"] == baseline["output_steel"] == baseline["pulverizer_dust"] == 0, baseline
        for pos in (FUEL_MODULE, COAL_MODULE, IRON_MODULE):
            self.extraction(pos)
        self.extraction(DUST_MODULE, "west")
        sprint(self, 4000)
        produced = self.snapshot()
        assert all(produced[k] == 0 for k in ("fuel_source", "coal_source", "iron_source", "generator_coal", "pulverizer_coal", "pulverizer_dust", "foundry_iron", "foundry_dust", "output_steel")), produced
        assert produced["foundry_steel"] == 4 and not any(produced["cargo"].values()), produced
        assert sum(produced["energy"].values()) == 51200 - 4*100*32 - 4*26*128, produced
        assert not any(produced["progress"].values()) and produced["core_used"] == [1, 1, 1], produced
        self.extraction(OUTPUT_MODULE)
        sprint(self, 10)
        pending = self.snapshot()
        assert pending["foundry_steel"] == pending["output_steel"] == 0 and pending["cargo"][STEEL] == 4, pending
        return {"without_extractors": baseline, "automatically_processed": produced, "saved_in_flight": pending}

    def finish(self, prior):
        reopened = self.snapshot()
        saved = prior["checks"]["saved_in_flight"]
        # A normal dedicated start runs ticks before the first console freeze.
        # Steel may already have arrived; every other field must remain exact.
        for key in saved.keys() - {"output_steel", "cargo"}:
            assert reopened[key] == saved[key], (key, reopened, saved)
        assert reopened["output_steel"] + reopened["cargo"][STEEL] == 4, reopened
        assert all(reopened["cargo"][item] == 0 for item in (COAL, IRON, DUST)), reopened
        sprint(self, 400)
        delivered = self.snapshot()
        assert delivered["output_steel"] == 4 and delivered["foundry_steel"] == 0 and not any(delivered["cargo"].values()), delivered
        assert delivered["energy"] == reopened["energy"], (delivered, reopened)
        # The Foundry has only 88 E left, below a processing tick's 128 E.
        # Make one more genuine dust and leave both inputs in the machine
        # while its output extractor remains enabled. Neither may be stolen.
        self.source(COAL_SOURCE, COAL, 1)
        self.source(IRON_SOURCE, IRON, 1)
        sprint(self, 600)
        protected = self.snapshot()
        assert protected["foundry_iron"] == protected["foundry_dust"] == 1, protected
        assert protected["output_steel"] == 4 and protected["foundry_steel"] == 0 and not any(protected["cargo"].values()), protected
        assert protected["energy"][FOUNDRY] == 88 and protected["progress"][FOUNDRY] == 0, protected
        assert sum(protected["energy"].values()) == 25088 - 100*32, protected
        return {"immediately_after_reopen": reopened, "first_batch_delivered": delivered,
                "both_input_slots_protected_while_energy_starved": protected, "final": protected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("prepare", "verify", "final"), required=True)
    parser.add_argument("--prior", type=Path)
    args = parser.parse_args()
    assert not args.output.exists() and not args.output.with_suffix(".commands.json").exists()
    lock = verify(args.server_dir)
    assert lock["modules"]["oritech"]["version"] == "0.4.0"
    assert lock["modules"]["prettypipes"]["version"] == "0.9.0"
    if args.phase != "prepare" and args.prior is None:
        parser.error("previous phase report required")
    probe = Factory(args.server_dir, Path(lock["server_binary"]))
    try:
        probe.load()
        if args.phase == "prepare":
            checks = probe.prepare()
        else:
            prior = json.loads(args.prior.read_text())
            assert prior["phase"] == ("prepare" if args.phase == "verify" else "verify")
            if args.phase == "verify":
                checks = probe.finish(prior)
            else:
                final = probe.snapshot()
                assert final == prior["checks"]["final"], (final, prior)
                checks = {"final": final}
        assert "Saved the game" in probe.command("save-all flush")
    finally:
        try:
            subprocess.run([str(probe.binary), "--dir", str(probe.server), "stop"], check=True,
                           capture_output=True, text=True, timeout=90)
        finally:
            args.output.with_suffix(".commands.json").write_text(json.dumps(probe.rows, indent=2) + "\n")
    args.output.write_text(json.dumps({"schema": 1, "phase": args.phase, "checks": checks,
                                      "oritech_content_version": "0.4.0", "oritech_native_version": "0.3.0", "pretty_pipes_version": "0.9.0",
                                      "machine_linked_cores_chests_pipes_modules_and_source_inventory_fixtures": True,
                                      "machine_inventory_energy_progress_outputs_or_cargo_injected": False,
                                      "normal_startup_ticks_can_advance_before_console_freeze": True,
                                      "gui_or_licensed_join_tested": False, "server_stopped": True, "published": False}, indent=2) + "\n")
    print("Dedicated Foundry", args.phase, "passed", flush=True)


if __name__ == "__main__":
    main()

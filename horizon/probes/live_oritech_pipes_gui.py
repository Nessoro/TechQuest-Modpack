#!/usr/bin/env python3
"""Real graphical client installs extractors and observes the automated chain.

Machine/source-inventory fixtures are shared with the dedicated probe. Extraction
modules enter through ordinary player interaction, and each phase is physically
saved/reopened. No queue entries, machine energy or processing output are seeded.
"""
import argparse
import json
from pathlib import Path
import shutil

from graphical_fixture import GraphicalFixture
from live_oritech_pipes import Probe, FUEL_MODULE, RAW_MODULE, OUT_MODULE, BLOCKED_BARREL


class LocalProbe(Probe):
    def __init__(self, game):
        self.game = game
        self.rows = []
        self.installs = []

    def command(self, line):
        reply = self.game.command(line)
        self.rows.append({"command": line, "reply": reply})
        return reply

    def setup(self):
        super().setup()
        self.command("fill 126 199 170 148 199 184 minecraft:glass")
        self.command("tp @s 140.5 200 179.5")
        self.command("gamemode survival")

    def module(self, pos):
        positions = {FUEL_MODULE: (129.5, 200, 175.5), RAW_MODULE: (129.5, 200, 177.5), OUT_MODULE: (138.5, 200, 179.5)}
        self.command("tp @s " + " ".join(map(str, positions[pos])))
        self.command("give @s prettypipes:high_extraction_module 1")
        call = self.game.call
        call("select", "prettypipes:high_extraction_module")
        self.game.settle()
        xyz = tuple(map(int, pos.split()))
        call("interact", *xyz)
        self.game.settle()
        assert call("inventory")["counts"].get("prettypipes:high_extraction_module", 0) == 0
        assert "prettypipes:high_extraction_module" in self.command(f"data get block {pos} modules")
        call("interact", *xyz)
        self.game.settle()
        screen = call("screen")
        assert screen["screen"] == "container", screen
        assert {s["slot"] for s in screen["slots"] if 300 <= s["slot"] < 500} == {300, 301, 302}, screen
        call("screenshot", self.game.work / ("module-" + pos.replace(" ", "-") + ".png"))
        call("close")
        self.game.settle()
        self.installs.append(pos)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("server-dir", "work"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    game = GraphicalFixture(args.server_dir, args.work, "0.6.0", "techquest-oritech-pipes", "TQAutoPipes", frozen=True)
    shutil.copytree(game.server / "techquest-horizon-test/datapacks", game.work / "saves" / game.world / "datapacks")
    probe = LocalProbe(game)
    try:
        game.start("prepare")
        probe.command("clear @s")
        probe.command("gamemode spectator")
        probe.command("tp @s 140.5 200 179.5")
        game.call("wait-ready", timeout=180)
        assert "techquest_terralith" in probe.command("datapack list enabled")
        probe.load()
        prepared = probe.prepare()
        game.call("screenshot", game.work / "automated-first-batch.png")
        game.call("save")
    finally:
        game.stop()
    try:
        game.start("verify")
        probe.load()
        completed = probe.finish()
        game.call("screenshot", game.work / "automated-second-batch.png")
        game.call("save")
    finally:
        game.stop()
    try:
        game.start("final-reopen")
        probe.load()
        assert probe.snapshot() == completed["final"]
        assert dict(probe.items(BLOCKED_BARREL)) == completed["barrel"]
        connections = {pos: game.call("block", *map(int, pos.split())) for pos in ("136 200 175", "137 200 177", "138 200 176")}
        status = game.call("status")
        assert status["server"]["joined"] and status["server"]["decode_errors"] == 0
        probe.command("tp @s 144.5 200 178.5")
        game.call("screenshot", game.work / "automated-reopened.png")
        game.call("save")
    finally:
        game.stop()
    assert probe.installs == [FUEL_MODULE, RAW_MODULE, OUT_MODULE]
    report = {"schema": 1, "pretty_pipes_version": game.version, "oritech_content_version": "0.2.0",
              "prepared": prepared, "completed": completed, "connections": connections,
              "connected_local_graphical_client": True, "terralith_world_datapack_enabled": True,
              "three_extractors_installed_by_player_interaction": True, "module_menus_opened_by_player": True,
              "input_and_output_automation_verified": True, "real_inflight_and_final_state_physically_reopened": True,
              "full_destination_pauses_extraction_and_freeing_slot_resumes": True,
              "machine_input_not_extracted": True, "sixteen_ingots_from_sixteen_raw_iron_and_one_coal": True,
              "machine_inventory_energy_progress_outputs_or_cargo_injected": False,
              "machine_core_pipe_chest_and_source_material_fixtures": True,
              "protocol_decode_errors": 0, "device_type": status["renderer"]["device_type"],
              "licensed_account_or_dedicated_join_tested": False, "full_modpack_ported": False, "published": False}
    (game.work / "checked-result.json").write_text(json.dumps(report, indent=2) + "\n")
    (game.work / "commands.json").write_text(json.dumps(probe.rows, indent=2) + "\n")
    print("Graphical Oritech/Pretty Pipes automation and physical reopens passed", flush=True)


if __name__ == "__main__":
    main()

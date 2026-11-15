#!/usr/bin/env python3
"""Run the original routing controls against an installed native Horizon server."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from reference_pretty_pipes import INPUT, OUTPUT, MODULE, inventory, module, snapshot, sprint

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from install_isolated_server import verify


class Native:
    def __init__(self, server, binary):
        self.server, self.binary = server.resolve(), binary.resolve()

    def command(self, line):
        return subprocess.run([str(self.binary), "--dir", str(self.server), "cmd", line],
                              capture_output=True, text=True, check=True, timeout=90).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("prepare", "verify"), required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    lock = verify(args.server_dir)
    if ("prettypipes" not in lock["modules"] or
            not any(m["id"] == "techquest_pretty_pipes" for m in lock["native_modules"])):
        raise ValueError("installed native transport prototype required")
    native = Native(args.server_dir, Path(lock["server_binary"]))
    native.command("tick freeze")
    native.command("forceload add 112 160 144 192")
    deadline = time.monotonic() + 45
    while "Test passed" not in native.command(f"execute if loaded {INPUT}"):
        if time.monotonic() >= deadline:
            raise TimeoutError("native fixture chunk not loaded")
        time.sleep(0.1)
    checks = {}
    if args.phase == "prepare":
        native.command("fill 124 198 172 136 204 180 minecraft:air")
        for position, block in ((INPUT, "minecraft:chest"), (OUTPUT, "minecraft:chest"),
                                (MODULE, "prettypipes:pipe"), ("130 200 176", "prettypipes:pipe"),
                                ("131 200 176", "prettypipes:pipe")):
            if "Changed the block" not in native.command(f"setblock {position} {block}"):
                raise RuntimeError("native fixture block placement failed")
        inventory(native, INPUT, 8)
        sprint(native, 300)
        checks["without_extraction_module"] = snapshot(native)
        assert checks["without_extraction_module"] == {"input": 8, "output": 0}
        module(native, "low")
        sprint(native, 400)
        checks["low_module_delivery"] = snapshot(native)
        assert checks["low_module_delivery"] == {"input": 0, "output": 8}
        native.command("setblock 130 200 176 minecraft:air")
        inventory(native, INPUT, 8)
        inventory(native, OUTPUT, 0)
        sprint(native, 100)
        checks["disconnected_network"] = snapshot(native)
        assert checks["disconnected_network"] == {"input": 8, "output": 0}
        native.command("setblock 130 200 176 prettypipes:pipe")
        module(native, "high")
        sprint(native, 20)
        checks["saved_while_in_flight"] = snapshot(native)
        assert checks["saved_while_in_flight"] == {"input": 0, "output": 0}
    else:
        checks["immediately_after_reopen"] = snapshot(native)
        sprint(native, 400)
        checks["delivery_after_reopen"] = snapshot(native)
        assert checks["delivery_after_reopen"] == {"input": 0, "output": 8}
    if "Saved the game" not in native.command("save-all flush"):
        raise RuntimeError("native fixture save failed")
    subprocess.run([str(native.binary), "--dir", str(native.server), "stop"],
                   check=True, capture_output=True, text=True, timeout=90)
    report = {"schema": 1, "phase": args.phase, "minecraft": "26.3",
              "native_module": "techquest_pretty_pipes", "content_modules": len(lock["modules"]),
              "compiled_native_modules": len(lock["native_modules"]), "checks": checks,
              "exact_transfer_timing_tested": False, "gui_tested": False,
              "recipes_tested": False, "full_mod_ported": False}
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("Native Pretty Pipes", args.phase, "checks:", checks)


if __name__ == "__main__":
    main()

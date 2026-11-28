#!/usr/bin/env python3
"""Observe original spawner NBT via private loopback RCON in a scratch server.

Start the original NeoForge 1.21.1 server separately with pinned pack JARs.
Use --place only in a dedicated scratch world, with the already accepted EULA.
The password stays in server.properties; no raw NBT or credentials are exported.
"""
import argparse
import json
from pathlib import Path
import re
import socket
import struct
import time


class Reference:
    def __init__(self, server):
        properties = {}
        for line in (server / "server.properties").read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                properties[key] = value
        if (properties.get("server-ip") != "127.0.0.1" or
                properties.get("online-mode") != "true" or
                properties.get("white-list") != "true" or
                properties.get("enable-rcon") != "true" or
                not properties.get("level-name", "").startswith("techquest-reference-")):
            raise ValueError("expected an isolated, authenticated reference test server")
        if not re.search(r"^eula=true$", (server / "eula.txt").read_text(), re.MULTILINE):
            raise ValueError("reference server EULA must already be accepted")
        self.port = int(properties["rcon.port"])
        self.password = properties["rcon.password"]

    def command(self, line):
        def packet(ident, kind, text):
            payload = struct.pack("<ii", ident, kind) + text.encode() + b"\0\0"
            return struct.pack("<i", len(payload)) + payload

        with socket.create_connection(("127.0.0.1", self.port), timeout=30) as sock:
            def readn(count):
                result = b""
                while len(result) < count:
                    part = sock.recv(count - len(result))
                    if not part:
                        raise RuntimeError("reference RCON closed unexpectedly")
                    result += part
                return result

            def receive():
                size = struct.unpack("<i", readn(4))[0]
                if not 10 <= size <= 4096:
                    raise RuntimeError("unexpected or fragmented reference response")
                payload = readn(size)
                return struct.unpack("<ii", payload[:8]), payload[8:-2].decode()

            sock.sendall(packet(1, 3, self.password))
            header, _ = receive()
            if header != (1, 2):
                raise RuntimeError("reference RCON authentication failed")
            sock.sendall(packet(2, 2, line))
            header, response = receive()
            if header != (2, 0):
                raise RuntimeError("reference RCON response mismatch")
            return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, required=True)
    parser.add_argument("--plans", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--place", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    reference = Reference(args.server_dir)
    plans = json.loads(args.plans.read_text())
    if plans["seed"] != 263 or any(p["id"] != "betterdungeons:small_dungeon" for p in plans["plans"]):
        parser.error("expected the reviewed small-dungeon plan")
    if "There are 0 " not in reference.command("list"):
        raise ValueError("reference server must have no connected players")
    probes = []
    for plan in plans["plans"]:
        if args.place:
            lo, hi = plan["box_min"], plan["box_max"]
            reference.command(f"forceload add {lo[0]} {lo[2]} {hi[0]} {hi[2]}")
            x, z = [v * 16 for v in plan["chunk"]]
            deadline = time.monotonic() + 90
            while "Test passed" not in reference.command(f"execute if loaded {x} 0 {z}"):
                if time.monotonic() >= deadline:
                    raise TimeoutError("reference chunks did not load")
                time.sleep(0.5)
            if "Generated structure" not in reference.command(f"place structure {plan['id']} {x} 100 {z}"):
                raise RuntimeError("reference structure placement failed")
        for candidate in plan["block_entity_candidates_before_processors"]:
            if candidate["block"] != "minecraft:spawner":
                continue
            position = " ".join(map(str, candidate["position"]))
            response = reference.command(f"data get block {position}")
            mob = re.search(r'SpawnData: \{entity: \{id: "([a-z0-9_:/.\-]+)"', response)
            if not mob:
                raise RuntimeError("original spawner missing at predicted position")
            fields = {}
            for key in ("Delay", "MinSpawnDelay", "MaxSpawnDelay", "SpawnCount",
                        "MaxNearbyEntities", "RequiredPlayerRange", "SpawnRange"):
                match = re.search(rf'\b{key}: (-?\d+)s\b', response)
                if not match:
                    raise RuntimeError("original spawner field missing")
                fields[key] = int(match.group(1))
            probes.append({"chunk": plan["chunk"], "position": candidate["position"],
                           "spawn_entity": mob.group(1), "fields": fields,
                           "potential_entity_matches":
                               f'SpawnPotentials: [{{data: {{entity: {{id: "{mob.group(1)}"}}}}' in response})
    report = {"schema": 1, "minecraft": "1.21.1", "loader": "NeoForge 21.1.264",
              "seed": 263, "probes": probes}
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print("Original spawners observed:", len(probes))


if __name__ == "__main__":
    main()

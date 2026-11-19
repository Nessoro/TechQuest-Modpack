"""TechQuest issue #52: Interdimensional Wireless Transmitter 1.21.1-0.1.5.

Static checks are not a substitute for client, world, chunk-loading or server tests.
Before a release, the official Modrinth SHA-512 must be locked and the full
pack builder must run successfully.
"""
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "nQR8XALE"
VERSION = "CcRkmcRp"
SLUG = "interdimensional-wireless-transmitter"
FILENAME = "interdimensionalwirelesstransmitter-neoforge-1.21.1-0.1.5.jar"
SHA512 = "7cb1ccf0af474c6229610e3aab81ea671d46e5380577ea194c4a9da80fa9a7eb0b318624faabeb708d82cde6129a4b43fdb4ec9eecebda1839a5d46e6f60e57d"
SIDES = {"client": "required", "server": "required"}


class InterdimensionalWirelessTransmitterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = cls.cfg["mods"]

    def test_unchanged_platform_and_parent_mods(self):
        self.assertEqual(
            (self.cfg["minecraft"], self.cfg["loader"], self.cfg["loader_version"]),
            ("1.21.1", "neoforge", "21.1.264"),
        )
        for slug in ("refined-storage", "refined-storage-jei-integration", "jei",
                     "ae2", "open-parties-and-claims", "xaeros-world-map"):
            with self.subTest(slug=slug):
                matches = [m for m in self.mods if m["project"] == slug]
                self.assertEqual(1, len(matches), slug)
                self.assertTrue(matches[0]["required"], slug)
        self.assertEqual(self.cfg["modrinth_lock"]["KDvYkUg3"]["version"], "2.0.9")

    def test_exact_neo_version_once_and_both_sides(self):
        matches = [m for m in self.mods if m["project"] == SLUG]
        self.assertEqual(1, len(matches))
        mod = matches[0]
        self.assertTrue(mod["required"])
        self.assertEqual(VERSION, mod["version_id"])
        self.assertEqual(SIDES, mod["environment"])
        self.assertFalse(mod.get("client_only", False))

    def test_upstream_sha512_must_be_pinned_before_full_build(self):
        pin = self.cfg["modrinth_lock"].get(PROJECT)
        self.assertIsNotNone(pin, 'Official Modrinth SHA-512 lock is required')
        self.assertEqual(VERSION, pin["version_id"])
        self.assertEqual("1.21.1-0.1.5", pin["version"])
        self.assertEqual(FILENAME, pin["filename"])
        self.assertEqual(SHA512, pin["sha512"])
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{128}", pin["sha512"]))
        self.assertEqual(SIDES, pin["environment"])

    def test_verified_pin_in_mrpack_when_available(self):
        pin = self.cfg["modrinth_lock"].get(PROJECT)
        self.assertIsNotNone(pin)
        record = {
            "filename": FILENAME, "environment": SIDES,
            "file": {
                "filename": FILENAME, "hashes": {"sha512": pin["sha512"]},
                "url": ("https://cdn.modrinth.com/data/" + PROJECT
                        + "/versions/" + VERSION + "/" + FILENAME),
                "size": 141867,
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "test.mrpack"
            build_pack.make_mrpack(self.cfg, [record], output)
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read("modrinth.index.json"))
                files = [f for f in manifest["files"] if f["path"] == "mods/" + FILENAME]
                self.assertEqual(1, len(files))
                self.assertEqual(pin["sha512"], files[0]["hashes"]["sha512"])
                self.assertEqual(SIDES, files[0]["env"])
                self.assertNotIn("overrides/mods/" + FILENAME, archive.namelist())

    def test_catalog_and_no_embedded_third_party_binary(self):
        source = (ROOT / "scripts" / "sync_site_mods.py").read_text(encoding="utf-8")
        self.assertIn('"interdimensional-wireless-transmitter"', source)
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn("https://modrinth.com/mod/" + SLUG, html)
        # Generated output/client and output/server legitimately contain the downloaded JAR.
        # Only source-controlled binary locations must stay clean.
        for root in (ROOT / "mods", ROOT / "manual-mods", ROOT / "overrides" / "mods"):
            if root.exists():
                self.assertFalse(list(root.rglob(FILENAME)), root)


if __name__ == "__main__":
    unittest.main()

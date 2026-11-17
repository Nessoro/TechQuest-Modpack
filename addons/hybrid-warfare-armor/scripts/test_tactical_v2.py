"""Tactical Blue V2 assets must match the four-slot model specification."""
import struct
import unittest
from tactical_v2 import geometry, generate, COLORS, NAMES, ASSET

class TacticalBlueV2Tests(unittest.TestCase):
    def test_all_slots_and_geometry(self):
        data = geometry()
        self.assertEqual(set(data), {"helmet", "chest", "leggings", "boots"})
        self.assertEqual(tuple(len(data[part]) for part in data), (24, 72, 18, 16))
        bones = {slot: {p[0] for p in models} for slot,models in data.items()}
        self.assertEqual(bones["helmet"], {"head"})
        self.assertIn("body", bones["chest"])
        self.assertIn("left_arm", bones["chest"])
        self.assertIn("left_leg", bones["leggings"])
        self.assertIn("right_leg", bones["boots"])

    def test_generated_resources_and_pngs(self):
        result = generate()
        self.assertEqual(len(result), 4)
        for item in NAMES.values():
            geometry_file = ASSET / "models/armor" / (item + ".cuboids")
            texture_file = ASSET / "textures/models/armor" / (item + "_3d.png")
            lines = geometry_file.read_text(encoding="utf-8").splitlines()
            self.assertTrue(all(len(line.split()) == 10 for line in lines))
            png = texture_file.read_bytes()
            self.assertTrue(png.startswith(bytes.fromhex("89504e470d0a1a0a")))
            self.assertEqual(struct.unpack(">II", png[16:24]), (256, 256))

    def test_original_blue_palette(self):
        self.assertTrue(COLORS["blue"][2] > COLORS["blue"][0])
        self.assertTrue(COLORS["navy"][2] > COLORS["navy"][0])

if __name__ == "__main__":
    unittest.main()

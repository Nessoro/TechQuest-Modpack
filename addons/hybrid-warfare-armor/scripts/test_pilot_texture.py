"""Smoke-test the real 64x32 pilot texture mapping without starting Minecraft."""
import unittest
from pilot_texture import texture, CYAN, GLOW

class PilotTextureTests(unittest.TestCase):
    def test_helmet_has_only_head_uv(self):
        pixels=texture("helmet")
        self.assertEqual(len(pixels), 64*32)
        self.assertEqual(pixels[11*64+9], CYAN)
        self.assertEqual(pixels[11*64+10], GLOW)
        self.assertTrue(all(pixels[y*64+x][3]==0 for y in range(16,32) for x in range(64)))

    def test_vest_only_torso_and_sleeves(self):
        pixels=texture("vest")
        self.assertEqual(len(pixels), 64*32)
        self.assertEqual(pixels[26*64+23], GLOW)
        self.assertTrue(all(pixels[y*64+x][3]==0 for y in range(16) for x in range(64)))

    def test_not_mutable_shared_data(self):
        original=texture("helmet")
        original[0]=(255,0,0,255)
        self.assertEqual(texture("helmet")[0],(0,0,0,0))

if __name__ == "__main__":
    unittest.main()

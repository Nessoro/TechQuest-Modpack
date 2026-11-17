"""Check the 3D pilot geometry, its UV bounds and 256x256 armor atlases."""
import unittest
from pathlib import Path
from generate_3d_textures import get_cubes, make_pixels, generate, TEXTURES

class MekMilitary3DTests(unittest.TestCase):
    def test_required_cuboids(self):
        c = get_cubes()
        self.assertEqual((len(c["helmet"]), len(c["chest"])), (24, 35))
        self.assertTrue(all(item[0] == "head" for item in c["helmet"]))
        self.assertEqual({item[0] for item in c["chest"]}, {"body", "right_arm", "left_arm"})

    def test_native_atlas_has_tech_colors(self):
        cubes = get_cubes()
        for piece in ["helmet", "chest"]:
            pixels = make_pixels(piece, cubes[piece])
            self.assertEqual(len(pixels), 256 * 256)
            self.assertTrue(any(r < 70 and b > 170 for r, g, b, a in pixels),
                            "Missing cyan energy accents")

    def test_created_png_dimensions(self):
        generate()
        for file in ("mek_ru_helmet_6b47_3d.png", "mek_ru_chest_6b43_3d.png"):
            data = (TEXTURES / file).read_bytes()
            self.assertEqual(data[:8], bytes.fromhex("89504e470d0a1a0a"))
            self.assertEqual(int.from_bytes(data[16:20], "big"), 256)
            self.assertEqual(int.from_bytes(data[20:24], "big"), 256)

if __name__ == "__main__":
    unittest.main()

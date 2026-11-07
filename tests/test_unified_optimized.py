"""The player-facing TechQuest package must be a single optimized profile."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("techquest_build_optimized", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class UnifiedOptimizedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))

    def test_single_profile_with_core_and_optimizations(self):
        self.assertEqual(self.cfg["version"], "0.3.3-alpha")
        self.assertNotIn("lite_profile", self.cfg)
        mods = {mod["project"]: mod for mod in self.cfg["mods"]}
        for name in ("buildcraft-community-edition", "create", "mekanism",
                     "modern-industrialization", "ae2", "superb-warfare"):
            self.assertIn(name, mods)
        self.assertTrue(any("Industrial Craft" in m["name"] and m["required"]
                            for m in self.cfg["manual_mods"]))
        for name in ("sodium", "entityculling", "ferrite-core", "modernfix",
                     "immediatelyfast", "moreculling", "badoptimizations",
                     "dynamic-fps", "lithostitched", "irons-lib"):
            self.assertIn(name, mods)
            self.assertTrue(mods[name]["required"], f"{name} should be pinned as required")
        self.assertNotIn("iris", mods)
        self.assertNotIn("new-health-bars", mods)
        self.assertTrue(mods["health-indicator-txf"]["client_only"])
        self.assertTrue(self.cfg["performance_profile"]["unified"])
        self.assertFalse(self.cfg["performance_profile"]["shader_loader_included"])

    def test_default_video_settings_are_embedded(self):
        cfg = dict(self.cfg)
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "optimized.mrpack"
            self.assertEqual(builder.make_mrpack(cfg, [], archive), 0)
            with zipfile.ZipFile(archive) as z:
                index = json.loads(z.read("modrinth.index.json"))
                settings = z.read("overrides/options.txt").decode("utf-8")
                guide = z.read("overrides/TECHQUEST_OPTIMIZED.txt").decode("utf-8")
            self.assertEqual(index["versionId"], "0.3.3-alpha")
            self.assertIn("renderDistance:6", settings)
            self.assertIn("graphicsMode:0", settings)
            self.assertIn("particles:2", settings)
            self.assertIn("Iris", guide)

if __name__ == "__main__":
    unittest.main()

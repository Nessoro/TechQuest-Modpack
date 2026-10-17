import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "include_industrialcraft.py"
spec = importlib.util.spec_from_file_location("techquest_ic2_local_pack", SCRIPT)
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)

IC2_NAME = "industrial-craft-2-nostalgia-21.1.0-local.26.jar"

def fake_ic2(path, modid="ic2"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("META-INF/neoforge.mods.toml",
                   'modLoader="javafml"\n[[mods]]\nmodId="' + modid + '"\n')
        z.writestr("dummy.bytes", "x" * 2300)

def fake_pack(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("modrinth.index.json",
                   json.dumps({"game": "minecraft",
                               "dependencies": {"minecraft": "1.21.1"}}))
        z.writestr("overrides/INSTALL_IC2.txt", "manual port")

class IncludeIndustrialCraftTests(unittest.TestCase):
    def test_embeds_ic2_jar(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            jar = root / IC2_NAME
            pack = root / "input.mrpack"
            out = root / "complete.mrpack"
            fake_ic2(jar)
            fake_pack(pack)
            item = plugin.embed_ic2(pack, jar, out, IC2_NAME)
            with zipfile.ZipFile(out) as z:
                self.assertEqual(z.read(item), jar.read_bytes())
                self.assertIn("modrinth.index.json", z.namelist())

    def test_rejects_other_mod_id(self):
        with tempfile.TemporaryDirectory() as d:
            jar = Path(d) / IC2_NAME
            fake_ic2(jar, modid="other")
            with self.assertRaises(plugin.build_pack.BuildError):
                plugin.validate_ic2(jar, IC2_NAME)

    def test_rejects_wrong_filename(self):
        with tempfile.TemporaryDirectory() as d:
            jar = Path(d) / "wrong.jar"
            fake_ic2(jar)
            with self.assertRaises(plugin.build_pack.BuildError):
                plugin.validate_ic2(jar, IC2_NAME)

    def test_rejects_input_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            jar = Path(d) / IC2_NAME
            pack = Path(d) / "input.mrpack"
            fake_ic2(jar)
            fake_pack(pack)
            with self.assertRaises(plugin.build_pack.BuildError):
                plugin.embed_ic2(pack, jar, pack, IC2_NAME)

if __name__ == "__main__":
    unittest.main()

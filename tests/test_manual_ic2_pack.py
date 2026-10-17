import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "build_pack.py"
spec = importlib.util.spec_from_file_location("techquest_manual_builder", SOURCE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

IC2_JAR = "industrial-craft-2-nostalgia-21.1.0-local.26.jar"
IC2_URL = "https://raw.githubusercontent.com/Nessoro/TechQuest-Modpack/503b0676cb44764ede56e94975f66e9a3c35c6db/manual-mods/" + IC2_JAR

class ManualModPackTests(unittest.TestCase):
    def fixture(self, root):
        moddir = root / "manual-mods"
        moddir.mkdir()
        path = moddir / IC2_JAR
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("META-INF/neoforge.mods.toml", 'modLoader="javafml"')
            z.writestr("assets/data.bin", b"x" * 4096)
        cfg = {"version":"test", "pack_name":"TechQuest", "description":"Test",
               "minecraft":"1.21.1", "loader_version":"21.1.259",
               "manual_mods":[{"name":"IC2", "file_name":IC2_JAR,
                               "download_url":IC2_URL, "required":True}]}
        return cfg, path

    def test_missing_required_mod_must_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cfg, jar = self.fixture(root)
            jar.unlink()
            with patch.object(builder,"ROOT",root):
                with self.assertRaises(builder.BuildError):
                    builder.manual_records(cfg)

    def test_mrpack_references_ic2_with_both_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cfg, jar = self.fixture(root)
            with patch.object(builder,"ROOT",root):
                manual = builder.manual_records(cfg)
            self.assertEqual(len(manual),1)
            self.assertEqual(manual[0]["hashes"]["sha512"],
                             hashlib.sha512(jar.read_bytes()).hexdigest())
            pack = root / "test.mrpack"
            self.assertEqual(builder.make_mrpack(cfg,[],pack,manual), 1)
            with zipfile.ZipFile(pack) as z:
                index = json.loads(z.read("modrinth.index.json"))
                names = z.namelist()
            self.assertEqual(index["files"][0]["path"],"mods/" + IC2_JAR)
            self.assertEqual(index["files"][0]["downloads"],[IC2_URL])
            self.assertIn("sha1",index["files"][0]["hashes"])
            self.assertIn("sha512",index["files"][0]["hashes"])
            self.assertNotIn("overrides/mods/" + IC2_JAR,names)

if __name__ == "__main__":
    unittest.main()

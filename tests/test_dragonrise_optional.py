"""Contract tests for DragonRise optional import (not runtime compatibility)."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("techquest_dr_builder", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class DragonRiseImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))

    def test_manifest(self):
        matches = [m for m in self.cfg["optional_local_mods"] if m["id"] == "dragonrise_reforge"]
        self.assertEqual(len(matches), 1)
        mod = matches[0]
        self.assertEqual(mod["file_name"], "dragonrise_reforge-1.5.1-release.jar")
        self.assertEqual(mod["curseforge_project_id"], 1346094)
        self.assertEqual(mod["curseforge_file_id"], 9208025)
        self.assertEqual(mod["version"], "1.5.1")
        self.assertEqual(mod["minecraft"], "1.21.1")
        self.assertEqual(mod["loader"], "neoforge")
        self.assertEqual(mod["side"], "both")
        self.assertFalse(mod["required"])
        self.assertEqual(mod["install_mode"], "manual_user_import")
        self.assertEqual(mod["dependencies"], ["superb-warfare"])
        self.assertTrue(any(m["project"] == "superb-warfare" and m["required"] for m in self.cfg["mods"]))
        self.assertFalse(any(m["file_name"] == mod["file_name"] for m in self.cfg["manual_mods"]))

    def test_archive_metadata_not_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.mrpack"
            self.assertEqual(builder.make_mrpack(self.cfg, [], path), 0)
            with zipfile.ZipFile(path) as archive:
                metadata = json.loads(archive.read("overrides/TECHQUEST_OPTIONAL_LOCAL_MODS.json"))
                self.assertTrue(any(m["id"] == "dragonrise_reforge" for m in metadata))
                self.assertFalse(any("dragonrise_reforge" in name.lower() for name in archive.namelist()))
                index = json.loads(archive.read("modrinth.index.json"))
                self.assertFalse(any("dragonrise_reforge" in m["path"].lower() for m in index["files"]))

    def test_installer_wiring(self):
        source = (ROOT / "windows-installer/Program.cs").read_text(encoding="utf-8")
        for expected in (
            "importDragonRise.Click += (_, _) => ImportDragonRise()",
            "importDragonRise.Enabled = !busy",
            "dragonrise_reforge-1.5.1-release.jar",
            "https://www.curseforge.com/minecraft/mc-mods/sbw-drr/files/9208025",
            '"superbwarfare", "TECHQUEST_DRAGONRISE_IMPORT.txt"',
            "File.Copy(source, destination, overwrite: false)",
        ):
            self.assertIn(expected, source)

if __name__ == "__main__":
    unittest.main()

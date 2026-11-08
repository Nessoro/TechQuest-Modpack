"""Contract tests for opt-in CurseForge AMW import without JAR redistribution."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("techquest_amw_builder", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class OptionalAMWTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))

    def test_amw_is_optional_and_sources_are_pinned(self):
        mods = self.cfg.get("optional_local_mods", [])
        self.assertEqual(len(mods), 1)
        mod = mods[0]
        self.assertEqual(mod["id"], "acceleratedmcwarfare")
        self.assertEqual(mod["file_name"], "acceleratedMcWarfare-1.0.4..jar")
        self.assertFalse(mod["required"])
        self.assertEqual(mod["install_mode"], "manual_user_import")
        self.assertEqual(mod["curseforge_file_id"], 9298161)
        self.assertEqual(mod["loader"], "neoforge")
        self.assertEqual(mod["minecraft"], "1.21.1")
        self.assertEqual(mod["side"], "both")
        self.assertEqual(mod["license"], "All Rights Reserved")
        self.assertEqual(mod["dependencies"], ["geckolib"])
        deps = [x for x in self.cfg["mods"] if x["project"] == "geckolib"]
        self.assertEqual(len(deps), 1)
        self.assertTrue(deps[0]["required"])

    def test_pack_contains_metadata_but_no_amw_jar(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "test.mrpack"
            self.assertEqual(builder.make_mrpack(self.cfg, [], archive_path), 0)
            with zipfile.ZipFile(archive_path) as archive:
                self.assertIn("overrides/TECHQUEST_OPTIONAL_LOCAL_MODS.json", archive.namelist())
                metadata = json.loads(archive.read("overrides/TECHQUEST_OPTIONAL_LOCAL_MODS.json"))
                self.assertEqual(metadata[0]["curseforge_file_id"], 9298161)
                self.assertFalse(any("acceleratedMcWarfare" in name for name in archive.namelist()))
                index = json.loads(archive.read("modrinth.index.json"))
                self.assertFalse(any("acceleratedMcWarfare" in m["path"] for m in index["files"]))


if __name__ == "__main__":
    unittest.main()

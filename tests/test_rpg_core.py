"""Protect micro3: preserve TechQuest Compatibility and exclude only RPG Core."""
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts import install_client, install_server


RPG_JAR = "techquest-rpg-core-0.1.0.jar"


class RemoveRPGCoreTests(unittest.TestCase):
    def test_rpg_builder_removed_compatibility_builder_preserved(self):
        self.assertFalse(hasattr(build_pack, "rpg_core_jar"))
        self.assertFalse(hasattr(build_pack, "RPG_JAR_NAME"))
        self.assertTrue(hasattr(build_pack, "compatibility_jar"))
        self.assertEqual(build_pack.COMPAT_JAR_NAME, "techquest-compat-1.0.0.jar")

    def test_client_server_and_mrpack_keep_compatibility_only(self):
        cfg = build_pack.load_cfg()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "micro3.mrpack"
            build_pack.make_mrpack(cfg, [], pack)
            with zipfile.ZipFile(pack) as archive:
                self.assertIn("overrides/mods/" + build_pack.COMPAT_JAR_NAME, archive.namelist())
                self.assertNotIn("overrides/mods/" + RPG_JAR, archive.namelist())
                install_client.install_guide_overrides(archive, root / "client")
            self.assertEqual((root / "client/mods" / build_pack.COMPAT_JAR_NAME).read_bytes(),
                             build_pack.compatibility_jar())
            self.assertFalse((root / "client/mods" / RPG_JAR).exists())
            mods = root / "server/mods"
            mods.mkdir(parents=True)
            install_server.install_compatibility(pack, mods)
            self.assertEqual((mods / build_pack.COMPAT_JAR_NAME).read_bytes(), build_pack.compatibility_jar())
            self.assertFalse((mods / RPG_JAR).exists())

    def test_windows_installer_requires_compatibility_and_rejects_rpg(self):
        text = (Path(__file__).resolve().parents[1] /
                "windows-installer/Program.cs").read_text(encoding="utf-8")
        self.assertIn("StageFirstPartyCompatibilityJar(staging)", text)
        self.assertIn('relative == "mods/techquest-compat-1.0.0.jar"', text)
        self.assertNotIn('relative == "mods/' + RPG_JAR + '"', text)
        self.assertIn('archive.GetEntry("overrides/mods/techquest-compat-1.0.0.jar") is null', text)
        self.assertIn('e.FullName.StartsWith("overrides/mods/techquest-rpg-core"', text)
        self.assertIn('e.FullName.StartsWith("overrides/mods/pmmo-"', text)
        self.assertIn('name.StartsWith("techquest-rpg-core"', text)


if __name__ == "__main__":
    unittest.main()

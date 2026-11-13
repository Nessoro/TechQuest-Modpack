"""Guard future TechQuest artifacts against reintroducing removed custom mod JARs."""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts import install_client, install_server


REMOVED_JARS = ("techquest-rpg-core-0.1.0.jar", "techquest-compat-1.0.0.jar")


class NoCustomFirstPartyModsTests(unittest.TestCase):
    def test_first_party_jar_build_functions_are_removed(self):
        self.assertFalse(hasattr(build_pack, "rpg_core_jar"))
        self.assertFalse(hasattr(build_pack, "compatibility_jar"))
        self.assertFalse(hasattr(build_pack, "RPG_JAR_NAME"))
        self.assertFalse(hasattr(build_pack, "COMPAT_JAR_NAME"))

    def test_both_custom_jars_excluded_from_manifest_and_client_and_server(self):
        cfg = build_pack.load_cfg()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            pack = folder / "micro3.mrpack"
            build_pack.make_mrpack(cfg, [], pack)
            with zipfile.ZipFile(pack) as archive:
                paths = archive.namelist()
                for jar in REMOVED_JARS:
                    self.assertNotIn("overrides/mods/" + jar, paths)
                self.assertFalse(any(n.startswith("overrides/mods/") for n in paths))
                install_client.install_guide_overrides(archive, folder / "client")
            for jar in REMOVED_JARS:
                self.assertFalse((folder / "client/mods" / jar).exists())
            mods = folder / "server/mods"
            mods.mkdir(parents=True)
            install_server.install_compatibility(pack, mods)
            for jar in REMOVED_JARS:
                self.assertFalse((mods / jar).exists())

    def test_windows_installer_does_not_stage_removed_custom_jars(self):
        text = (Path(__file__).resolve().parents[1] /
                "windows-installer/Program.cs").read_text(encoding="utf-8")
        self.assertNotIn("StageFirstPartyCompatibilityJar(staging)", text)
        for jar in REMOVED_JARS:
            self.assertNotIn('relative == "mods/' + jar + '"', text)
            self.assertIn('archive.GetEntry("overrides/mods/' + jar + '") is not null', text)


if __name__ == "__main__":
    unittest.main()

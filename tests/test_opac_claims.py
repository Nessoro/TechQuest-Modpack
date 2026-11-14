"""Regression tests for OPAC beta 0.33.0 in the TechQuest micro5 stack.

Static and file-install tests only. These do not prove real Minecraft runtime
compatibility, Xaero integration, claim permission behavior or server TPS.
"""
import json
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts import install_client, install_server


ROOT = Path(__file__).resolve().parents[1]
CONFIG_REL = "defaultconfigs/openpartiesandclaims-server.toml"
PROJECT = "gF3BGWvG"
VERSION = "yWmXD7GW"
FILENAME = "open-parties-and-claims-neoforge-1.21.1-0.33.0.jar"
SHA512 = "646fd9796ef2dfd1132e22aacf1a417639233d90fb7eb862a718badfed955d54714c88327b7ddc651f98cd5b7d2a80e8c91233d2232680d4998fdd10ef392ffb"


class TestOpenPartiesClaims(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = {m["project"]: m for m in cls.cfg["mods"]}
        cls.lock = cls.cfg["modrinth_lock"][PROJECT]
        cls.config_path = ROOT / "compat" / "opac" / "openpartiesandclaims-server.toml"

    def test_keeps_techquest_platform_and_existing_mods(self):
        self.assertEqual(("1.21.1", "neoforge", "21.1.264"),
                         (self.cfg["minecraft"], self.cfg["loader"], self.cfg["loader_version"]))
        for mod in ("ae2", "refined-storage", "xaeros-minimap", "xaeros-world-map",
                    "create", "mekanism", "buildcraft-community-edition"):
            self.assertIn(mod, self.mods, mod)
            self.assertTrue(self.mods[mod]["required"], mod)
        self.assertEqual(1, sum(m["project"] == "open-parties-and-claims"
                                for m in self.cfg["mods"]))

    def test_exact_official_release_pinned_on_client_and_server(self):
        mod = self.mods["open-parties-and-claims"]
        self.assertTrue(mod["required"])
        self.assertEqual(VERSION, mod["version_id"])
        self.assertEqual({"client": "required", "server": "required"}, mod["environment"])
        self.assertFalse(mod.get("client_only", False))
        self.assertEqual(VERSION, self.lock["version_id"])
        self.assertEqual("neoforge-1.21.1-0.33.0", self.lock["version"])
        self.assertEqual(FILENAME, self.lock["filename"])
        self.assertEqual(SHA512, self.lock["sha512"])
        self.assertEqual(128, len(self.lock["sha512"]))
        self.assertEqual(mod["environment"], self.lock["environment"])

    def test_conservative_new_world_config(self):
        config = tomllib.loads(self.config_path.read_text(encoding="utf-8"))
        claims = config["serverConfig"]["claims"]
        self.assertIs(claims["enabled"], True)
        self.assertEqual(64, claims["maxPlayerClaims"])
        self.assertEqual(4, claims["maxPlayerClaimForceloads"])
        self.assertEqual("", claims["maxPlayerClaimsPermission"])
        self.assertEqual("", claims["maxPlayerClaimForceloadsPermission"])
        self.assertEqual("ALL", claims["claimsSynchronization"])
        self.assertLess(claims["maxPlayerClaimForceloads"], claims["maxPlayerClaims"])

    def test_pack_builder_seeds_only_new_world_defaults(self):
        overrides = build_pack.opac_config_overrides(self.cfg)
        self.assertEqual([CONFIG_REL], list(overrides))
        self.assertEqual(self.config_path.read_bytes(), overrides[CONFIG_REL])
        self.assertNotIn("world/serverconfig/openpartiesandclaims-server.toml", overrides)
        self.assertNotIn("saves", "/".join(overrides))

    def test_client_and_server_installers_preserve_existing_defaults(self):
        cfg_data = self.config_path.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            pack = path / "sample.mrpack"
            with zipfile.ZipFile(pack, "w") as zipf:
                zipf.writestr("overrides/" + CONFIG_REL, cfg_data)
                zipf.writestr("overrides/untrusted.txt", b"not allowed")
            for label, install in (("client", "client"), ("server", "server")):
                dest = path / label
                dest.mkdir()
                target = dest / CONFIG_REL
                target.parent.mkdir(parents=True)
                target.write_bytes(b"original user config")
                if install == "client":
                    with zipfile.ZipFile(pack) as zf:
                        install_client.install_guide_overrides(zf, dest)
                else:
                    install_server.install_guide_overrides(pack, dest)
                self.assertEqual(b"original user config", target.read_bytes())
                self.assertFalse((dest / "untrusted.txt").exists())
                target.unlink()
                if install == "client":
                    with zipfile.ZipFile(pack) as zf:
                        install_client.install_guide_overrides(zf, dest)
                else:
                    install_server.install_guide_overrides(pack, dest)
                self.assertEqual(cfg_data, target.read_bytes())

    def test_gui_installer_whitelists_exact_defaultconfigs_file(self):
        source = (ROOT / "windows-installer" / "Program.cs").read_text(encoding="utf-8")
        self.assertIn('relative == "' + CONFIG_REL + '"', source)
        self.assertIn("if (File.Exists(destination))", source)


if __name__ == "__main__":
    unittest.main()

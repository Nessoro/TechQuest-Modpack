import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path
import build_pack
from scripts import install_client, install_server

ROOT = Path(__file__).resolve().parents[1]
BOSSES = {"ender_guardian", "ender_golem", "netherite_monstrosity", "ignis",
          "harbinger", "leviathan", "ancient_remnant", "scylla",
          "clawdian", "maledictus"}

class BossDamageTests(unittest.TestCase):
    def test_preserve_conditions_with_range_only(self):
        data = tomllib.loads((ROOT / "compat/boss-damage/conditions-preserved.toml").read_text())
        self.assertEqual(set(data["mobs"]), BOSSES | {"prowler"})
        for name in BOSSES:
            self.assertEqual(data["mobs"][name]["cap_config"], {"range_cap": 256.0})
        self.assertEqual(data["mobs"]["prowler"], {"range_cap": 256.0})

    def test_experimental_is_not_packaged(self):
        data = tomllib.loads((ROOT / "compat/boss-damage/high-impact-experimental.toml").read_text())
        for name in BOSSES:
            self.assertEqual(data["mobs"][name]["cap_config"],
                             {"range_cap": 1000000.0, "damage_cap": 1000000.0, "dps_cap": 1000000.0})
        cfg = build_pack.load_cfg()
        payload = build_pack.boss_damage_overrides(cfg)
        self.assertEqual(set(payload), {"config/cataclysm-common.toml"})
        self.assertNotIn(b"1000000.0", payload["config/cataclysm-common.toml"])

    def test_both_installers_and_player_settings(self):
        cfg = build_pack.load_cfg()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack = root / "pack.mrpack"
            build_pack.make_mrpack(cfg, [], pack)
            with zipfile.ZipFile(pack) as archive:
                data = archive.read("overrides/config/cataclysm-common.toml")
                self.assertIn(b"renderDistance:16", archive.read("overrides/options.txt"))
                self.assertNotIn("overrides/config/high-impact-experimental.toml", archive.namelist())
                install_client.install_guide_overrides(archive, root / "client")
                config = root / "client/config/cataclysm-common.toml"
                self.assertEqual(config.read_bytes(), data)
                config.write_text("player-settings")
                install_client.install_guide_overrides(archive, root / "client")
                self.assertEqual(config.read_text(), "player-settings")
            install_server.install_guide_overrides(pack, root / "server")
            config = root / "server/config/cataclysm-common.toml"
            self.assertEqual(config.read_bytes(), data)
            config.write_text("server-settings")
            install_server.install_guide_overrides(pack, root / "server")
            self.assertEqual(config.read_text(), "server-settings")
            install_server.prepare_properties(root / "server")
            props = (root / "server/server.properties").read_text()
            self.assertIn("view-distance=14\n", props)
            self.assertIn("simulation-distance=5\n", props)

if __name__ == "__main__":
    unittest.main()

"""MI guide after death must not accumulate; preserve first-join and worlds."""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts.mi_guide_config import patch_existing_mi_worlds, patch_mi_guide_config
from scripts.install_client import install_guide_overrides as install_client_overrides
from scripts.install_server import install_guide_overrides as install_server_overrides


class MIRespawnGuideTests(unittest.TestCase):
    def test_only_guide_on_death_disabled_in_new_world_default_config(self):
        cfg = build_pack.load_cfg()
        self.assertEqual(cfg["modrinth_lock"]["Gov5Dboq"]["version"], "2.5.12")
        path = "defaultconfigs/modern_industrialization-server.toml"
        data = build_pack.mi_guide_config_overrides(cfg)
        self.assertEqual(set(data), {path})
        config = data[path].decode("utf-8")
        self.assertIn("spawnWithGuideBook = true", config)
        self.assertIn("respawnWithGuideBook = false", config)
        self.assertNotIn("forgeEnergyPerEu =", config)
        self.assertNotIn("[recipes]", config)

    def test_mrpack_and_both_installers_install_default_config(self):
        cfg = build_pack.load_cfg()
        expected = build_pack.mi_guide_config_overrides(cfg)[
            "defaultconfigs/modern_industrialization-server.toml"]
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            archive_path = root / "test.mrpack"
            build_pack.make_mrpack(cfg, [], archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                key = "overrides/defaultconfigs/modern_industrialization-server.toml"
                self.assertEqual(archive.read(key), expected)
                client = root / "client"
                install_client_overrides(archive, client)
                self.assertEqual((client / "defaultconfigs" /
                                  "modern_industrialization-server.toml").read_bytes(), expected)
            server = root / "server"
            install_server_overrides(archive_path, server)
            self.assertEqual((server / "defaultconfigs" /
                              "modern_industrialization-server.toml").read_bytes(), expected)

    def test_existing_singleplayer_worlds_patch_only_mi_and_backup_once(self):
        with tempfile.TemporaryDirectory() as t:
            game = Path(t)
            world = game / "saves" / "original" / "serverconfig"
            world.mkdir(parents=True)
            config = world / "modern_industrialization-server.toml"
            before = (b"forgeEnergyPerEu = 18\r\n"
                      b"spawnWithGuideBook = true\r\n"
                      b"respawnWithGuideBook = true # keep my machines\r\n"
                      b"[recipes]\r\ncompostableToPlantOil = false\r\n")
            config.write_bytes(before)
            (world.parent / "level.dat").write_bytes(b"world data")
            changed = patch_existing_mi_worlds(game)
            self.assertEqual(changed, [config])
            after = config.read_bytes()
            self.assertEqual(after, before.replace(b"respawnWithGuideBook = true",
                                                   b"respawnWithGuideBook = false"))
            backup = config.with_name(config.name + ".techquest-original.bak")
            self.assertEqual(backup.read_bytes(), before)
            self.assertEqual((world.parent / "level.dat").read_bytes(), b"world data")
            self.assertEqual(patch_existing_mi_worlds(game), [])
            self.assertEqual(backup.read_bytes(), before)

    def test_dedicated_custom_world_and_no_unrelated_files_modified(self):
        with tempfile.TemporaryDirectory() as t:
            server = Path(t)
            (server / "server.properties").write_text("level-name=custom-world\n")
            target = server / "custom-world" / "serverconfig"
            target.mkdir(parents=True)
            config = target / "modern_industrialization-server.toml"
            config.write_text("spawnWithGuideBook = true\n"
                              "respawnWithGuideBook = true\n")
            (server / "eula.txt").write_text("eula=false\n")
            changed = patch_existing_mi_worlds(server, dedicated_server=True)
            self.assertEqual(changed, [config])
            text = config.read_text()
            self.assertIn("spawnWithGuideBook = true", text)
            self.assertIn("respawnWithGuideBook = false", text)
            self.assertEqual((server / "eula.txt").read_text(), "eula=false\n")
            self.assertFalse((server / "world" / "serverconfig" /
                              "modern_industrialization-server.toml").exists())

    def test_legacy_config_missing_key_inserted_at_root(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "modern_industrialization-server.toml"
            path.write_text("spawnWithGuideBook = true\n[recipes]\n"
                            "compostableToPlantOil = true\n")
            self.assertTrue(patch_mi_guide_config(path))
            s = path.read_text()
            self.assertTrue(s.startswith("respawnWithGuideBook = false\n"))
            self.assertIn("spawnWithGuideBook = true", s)
            self.assertTrue(s.index("respawnWithGuideBook") < s.index("[recipes]"))

    def test_missing_or_already_false_files_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "modern_industrialization-server.toml"
            self.assertFalse(patch_mi_guide_config(path))
            path.write_bytes(b"spawnWithGuideBook = false\nrespawnWithGuideBook = false\n")
            self.assertFalse(patch_mi_guide_config(path))
            self.assertFalse(path.with_name(path.name + ".techquest-original.bak").exists())


if __name__ == "__main__":
    unittest.main()

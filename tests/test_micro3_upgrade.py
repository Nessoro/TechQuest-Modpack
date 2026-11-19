"""micro3: repeat installation, removal guards and injected-failure rollback."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import build_pack
from scripts import install_client, install_server
from scripts.mods_transaction import BACKUP, ROTATION, activate_staged_mods

RPG = "techquest-rpg-core-0.1.0.jar"
PMMO = "pmmo-1.21.1-2.10.47.jar"
COMPAT = "techquest-compat-1.0.0.jar"


def fixture_pack(path):
    data = b"fixture-mod"
    filename = "buildcraft-fixture.jar"
    record = {"file": {"filename": filename, "url": "https://example.org/mod.jar",
                       "hashes": {"sha1": hashlib.sha1(data).hexdigest()}, "size": len(data)},
              "environment": {"client": "required", "server": "required"}}
    cfg = {"version": "0.3.3-alpha", "pack_name": "fixture",
           "description": "fixture", "minecraft": "1.21.1",
           "loader_version": "21.1.264"}
    build_pack.make_mrpack(cfg, [record], path)
    return filename, data, cfg


class Micro3UpgradeTests(unittest.TestCase):
    def test_builder_rejects_removed_jars_even_in_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack.mrpack"
            _, _, cfg = fixture_pack(pack)
            for name in (RPG, PMMO):
                with self.subTest(name=name):
                    rec = {"file": {"filename": name, "url": "https://example.org/mod.jar",
                                    "hashes": {"sha1": "a" * 40}, "size": 100},
                           "environment": {"client": "required", "server": "required"}}
                    with self.assertRaisesRegex(build_pack.BuildError, "Removed mod"):
                        build_pack.make_mrpack(cfg, [rec], pack)

    def test_client_repeat_upgrade_preserves_world_and_player_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "pack.mrpack"
            filename, data, _ = fixture_pack(pack)
            game = root / "game"
            mods = game / "mods"
            mods.mkdir(parents=True)
            (game / "TECHQUEST_LAUNCHER_README.txt").write_text("managed")
            for name in (RPG, PMMO, "old.jar"):
                (mods / name).write_bytes(b"legacy")
            (game / "options.txt").write_text("custom")
            (game / "saves").mkdir()
            (game / "saves" / "world.dat").write_bytes(b"world")
            (game / "config").mkdir()
            (game / "config" / "personal.toml").write_text("keep")
            with patch.object(build_pack, "download_checked",
                              side_effect=lambda record, dest: (dest / filename).write_bytes(data)):
                install_client.install(pack, game)
                self.assertTrue((mods / COMPAT).is_file())
                self.assertEqual((mods / filename).read_bytes(), data)
                self.assertFalse((mods / RPG).exists())
                self.assertFalse((mods / PMMO).exists())
                self.assertTrue((game / BACKUP / RPG).exists())
                install_client.install(pack, game)
            self.assertEqual((game / "options.txt").read_text(), "custom")
            self.assertEqual((game / "saves" / "world.dat").read_bytes(), b"world")
            self.assertEqual((game / "config" / "personal.toml").read_text(), "keep")
            self.assertEqual((game / BACKUP / filename).read_bytes(), data)
            self.assertFalse((game / ROTATION).exists())

    def test_server_upgrade_cleans_old_mods_and_preserves_eula(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "pack.mrpack"
            filename, data, _ = fixture_pack(pack)
            server = root / "server"
            mods = server / "mods"
            mods.mkdir(parents=True)
            (server / "TECHQUEST_README.txt").write_text("managed")
            (mods / RPG).write_bytes(b"legacy")
            (mods / PMMO).write_bytes(b"legacy")
            (server / "eula.txt").write_text("eula=false\n")
            (server / "world").mkdir()
            (server / "world" / "level.dat").write_bytes(b"world")
            with patch.object(build_pack, "download_checked",
                              side_effect=lambda record, dest: (dest / filename).write_bytes(data)):
                install_server.install_pack(pack, server, skip_neoforge=True)
            self.assertTrue((mods / COMPAT).is_file())
            self.assertEqual((mods / filename).read_bytes(), data)
            self.assertFalse((mods / RPG).exists())
            self.assertFalse((mods / PMMO).exists())
            self.assertTrue((server / BACKUP / RPG).exists())
            self.assertEqual((server / "eula.txt").read_text(), "eula=false\n")
            self.assertEqual((server / "world" / "level.dat").read_bytes(), b"world")

    def test_injected_failure_restores_active_and_old_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active, backup = root / "mods", root / BACKUP
            active.mkdir()
            backup.mkdir()
            (active / "current.jar").write_bytes(b"current")
            (backup / RPG).write_bytes(b"prior")
            staged = root / ".staged"
            staged.mkdir()
            (staged / "failed.jar").write_bytes(b"failed")
            def fail():
                raise RuntimeError("injected-failure")
            with self.assertRaisesRegex(RuntimeError, "injected-failure"):
                activate_staged_mods(root, staged, fail)
            self.assertEqual((active / "current.jar").read_bytes(), b"current")
            self.assertFalse((active / "failed.jar").exists())
            self.assertEqual((backup / RPG).read_bytes(), b"prior")
            self.assertTrue((staged / "failed.jar").is_file())
            self.assertFalse((root / ROTATION).exists())

    def test_unknown_profile_and_bad_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "pack.mrpack"
            filename, data, _ = fixture_pack(pack)
            unknown = root / "unknown"
            mods = unknown / "mods"
            mods.mkdir(parents=True)
            (mods / "personal.jar").write_bytes(b"mine")
            with self.assertRaisesRegex(build_pack.BuildError, "managed"):
                install_client.install(pack, unknown)
            self.assertEqual((mods / "personal.jar").read_bytes(), b"mine")
            with zipfile.ZipFile(pack) as z:
                index = json.loads(z.read("modrinth.index.json"))
            index["files"][0]["path"] = "mods/" + RPG
            corrupt = root / "bad.mrpack"
            with zipfile.ZipFile(corrupt, "w") as z:
                z.writestr("modrinth.index.json", json.dumps(index))
                z.writestr("overrides/mods/" + COMPAT, build_pack.compatibility_jar())
            with self.assertRaisesRegex(build_pack.BuildError, "Removed mod"):
                install_client.install(corrupt, root / "new-client")
            with self.assertRaisesRegex(build_pack.BuildError, "Removed mod"):
                install_server.install_pack(corrupt, root / "new-server", skip_neoforge=True)


if __name__ == "__main__":
    unittest.main()

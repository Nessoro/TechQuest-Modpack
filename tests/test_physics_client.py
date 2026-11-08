"""Keep the experimental debris mod and its singleplayer settings off servers."""
import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import build_pack as builder
from scripts import install_client, install_server


ROOT = Path(__file__).resolve().parents[1]


class PhysicsClientTests(unittest.TestCase):
    def setUp(self):
        self.cfg = builder.load_cfg()
        self.entry = next(m for m in self.cfg["mods"] if m["project"] == "physicsmod")

    def test_exact_version_is_client_only_through_resolver_pack_and_installers(self):
        snapshot = json.loads((ROOT / "experiments/destruction/candidates.json").read_text())
        candidate = next(c for c in snapshot["candidates"] if c["version_id"] == "wudTG1nk")
        file = candidate["verified_files"][0]
        version = {"id": "wudTG1nk", "version_number": "3.0.35", "version_type": "release",
                   "date_published": "2026-01-01", "files": [file], "dependencies": []}

        def metadata(path, args=None):
            if path.endswith("/version"):
                return [dict(version, id="newer-unreviewed", version_number="9.9.9"), version]
            # Even a changed generic project-side tag must not install this mod on servers.
            return {"id": "Xy8aRQKS", "title": "Physics Mod", "project_type": "mod",
                    "client_side": "required", "server_side": "required"}

        cfg = dict(self.cfg, mods=[self.entry], modrinth_lock={})
        with patch.object(builder, "get_json", side_effect=metadata):
            records, skipped = builder.resolve_manifest(cfg)
        self.assertFalse(skipped)
        self.assertEqual(records[0]["version_id"], "wudTG1nk")
        self.assertEqual(records[0]["environment"], {"client": "required", "server": "unsupported"})
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "test.mrpack"
            builder.make_mrpack(cfg, records, pack)
            with zipfile.ZipFile(pack) as archive:
                index = json.loads(archive.read("modrinth.index.json"))
            self.assertEqual(install_client.client_records(index)[0]["file"]["filename"], file["filename"])
            self.assertEqual(list(install_server.server_records(index)), [])

    def test_client_presets_are_identical_preserved_and_excluded_from_server(self):
        expected = builder.client_config_overrides(self.cfg)
        physics = json.loads(expected["config/physicsmod/physics_client_config.json"])
        self.assertTrue(physics["quickSetupNormalComplete"])
        self.assertTrue(physics["quickSetupProCompleteV2"])
        self.assertFalse(physics["oceanPhysics"])
        self.assertFalse(physics["liquidPhysics"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "test.mrpack"
            builder.make_mrpack(self.cfg, [], pack)
            with zipfile.ZipFile(pack, "a") as archive:
                archive.writestr("overrides/config/physicsmod/unreviewed.json", "untrusted")
            with zipfile.ZipFile(pack) as archive:
                install_client.install_guide_overrides(archive, root / "client")
                for relative, data in expected.items():
                    self.assertEqual(archive.read("overrides/" + relative), data)
                    target = root / "client" / relative
                    self.assertEqual(target.read_bytes(), data)
                    target.write_bytes(b"existing-player-config")
                install_client.install_guide_overrides(archive, root / "client")
            for relative in expected:
                self.assertEqual((root / "client" / relative).read_bytes(), b"existing-player-config")
            self.assertFalse((root / "client/config/physicsmod/unreviewed.json").exists())
            install_server.install_guide_overrides(pack, root / "server")
            self.assertFalse((root / "server/config/physicsmod").exists())
            local_server = json.loads(expected["config/physicsmod/physics_server_config.json"])
            self.assertFalse(local_server["collapse"])

    def test_presets_require_the_reviewed_mod_version_and_side(self):
        without_physics = dict(self.cfg, mods=[])
        self.assertFalse(any("physicsmod/" in path for path in builder.client_config_overrides(without_physics)))
        for changes in ({"version_id": "unreviewed"}, {"client_only": False}):
            cfg = copy.deepcopy(self.cfg)
            next(m for m in cfg["mods"] if m["project"] == "physicsmod").update(changes)
            with self.assertRaisesRegex(builder.BuildError, "Review Physics Mod"):
                builder.client_config_overrides(cfg)


if __name__ == "__main__":
    unittest.main()

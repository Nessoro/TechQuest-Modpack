"""Deliver reviewed HUD/blast settings consistently, preserving player files."""
import copy
import json
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

import build_pack as builder
from scripts import install_client, install_server


class HudBlastPresets(unittest.TestCase):
    def test_all_client_presets_arrive_without_overwriting_player_settings(self):
        cfg = builder.load_cfg()
        expected = builder.client_config_overrides(cfg)
        health = json.loads(expected["config/healthindicatortxf.json5"])
        self.assertTrue(health["showHealth"])
        self.assertEqual(health["healthTextFormat"], "BOTH")
        self.assertEqual(health["position"], "TOP_CENTER")
        self.assertEqual(json.loads(expected["config/jade/plugins.json"])["minecraft"],
                         {"entity_health": False, "entity_armor": False})
        self.assertIn("config/explosionoverhaul/explosionoverhaul-client.toml", expected)
        concussion = tomllib.loads(expected["config/explosionoverhaul/explosionoverhaul-client.toml"].decode())
        self.assertEqual(concussion["Wind System"]["Concussion"]["concussionDurationMultiplier"], 0.25)
        self.assertNotIn("Concussion", concussion)
        self.assertNotIn("config/explosionoverhaul-client.toml", expected)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "test.mrpack"
            builder.make_mrpack(cfg, [], pack)
            with zipfile.ZipFile(pack, "a") as archive:
                archive.writestr("overrides/config/jade/arbitrary.json", "untrusted")
            with zipfile.ZipFile(pack) as archive:
                install_client.install_guide_overrides(archive, root / "client")
                for relative, data in expected.items():
                    target = root / "client" / relative
                    self.assertEqual(target.read_bytes(), data)
                    target.write_bytes(b"player-custom-settings")
                install_client.install_guide_overrides(archive, root / "client")
                for relative in expected:
                    self.assertEqual((root / "client" / relative).read_bytes(), b"player-custom-settings")
            self.assertFalse((root / "client/config/jade/arbitrary.json").exists())
            install_server.install_guide_overrides(pack, root / "server")
            for relative in expected:
                self.assertFalse((root / "server" / relative).exists(), relative)

    def test_changed_jar_version_requires_review_of_config_schema(self):
        for project in ("N56hoqkq", "nvQzSEkH", "sOxnTLKl"):
            cfg = copy.deepcopy(builder.load_cfg())
            cfg["modrinth_lock"][project]["version_id"] = "unreviewed"
            with self.assertRaisesRegex(builder.BuildError, "Review HUD/blast"):
                builder.client_config_overrides(cfg)
        cfg = copy.deepcopy(builder.load_cfg())
        cfg["external_mods"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(builder.BuildError, "Review Incoming"):
            builder.client_config_overrides(cfg)

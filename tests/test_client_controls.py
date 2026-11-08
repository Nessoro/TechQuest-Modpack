import json
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import build_pack
from scripts import audit_keybinds, install_client, install_server

ROOT = Path(__file__).resolve().parents[1]


class ClientControlsTests(unittest.TestCase):
    def test_client_only_and_side_overrides_survive_dependency_id_aliases(self):
        for reviewed, published, expected in (
            ({"client_only": True}, {"client_side": "required", "server_side": "required"},
             {"client": "required", "server": "unsupported"}),
            ({"environment": {"client": "required", "server": "required"}},
             {"client_side": "unsupported", "server_side": "required"},
             {"client": "required", "server": "required"}),
        ):
            def api(path, args=None):
                project = path.split("/")[2]
                library = project in ("library", "LibraryID")
                if path.endswith("/version"):
                    return [{"id": "library-version" if library else "parent-version",
                             "version_number": "1.0", "version_type": "release", "date_published": "2026-01-01",
                             "files": [{"filename": project + ".jar", "hashes": {"sha1": "a" * 40}}],
                             "dependencies": [] if library else [{"project_id": "LibraryID", "dependency_type": "required"}]}]
                return {"id": "LibraryID" if library else "ParentID", "title": project, "project_type": "mod",
                        **(published if library else {"client_side": "required", "server_side": "required"})}
            cfg = {"minecraft": "1.21.1", "loader": "neoforge", "mods": [
                {"project": "parent", "version_id": "parent-version"},
                {"project": "library", "version_id": "library-version", **reviewed}]}
            with patch.object(build_pack, "get_json", side_effect=api):
                records, _ = build_pack.resolve_manifest(cfg)
            self.assertEqual(next(r for r in records if r["id"] == "LibraryID")["environment"], expected)

    def test_client_manifest_settings_and_preservation_across_install_paths(self):
        cfg = build_pack.load_cfg()
        snapshot = json.loads((ROOT / "compat/client-controls/verified-mods.json").read_text())
        entries = {m["project"]: m for m in cfg["mods"]}
        records = []
        for item in snapshot["mods"]:
            entry = entries[item["project"]]
            self.assertEqual(entry["version_id"], item["version_id"])
            self.assertTrue(entry["client_only"])
            records.append({"filename": item["file"]["filename"], "file": item["file"],
                            "environment": {"client": "required", "server": "unsupported"}})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "pack.mrpack"
            build_pack.make_mrpack(cfg, records, pack)
            with zipfile.ZipFile(pack) as archive:
                index = json.loads(archive.read("modrinth.index.json"))
                self.assertEqual(len(install_client.client_records(index)), 3)
                self.assertEqual(list(install_server.server_records(index)), [])
                options = archive.read("overrides/options.txt")
                self.assertEqual(options, build_pack.client_options(cfg))
                self.assertTrue(options.startswith(b"version:3955\n"))
                self.assertIn(b"key_key.betterzoom.zoom:key.keyboard.z\n", options)
                self.assertIn(b"key_gui.xaero_enlarge_map:key.keyboard.f9\n", options)
                preset = tomllib.loads(archive.read("overrides/config/betterzoom-client.toml").decode())
                self.assertTrue(preset["holdToZoom"])
                self.assertTrue(preset["smoothZoom"])
                self.assertEqual(preset["zoomMode"], "WHEEL")
                self.assertFalse(preset["hideGui"])
                install_client.install_guide_overrides(archive, root / "client")
                (root / "client/options.txt").write_text("player-options")
                target = root / "client/config/betterzoom-client.toml"
                target.write_text("player-zoom-options")
                install_client.install_guide_overrides(archive, root / "client")
                self.assertEqual((root / "client/options.txt").read_text(), "player-options")
                self.assertEqual(target.read_text(), "player-zoom-options")
            install_server.install_guide_overrides(pack, root / "server")
            self.assertFalse((root / "server/config/betterzoom-client.toml").exists())

    def test_static_report_keeps_unknowns_and_verifies_only_observed_zoom_bindings(self):
        overrides = build_pack.load_cfg()["performance_profile"]["key_defaults"]
        rows = [{"id": name, "code": code, "modifier": None, "input": None, "context": None,
                 "origin": "fixture.jar", "method": "Fixture"}
                for name, code in (("key.betterzoom.zoom", 67),
                                   ("gui.xaero_enlarge_map", 90),
                                   ("key.sophisticatedbackpacks.toggle_upgrade_1", 90), (None, None))]
        rows[-2]["modifier"] = "ALT"
        report = audit_keybinds.analyze(rows, overrides)
        audit_keybinds.verify_zoom(report)
        self.assertFalse(report["runtime_verified"])
        self.assertEqual(report["constructors"], 4)
        self.assertEqual(report["resolved"], 3)
        self.assertFalse(report["bindings"][-1]["resolved"])
        self.assertEqual(report["bindings"][-2]["default_modifier"], "ALT")
        self.assertEqual(report["bindings"][-2]["modifier"], "NONE")
        rows.append(dict(rows[0], id="another.mod.zoom", code=90))
        with self.assertRaisesRegex(ValueError, "Other observed bindings"):
            audit_keybinds.verify_zoom(audit_keybinds.analyze(rows, overrides))
        rows[-1] = dict(rows[-1], id=None)
        with self.assertRaisesRegex(ValueError, "Unresolved constructor"):
            audit_keybinds.verify_zoom(audit_keybinds.analyze(rows, overrides))

    def test_options_header_is_not_silently_reused_for_another_game_version(self):
        with self.assertRaisesRegex(build_pack.BuildError, "DataVersion"):
            build_pack.client_options({"minecraft": "different", "performance_profile": {"video_defaults": {"renderDistance": 6}}})

    def test_zoom_preset_requires_reviewed_version(self):
        cfg = {"mods": [{"project": "better-zoom", "client_only": True, "version_id": "unreviewed"}]}
        with self.assertRaisesRegex(build_pack.BuildError, "Review Better Zoom"):
            build_pack.client_config_overrides(cfg)


if __name__ == "__main__":
    unittest.main()

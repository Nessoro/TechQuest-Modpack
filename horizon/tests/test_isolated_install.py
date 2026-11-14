"""Prevent mismatched content and accidental starts against changed installations."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import install_isolated_server as installer


class IsolatedInstallTests(unittest.TestCase):
    def installation(self, root):
        root.mkdir()
        (root / "server.toml").write_text(
            '[server]\nbind="127.0.0.1"\nonline_mode=true\nwhitelist=true\n'
            '[world]\nname="' + installer.WORLD + '"\n'
            '[engine]\nrestart_on_crash=false\n[panel]\nbind=""\n')
        for name in ("ops.json", "whitelist.json"):
            (root / name).write_text("[]")
        mods = root / "horizon-mods"
        mods.mkdir()
        for mod in installer.MODULES:
            (mods / f"{mod}.hmod").write_bytes(b"fixture, never executed")
        pack = root / installer.PACK
        pack.mkdir(parents=True)
        (pack / "pack.mcmeta").write_text("{}")
        external = root.parent / "fixture-server"
        external.write_bytes(b"fixture, never executed")
        names = ["server.toml", f"{installer.PACK}/pack.mcmeta"]
        names += [f"horizon-mods/{mod}.hmod" for mod in installer.MODULES]
        report = {
            "schema": 1, "minecraft": "26.3", "upstream_commit": installer.UPSTREAM,
            "world": installer.WORLD, "modules": dict.fromkeys(installer.MODULES, {}),
            "files": {name: installer.digest(root / name) for name in names},
            "external_files": {str(external): installer.digest(external)}, "server_binary": str(external),
        }
        (root / installer.LOCK).write_text(json.dumps(report))
        return root

    def test_changed_module_blocks_start_before_creating_home_or_spawning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.installation(Path(temp) / "server")
            (root / "horizon-mods/terralith.hmod").write_bytes(b"stale pre-adaptation module")
            with patch.object(installer.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "installed file changed"):
                    installer.start(root)
                run.assert_not_called()
            self.assertFalse((root / ".runs").exists())

    def test_extra_module_or_datapack_cannot_silently_change_content(self):
        for name in ("horizon-mods/extra.hmod", installer.PACK + "/extra.json",
                     installer.WORLD + "/datapacks/extra/pack.mcmeta"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = self.installation(Path(temp) / "server")
                extra = root / name
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text("{}")
                with self.assertRaises(ValueError):
                    installer.verify(root)

    def test_changed_external_engine_and_account_lists_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.installation(Path(temp) / "server")
            installer.verify(root)
            (root / "ops.json").write_text('[{"name":"ExistingPlayer"}]')
            with self.assertRaisesRegex(ValueError, "player accounts"):
                installer.verify(root)
            (root / "ops.json").write_text("[]")
            (root.parent / "fixture-server").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "external tool/resources changed"):
                installer.verify(root)

    def test_symlink_inside_datapack_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.installation(Path(temp) / "server")
            (root / installer.PACK / "extra.json").symlink_to(root / "ops.json")
            with self.assertRaisesRegex(ValueError, "symlink"):
                installer.verify(root)

    def test_mismatched_sdk_valid_terralith_and_pack_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "pack/data/terralith/worldgen/feature/tree.json"
            data.parent.mkdir(parents=True)
            data.write_text('{"current":true}')
            for mod in installer.MODULES:
                with zipfile.ZipFile(root / f"{mod}.hmod", "w") as archive:
                    archive.writestr("horizon-mod.toml", f'id="{mod}"\ncapabilities=["registries"]\n')
                    if mod == "terralith":
                        archive.writestr("data/terralith/worldgen/feature/tree.json", '{"stale":true}')
            def sdk(args, **kwargs):
                path = args[2]
                return json.dumps({"ok": True, "report": {"id": path.stem, "version": "fixture",
                    "api": "0.2", "side": "both", "sha256": installer.digest(path)}})
            with patch.object(installer, "run", side_effect=sdk):
                with self.assertRaisesRegex(ValueError, "hmod/datapack differ"):
                    installer.check_modules(root, root / "terralith.hmod", root / "pack", root / "sdk", root / "work")

    def test_sdk_valid_but_uncanonicalized_carried_tag_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            feature = "data/terralith/worldgen/feature/tree.json"
            tag = "data/minecraft/tags/block/nylium.json"
            for name in ("pack/" + feature, "work/mods/terralith/carry/" + tag):
                path = root / name
                path.parent.mkdir(parents=True)
                path.write_text('{}' if name.endswith("tree.json") else '{"values":["moss_block"]}')
            for mod in installer.MODULES:
                with zipfile.ZipFile(root / f"{mod}.hmod", "w") as archive:
                    archive.writestr("horizon-mod.toml", f'id="{mod}"\ncapabilities=["registries"]\n')
                    if mod == "terralith":
                        archive.writestr(feature, '{}')
                        archive.writestr(tag, '{"values":["moss_block"]}')
            def sdk(args, **kwargs):
                path = args[2]
                return json.dumps({"ok": True, "report": {"id": path.stem, "version": "fixture",
                    "api": "0.2", "side": "both", "sha256": installer.digest(path)}})
            with patch.object(installer, "run", side_effect=sdk):
                with self.assertRaisesRegex(ValueError, "block tags differ"):
                    installer.check_modules(root, root / "terralith.hmod", root / "pack", root / "sdk", root / "work")

    def test_each_start_environment_is_new_and_does_not_import_player_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.dict(os.environ, {"HORIZON_OP": "ExistingPlayer", "HORIZON_HOME": "/old",
                                         "HORIZON_ONLINE": "false"}):
                a = installer.fresh_environment(root / "a")
                b = installer.fresh_environment(root / "b")
            self.assertNotIn("HORIZON_OP", a)
            self.assertNotIn("HORIZON_ONLINE", a)
            for key in ("HORIZON_HOME", "HORIZON_LAUNCHER_HOME", "XDG_DATA_HOME", "XDG_CONFIG_HOME"):
                self.assertNotEqual(a[key], b[key])
                self.assertEqual(list(Path(a[key]).iterdir()), [])

    def test_existing_target_is_unchanged_before_any_external_command(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "existing"
            output.mkdir()
            marker = output / "level.dat"
            marker.write_bytes(b"existing world")
            with patch.object(installer.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "must be new"):
                    installer.install(**dict.fromkeys(("resources", "tools", "work", "modules", "terralith",
                        "datapack", "sdk", "upstream"), root / "input"), output=output, port=25600, accept_eula=True)
                run.assert_not_called()
            self.assertEqual(marker.read_bytes(), b"existing world")

    def test_trial_without_recipe_unlock_migration_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            pack = Path(temp) / "pack"
            pack.mkdir()
            (pack / "pack.mcmeta").write_text("{}")
            (pack / "techquest-worldgen-trial.json").write_text(json.dumps({"schema": 1,
                "minecraft": "26.3", "terralith": "2.6.2", "inlined_legacy_feature_references": 5,
                "deferred_patch_files": []}))
            with self.assertRaisesRegex(ValueError, "recipe unlocks"):
                installer.validate_trial(pack, Path(temp) / "work")

    def test_missing_or_changed_restored_advancement_cannot_hide_behind_trial_counts(self):
        for remove in (False, True):
            with self.subTest(remove=remove), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                pack, work = root / "pack", root / "work"
                pack.mkdir()
                (pack / "pack.mcmeta").write_text("{}")
                sources = []
                for name in sorted(installer.RECIPE_ADVANCEMENTS):
                    original = {"criteria": {"has_recipe": {"trigger": "minecraft:recipe_unlocked",
                        "conditions": {"recipe": "minecraft:" + Path(name).stem}}},
                        "rewards": {"recipes": ["minecraft:" + Path(name).stem, "terralith:" + Path(name).stem + "_alt"]}}
                    path = work / "mods/terralith/outside" / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(original))
                    sources.append({"section": "outside", "path": name, "sha256": installer.digest(path)})
                    original["criteria"]["has_recipe"]["conditions"] = {"recipes": "minecraft:" + Path(name).stem}
                    target = pack / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(json.dumps(original))
                (pack / "techquest-worldgen-trial.json").write_text(json.dumps({"schema": 1,
                    "minecraft": "26.3", "terralith": "2.6.2", "inlined_legacy_feature_references": 5,
                    "deferred_patch_files": [], "normalized_recipe_unlock_criteria": 5,
                    "selected_recipe_advancements": sorted(installer.RECIPE_ADVANCEMENTS),
                    "sources": sources, "input_files": 5}))
                installer.validate_trial(pack, work)
                target = pack / sorted(installer.RECIPE_ADVANCEMENTS)[0]
                if remove:
                    target.unlink()
                else:
                    value = json.loads(target.read_text())
                    value["rewards"]["recipes"] = []
                    target.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, "recipe advancement|advancement differs"):
                    installer.validate_trial(pack, work)


if __name__ == "__main__":
    unittest.main()

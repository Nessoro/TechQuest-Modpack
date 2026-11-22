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
    def test_redstone_content_requires_the_matching_native_version(self):
        mods = {"prettypipes": {"version": "0.8.0"}}
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            installer.check_native_pairs(mods, [{"id": "techquest_pretty_pipes", "version": "0.7.0"}])
        installer.check_native_pairs(mods, [{"id": "techquest_pretty_pipes", "version": "0.8.0"}])

    def test_silicon_route_rejects_old_machine_native_and_incomplete_core(self):
        mods = {"oritech": {"version": "0.3.0"}, "prettypipes": {"version": "0.7.0"}}
        native = [{"id": "techquest_oritech", "version": "0.2.0"},
                  {"id": "techquest_pretty_pipes", "version": "0.7.0"}]
        base = json.loads(installer.CORE_PATCH.read_text())
        runtime = json.loads(installer.WORLD_CORE_PATCH.read_text())
        installer.check_native_pairs(mods, native, [base, runtime])
        with self.assertRaisesRegex(ValueError, "world-pack feature correction"):
            installer.check_native_pairs(mods, native, [base])
        native[0]["version"] = "0.1.0"
        with self.assertRaisesRegex(ValueError, "Oritech content/native"):
            installer.check_native_pairs(mods, native, [base, runtime])
        native[0]["version"] = "0.2.0"
        native[1]["version"] = "0.6.0"
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            installer.check_native_pairs(mods, native, [base, runtime])

    def test_foundry_route_requires_current_machine_and_pipe_bundles(self):
        mods = {"oritech": {"version": "0.4.0"}, "prettypipes": {"version": "0.9.0"}}
        native = [{"id": "techquest_oritech", "version": "0.3.0"},
                  {"id": "techquest_pretty_pipes", "version": "0.9.0"}]
        core = [json.loads(installer.CORE_PATCH.read_text()),
                json.loads(installer.WORLD_CORE_PATCH.read_text())]
        installer.check_native_pairs(mods, native, core)
        with self.assertRaisesRegex(ValueError, "world-pack feature correction"):
            installer.check_native_pairs(mods, native, core[:1])
        native[0]["version"] = "0.2.0"
        with self.assertRaisesRegex(ValueError, "Oritech content/native"):
            installer.check_native_pairs(mods, native, core)
        native[0]["version"] = "0.3.0"
        native[1]["version"] = "0.8.0"
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            installer.check_native_pairs(mods, native, core)

    def test_assembler_rejects_three_slot_native_and_old_pipe_endpoint_bundle(self):
        mods = {"oritech": {"version": "0.5.0"}, "prettypipes": {"version": "0.10.0"}}
        native = [{"id": "techquest_oritech", "version": "0.4.0"},
                  {"id": "techquest_pretty_pipes", "version": "0.10.0"}]
        core = [json.loads(installer.CORE_PATCH.read_text()),
                json.loads(installer.WORLD_CORE_PATCH.read_text())]
        installer.check_native_pairs(mods, native, core)
        with self.assertRaisesRegex(ValueError, "world-pack feature correction"):
            installer.check_native_pairs(mods, native, core[:1])
        native[0]["version"] = "0.3.0"
        with self.assertRaisesRegex(ValueError, "Oritech content/native"):
            installer.check_native_pairs(mods, native, core)
        native[0]["version"] = "0.4.0"
        native[1]["version"] = "0.9.0"
        with self.assertRaisesRegex(ValueError, "version mismatch"):
            installer.check_native_pairs(mods, native, core)

    def test_new_progression_install_requires_runtime_fix_but_old_lock_remains_valid(self):
        mods = {"oritech": {"version": "0.2.0"}}
        native = [{"id": "techquest_oritech", "version": "0.1.0"}]
        base = json.loads(installer.CORE_PATCH.read_text())
        runtime = json.loads(installer.WORLD_CORE_PATCH.read_text())
        installer.check_native_pairs(mods, native, [base])
        with self.assertRaisesRegex(ValueError, "world-pack feature correction"):
            installer.check_native_pairs(mods, native, [base], new_installation=True)
        installer.check_native_pairs(mods, native, [base, runtime], new_installation=True)

    def test_changed_runtime_module_is_rejected_before_installation(self):
        base = json.loads(installer.CORE_PATCH.read_text())
        runtime = json.loads(installer.WORLD_CORE_PATCH.read_text())
        with tempfile.TemporaryDirectory() as temp:
            tools = Path(temp)
            (tools / "build-result.json").write_text(json.dumps({"core_patches": [base, runtime]}))
            for spec, origin in ((base, installer.CORE_PATCH.parent), (runtime, installer.WORLD_CORE_PATCH.parent)):
                root = tools / "core-patches" / spec["id"]
                root.mkdir(parents=True)
                for name in ("horizon-core-patch.json", spec.get("patch_file", "merged-biomes.patch")):
                    (root / name).write_bytes((origin / name).read_bytes())
                if "module_file" in spec:
                    (root / spec["module_file"]).write_bytes(b"unreviewed runtime source")
            with self.assertRaisesRegex(ValueError, "core correction module differs"):
                installer.check_core_patches(tools)

    def test_oritech_progression_needs_reviewed_core_before_start(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.installation(Path(temp) / "server")
            report = json.loads((root / installer.LOCK).read_text())
            report["modules"]["oritech"] = {"version": "0.2.0"}
            report["native_modules"] = [{"id": "techquest_oritech", "version": "0.1.0"}]
            (root / installer.LOCK).write_text(json.dumps(report))
            with patch.object(installer.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "merged-biome core correction"):
                    installer.start(root)
                run.assert_not_called()
        core = json.loads(installer.CORE_PATCH.read_text())
        installer.check_native_pairs({"oritech": {"version": "0.2.0"}},
                                     [{"id": "techquest_oritech", "version": "0.1.0"}], [core])
        core["patched_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "merged-biome core correction"):
            installer.check_native_pairs({"oritech": {"version": "0.2.0"}},
                                         [{"id": "techquest_oritech", "version": "0.1.0"}], [core])

    def test_oritech_mismatch_blocks_start_without_spawning(self):
        for native in ([], [{"id": "techquest_oritech", "version": "0.2.0"}]):
            with self.subTest(native=native), tempfile.TemporaryDirectory() as temp:
                root = self.installation(Path(temp) / "server")
                report = json.loads((root / installer.LOCK).read_text())
                report["modules"]["oritech"] = {"version": "0.1.0"}
                report["native_modules"] = native
                (root / installer.LOCK).write_text(json.dumps(report))
                with patch.object(installer.subprocess, "run") as run:
                    with self.assertRaisesRegex(ValueError, "Oritech content/native"):
                        installer.start(root)
                    run.assert_not_called()
                self.assertFalse((root / ".runs").exists())

    def test_mixed_pipe_versions_block_start_before_spawning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.installation(Path(temp) / "server")
            report = json.loads((root / installer.LOCK).read_text())
            report["modules"]["prettypipes"] = {"version": "0.2.0"}
            report["native_modules"] = [{"id": "techquest_pretty_pipes", "version": "0.1.0"}]
            (root / installer.LOCK).write_text(json.dumps(report))
            with patch.object(installer.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "version mismatch"):
                    installer.start(root)
                run.assert_not_called()
            self.assertFalse((root / ".runs").exists())

    def test_pipe_content_cannot_be_declared_without_native_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.installation(Path(temp) / "server")
            report = json.loads((root / installer.LOCK).read_text())
            report["modules"]["prettypipes"] = {}
            (root / installer.LOCK).write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "no native extension"):
                installer.verify(root)

    def test_unreviewed_seventh_module_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.installation(Path(temp) / "server")
            report = json.loads((root / installer.LOCK).read_text())
            report["modules"]["unknown_machine"] = {}
            (root / installer.LOCK).write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "unrecognized"):
                installer.verify(root)

    def test_changed_native_source_bundle_is_rejected_before_sdk(self):
        with tempfile.TemporaryDirectory() as temp:
            tools = Path(temp)
            package = tools / "native-mods/example.hnmod"
            package.parent.mkdir()
            package.write_bytes(b"changed local native source")
            (tools / "build-result.json").write_text(json.dumps({"native_mods": [{
                "id": "example", "version": "1", "mixins_commit": "a" * 40, "sha256": "0" * 64}]}))
            with patch.object(installer, "run") as sdk:
                with self.assertRaisesRegex(ValueError, "native source bundle checksum"):
                    installer.check_native_modules(tools, tools / "sdk")
                sdk.assert_not_called()

    def test_native_bundle_must_match_the_engines_declared_pins(self):
        with tempfile.TemporaryDirectory() as temp:
            tools = Path(temp)
            package = tools / "native-mods/example.hnmod"
            package.parent.mkdir()
            package.write_bytes(b"fixture source bundle")
            checksum = installer.digest(package)
            (tools / "build-result.json").write_text(json.dumps({"native_mods": [{
                "id": "example", "version": "1", "mixins_commit": "a" * 40, "sha256": checksum}]}))
            verdict = {"ok": True, "report": {"id": "example", "version": "1", "kind": "native-mod",
                "game": "26.3", "sha256": checksum, "api": f'native-1/{installer.UPSTREAM}/' + "b" * 40}}
            with patch.object(installer, "run", return_value=json.dumps(verdict)):
                with self.assertRaisesRegex(ValueError, "identity/pins"):
                    installer.check_native_modules(tools, tools / "sdk")

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

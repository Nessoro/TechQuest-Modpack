import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "terralith_content", Path(__file__).parents[1] / "tools/stage_terralith_content.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class TerralithContentTests(unittest.TestCase):
    def fixture(self, base):
        work, pack = base / "work", base / "pack"
        carry = work / "mods/terralith/carry"
        carry.mkdir(parents=True)
        (carry / "horizon-mod.toml").write_text(
            'id="terralith"\nversion="2.6.2"\napi="0.2"\nside="both"\ncapabilities=["registries"]\n')
        old = carry / "data/terralith/worldgen/configured_feature/tree.json"
        old.parent.mkdir(parents=True)
        old.write_text('{"legacy":true}')
        new = pack / "data/terralith/worldgen/feature/tree.json"
        new.parent.mkdir(parents=True)
        new.write_text('{"upgraded":true}')
        vanilla = pack / "data/minecraft/dimension/overworld.json"
        vanilla.parent.mkdir(parents=True)
        vanilla.write_text('{}')
        (pack / "techquest-worldgen-trial.json").write_text(
            '{"schema":1,"terralith":"2.6.2","minecraft":"26.3"}')
        return work, pack, old, new

    def fake_sdk(self, args, cwd, **kwargs):
        package = cwd / "target/horizon-mod/terralith.hmod"
        if args[1] == "build":
            package.parent.mkdir(parents=True)
            package.write_bytes(b"fixture-package")
            return SimpleNamespace(stdout="built")
        return SimpleNamespace(stdout=json.dumps({"ok": True, "report": {
            "id": "terralith", "version": "2.6.2", "api": "0.2", "side": "both",
            "sha256": hashlib.sha256(package.read_bytes()).hexdigest()}}))

    def test_replaces_deprecated_paths_without_changing_source_or_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            work, pack, old, new = self.fixture(base)
            original = old.read_bytes()
            with patch.object(module.subprocess, "run", side_effect=self.fake_sdk):
                report = module.stage(work, pack, base / "output", base / "sdk")
            output = base / "output"
            self.assertEqual(old.read_bytes(), original)
            self.assertEqual((output / new.relative_to(pack)).read_bytes(), new.read_bytes())
            self.assertFalse((output / "data/terralith/worldgen/configured_feature/tree.json").exists())
            self.assertFalse((output / "data/minecraft").exists())
            self.assertEqual((output / "horizon-mod.toml").read_bytes(),
                             (work / "mods/terralith/carry/horizon-mod.toml").read_bytes())
            self.assertFalse(report["namespace_ownership_changed"])
            self.assertFalse(report["server_boot_tested"])
            self.assertTrue(report["world_datapack_still_required"])

    def test_missing_replacement_is_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            work, pack, _, new = self.fixture(base)
            new.rename(new.with_name("different.json"))
            with self.assertRaises(ValueError):
                module.stage(work, pack, base / "output", base / "sdk")
            self.assertFalse((base / "output").exists())

    def test_sdk_failure_does_not_leave_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            work, pack, _, _ = self.fixture(base)
            with patch.object(module.subprocess, "run",
                              side_effect=subprocess.CalledProcessError(2, "sdk")):
                with self.assertRaises(subprocess.CalledProcessError):
                    module.stage(work, pack, base / "output", base / "sdk")
            self.assertFalse((base / "output").exists())
            self.assertFalse(list(base.glob('.terralith-content-*')))

    def test_sdk_checksum_disagreement_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            work, pack, _, _ = self.fixture(base)
            def bad_check(args, **kwargs):
                result = self.fake_sdk(args, **kwargs)
                if args[1] == "check":
                    data = json.loads(result.stdout)
                    data["report"]["sha256"] = "0" * 64
                    result.stdout = json.dumps(data)
                return result
            with patch.object(module.subprocess, "run", side_effect=bad_check):
                with self.assertRaises(ValueError):
                    module.stage(work, pack, base / "output", base / "sdk")
            self.assertFalse((base / "output").exists())

    def test_new_directory_inside_existing_world_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "level.dat").write_bytes(b"preserve")
            with self.assertRaises(ValueError):
                module.stage(base / "work", base / "pack", base / "new-content", base / "sdk")
            self.assertEqual((base / "level.dat").read_bytes(), b"preserve")

    def test_new_output_cannot_pollute_the_datapack(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory)
            with self.assertRaises(ValueError):
                module.stage(pack / "work", pack, pack / "new-content", pack / "sdk")
            self.assertFalse((pack / "new-content").exists())

    def test_prepared_resources_cannot_become_an_output_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory)
            (resources / "horizon-resources.json").write_text('{}')
            with self.assertRaises(ValueError):
                module.stage(resources / "work", resources / "pack", resources / "derived", resources / "sdk")
            self.assertFalse((resources / "derived").exists())

    def test_symlink_in_adapted_namespace_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            work, pack, old, new = self.fixture(base)
            new.unlink()
            new.symlink_to(old)
            with self.assertRaises(ValueError):
                module.stage(work, pack, base / "output", base / "sdk")
            self.assertFalse((base / "output").exists())


if __name__ == "__main__":
    unittest.main()

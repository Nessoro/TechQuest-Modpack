import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("compat_builder", ROOT / "build_pack.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
spec = importlib.util.spec_from_file_location("compat_installer", ROOT / "scripts/install_server.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class CompatibilityTests(unittest.TestCase):
    def test_rebuild_removes_old_sodium_without_removing_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("sodium-0.8.13.jar", "sodium-0.6.13.jar", "README.txt"):
                (root / name).write_text("fixture")
            builder.remove_stale_generated_jars(root, {"sodium-0.6.13.jar"})
            self.assertEqual({p.name for p in root.iterdir()}, {"sodium-0.6.13.jar", "README.txt"})

    def test_pack_and_server_install_preserve_recipe_fix(self):
        cfg = {"version": "test", "pack_name": "Test", "description": "Test",
               "minecraft": "1.21.1", "loader_version": "21.1.259"}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "test.mrpack"
            builder.make_mrpack(cfg, [], pack)
            mods = root / "mods"
            mods.mkdir()
            installer.install_compatibility(pack, mods)
            with zipfile.ZipFile(mods / builder.COMPAT_JAR_NAME) as jar:
                for method in ("smelting", "blasting"):
                    for metal in ("tin", "silver", "uranium"):
                        recipe = json.loads(jar.read(
                            f"data/create/recipe/{method}/ingot_{metal}_compat_ic2.json"))
                        self.assertEqual(recipe["result"]["id"], f"ic2:{metal}_ingot")
                    disabled = json.loads(jar.read(
                        f"data/create/recipe/{method}/ingot_aluminium_compat_ic2.json"))
                    self.assertEqual(disabled["neoforge:conditions"], [{"type": "neoforge:false"}])
            self.assertEqual((mods / builder.COMPAT_JAR_NAME).read_bytes(), builder.compatibility_jar())

    def test_server_patch_changes_only_common_mixin_list_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "superbwarfare-0.8.9.2-mc1.21.1-test.jar"
            config = {"mixins": ["LevelMixin", "ClientLevelMixin"], "client": ["ClientLevelMixin"]}
            original_class = b"unchanged-class-bytes"
            with zipfile.ZipFile(path, "w") as jar:
                jar.writestr("mixins.superbwarfare.json", json.dumps(config))
                jar.writestr("example.class", original_class)
            self.assertTrue(builder.patch_superb_server_jar(path))
            once = path.read_bytes()
            self.assertFalse(builder.patch_superb_server_jar(path))
            self.assertEqual(path.read_bytes(), once)
            with zipfile.ZipFile(path) as jar:
                patched = json.loads(jar.read("mixins.superbwarfare.json"))
                self.assertEqual(patched["mixins"], ["LevelMixin"])
                self.assertEqual(patched["client"], ["ClientLevelMixin"])
                self.assertEqual(jar.read("example.class"), original_class)

    def test_installer_writes_separate_property_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installer.prepare_properties(root)
            lines = (root / "server.properties").read_text().splitlines()
            self.assertIn("online-mode=true", lines)
            self.assertIn("enforce-whitelist=true", lines)
            self.assertFalse(any("\\n" in line for line in lines))


class ExactDependencyTests(unittest.TestCase):
    def version(self, project, version_id, number, date, deps=()):
        return {"id": version_id, "project_id": project, "version_number": number,
                "version_type": "release", "date_published": date,
                "dependencies": list(deps), "files": [{"filename": project + "-" + version_id + ".jar",
                "url": "https://example.org/mod.jar", "primary": True,
                "size": 2048, "hashes": {"sha1": "a" * 40}}]}

    def fixture(self):
        versions = {
            "iris": [self.version("iris", "iris-fixed", "1.8.12", "2026-01-01",
                     [{"dependency_type": "required", "project_id": "sodium", "version_id": "sodium-old"}])],
            "sodium": [self.version("sodium", "sodium-new", "0.8.13", "2026-02-01"),
                       self.version("sodium", "sodium-old", "0.6.13", "2025-01-01")],
        }
        def fetch(path, args=None):
            parts = path.split("/")
            slug = parts[2]
            if path.endswith("/version"):
                return versions[slug]
            return {"id": slug, "title": slug, "project_type": "mod"}
        return fetch

    def test_uses_required_version_id_instead_of_latest(self):
        cfg = {"loader": "neoforge", "minecraft": "1.21.1", "mods": [{"project": "iris"}]}
        with patch.object(builder, "get_json", side_effect=self.fixture()):
            result, skipped = builder.resolve_manifest(cfg)
        self.assertFalse(skipped)
        self.assertEqual(next(m["version_id"] for m in result if m["id"] == "sodium"), "sodium-old")

    def test_conflicting_exact_pins_fail_instead_of_emitting_broken_pack(self):
        cfg = {"loader": "neoforge", "minecraft": "1.21.1", "mods": [
            {"project": "sodium", "version_id": "sodium-new"}, {"project": "iris"}]}
        with patch.object(builder, "get_json", side_effect=self.fixture()):
            with self.assertRaisesRegex(builder.BuildError, "Exact dependency conflict"):
                builder.resolve_manifest(cfg)

    def test_pinned_version_not_in_compatible_results_is_rejected(self):
        cfg = {"loader": "neoforge", "minecraft": "1.21.1", "mods": [
            {"project": "sodium", "version_id": "wrong-minecraft-version"}]}
        with patch.object(builder, "get_json", side_effect=self.fixture()):
            with self.assertRaises(builder.BuildError):
                builder.resolve_manifest(cfg)


if __name__ == "__main__":
    unittest.main()

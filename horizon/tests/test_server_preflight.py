"""Guard failures must remain read-only; fixtures are not Minecraft resources."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import server_preflight as preflight


class ServerPreflightTests(unittest.TestCase):
    def fixture(self, root):
        resources, tools, work, target = (root / x for x in ("resources", "tools", "work", "server"))
        resources.mkdir()
        tools.mkdir()
        meta = {"minecraft": "26.3", "schema": 7}
        for name in ("facts.json", "block-tags.json", "registries.json", "commands.json"):
            (resources / name).write_text("{}")
        for name, key in (("facts.json", "facts_sha256"), ("block-tags.json", "block_tags_sha256")):
            meta[key] = preflight.digest(resources / name)
        (resources / "horizon-resources.json").write_text(json.dumps(meta))
        (resources / "horizon-prepare.json").write_text('{"output_version":3}')
        for name in ("font", "textures"):
            folder = resources / "assets/minecraft" / name
            folder.mkdir(parents=True)
            (folder / "fixture").write_text("fixture only")
        hashes = {}
        for name in preflight.BINARIES:
            (tools / name).write_text("fixture, never executed")
            hashes[name] = preflight.digest(tools / name)
        (tools / "build-result.json").write_text(json.dumps({
            "upstream_commit": preflight.UPSTREAM, "minecraft": "26.3",
            "platform": "linux-x86_64", "default_features": False, "sha256": hashes,
        }))
        for mod_id in preflight.MODULES:
            folder = work / "mods" / mod_id / "carry"
            folder.mkdir(parents=True)
            (folder / "horizon-mod.toml").write_text(
                f'id="{mod_id}"\napi="0.2"\nside="both"\ncapabilities=["registries"]\n')
        return resources, tools, work, target

    def test_missing_inputs_cannot_create_server_or_accept_eula(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = preflight.inspect(*(root / x for x in ("r", "t", "w", "s")))
            self.assertFalse(report["preflight_passed"])
            self.assertFalse(report["eula_consent_provided"])
            self.assertEqual(list(root.iterdir()), [])

    def test_fixture_pass_does_not_claim_runtime_or_write_world(self):
        with tempfile.TemporaryDirectory() as temp:
            args = self.fixture(Path(temp))
            self.assertFalse(preflight.inspect(*args)["preflight_passed"])
            report = preflight.inspect(*args, accept_eula=True)
            self.assertTrue(report["preflight_passed"], report)
            for field in ("resources_fully_validated", "ownership_verified", "server_boot_tested",
                          "combined_mod_load_tested", "world_save_reopen_tested", "gameplay_ported"):
                self.assertFalse(report[field])
            self.assertFalse(args[-1].exists())

    def test_wrong_version_damage_and_missing_module_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            resources, tools, work, target = self.fixture(Path(temp))
            (resources / "facts.json").write_text("damaged")
            (tools / "horizon-engine").write_text("changed")
            (work / "mods/terralith/carry/horizon-mod.toml").unlink()
            report = preflight.inspect(resources, tools, work, target, True)
            self.assertFalse(report["preflight_passed"])
            self.assertTrue(any("resource checksum differs" in p for p in report["problems"]))
            self.assertTrue(any("native tool checksum differs" in p for p in report["problems"]))
            self.assertTrue(any("terralith" in p for p in report["problems"]))
            meta = json.loads((resources / "horizon-resources.json").read_text())
            meta["minecraft"] = "1.21.1"
            (resources / "horizon-resources.json").write_text(json.dumps(meta))
            self.assertTrue(any("26.3" in p for p in preflight.inspect(
                resources, tools, work, target, True)["problems"]))

    def test_existing_server_and_source_overlap_are_rejected_without_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            resources, tools, work, target = self.fixture(Path(temp))
            target.mkdir()
            (target / "level.dat").write_bytes(b"existing world")
            self.assertFalse(preflight.inspect(resources, tools, work, target, True)["preflight_passed"])
            self.assertEqual((target / "level.dat").read_bytes(), b"existing world")
            self.assertFalse(preflight.inspect(resources, tools, work, resources / "server", True)
                             ["preflight_passed"])
            link = Path(temp) / "server-link"
            link.symlink_to(target, target_is_directory=True)
            self.assertFalse(preflight.inspect(resources, tools, work, link, True)["preflight_passed"])

    def test_shared_namespace_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            resources, tools, work, target = self.fixture(Path(temp))
            for mod_id in ("betterdungeons", "betterfortresses"):
                path = work / "mods" / mod_id / "carry/horizon-mod.toml"
                with path.open("a") as stream:
                    stream.write('namespaces=["yungsapi"]\n')
            report = preflight.inspect(resources, tools, work, target, True)
            self.assertIn("namespace has multiple owners: yungsapi", report["problems"])


if __name__ == "__main__":
    unittest.main()

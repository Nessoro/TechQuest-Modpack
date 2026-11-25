"""TechQuest 0.3.3.4: boss-only entity tracking and conservative range migration."""
import io
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts import cataclysm_range, install_client, install_server

ROOT = Path(__file__).resolve().parents[1]
CLASS = "techquest/compat/mixin/BossTrackingRangeMixin.class"
SOURCE = ROOT / "compat/hotfix-src" / CLASS.replace(".class", ".java")
BINARY = ROOT / "compat/techquest-compat" / CLASS
STUBS = ROOT / "compat/hotfix-stubs"
BOSSES = {
    "ender_golem", "ender_guardian", "netherite_monstrosity", "ignis",
    "the_harbinger", "the_leviathan", "ancient_remnant",
    "scylla", "clawdian", "maledictus", "the_prowler",
}

class BossTrackingTests(unittest.TestCase):
    def test_mixin_is_shared_and_only_cataclysm_bosses(self):
        config = json.loads((ROOT / "compat/techquest-compat/techquest-compat.mixins.json").read_text())
        self.assertIn("BossTrackingRangeMixin", config["mixins"])
        self.assertIn("BetterZoomEarlyTickMixin", config["client"])
        source = SOURCE.read_text()
        self.assertIn('method = "clientTrackingRange()I"', source)
        self.assertIn('!"cataclysm".equals(id.getNamespace())', source)
        self.assertIn("TECHQUEST_BOSS_TRACKING_CHUNKS = 14", source)
        import re
        self.assertEqual(set(re.findall(r'"([a-z_]+)"\s*(?:,|->)', source)) & BOSSES, BOSSES)
        for forbidden in ("zombie", "skeleton", "ender_guardian_bullet", "ender_golem_spawn_egg"):
            self.assertNotIn('case "' + forbidden + '"', source)
        self.assertNotIn("bypasses_invulnerability", source)

    def test_bytecode_is_reproducible_with_java21(self):
        javac = shutil.which("javac")
        if not javac:
            self.skipTest("JDK 21 not installed; CI installs Temurin 21")
        stubs = sorted(STUBS.rglob("*.java"))
        self.assertEqual(8, len(stubs))
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([javac, "--release", "21", "-d", tmp,
                            *(str(path) for path in stubs), str(SOURCE)],
                           check=True, capture_output=True, text=True)
            compiled = Path(tmp) / CLASS
            self.assertEqual(BINARY.read_bytes(), compiled.read_bytes())

    def test_packaged_for_client_and_server(self):
        data = BINARY.read_bytes()
        self.assertTrue(data.startswith(bytes.fromhex("cafebabe")))
        compat = build_pack.compatibility_jar()
        with zipfile.ZipFile(io.BytesIO(compat)) as jar:
            self.assertEqual(jar.read(CLASS), data)
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack.mrpack"
            build_pack.make_mrpack(build_pack.load_cfg(), [], pack)
            with zipfile.ZipFile(pack) as jar:
                self.assertEqual(jar.read("overrides/mods/" + build_pack.COMPAT_JAR_NAME), compat)

    def test_default_range_migration_preserves_custom_values_and_backup(self):
        original = ("[mobs.ender_golem.cap_config]\n"
                    "damage_cap = 1234.0\nrange_cap = 8.0\n"
                    "[mobs.ender_guardian.cap_config]\nrange_cap = 12.0\n"
                    "[mobs.ignis.cap_config]\nrange_cap = 95.0\n"
                    "[mobs.prowler]\nrange_cap = 15.0\n"
                    "[mobs.not_a_boss.cap_config]\nrange_cap = 8.0\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cataclysm-common.toml"
            path.write_text(original)
            self.assertTrue(cataclysm_range.migrate_default_boss_ranges(path))
            changed = path.read_text()
            self.assertIn("damage_cap = 1234.0", changed)
            self.assertIn("[mobs.ignis.cap_config]\nrange_cap = 95.0", changed)
            self.assertIn("[mobs.prowler]\nrange_cap = 256.0", changed)
            self.assertIn("[mobs.not_a_boss.cap_config]\nrange_cap = 8.0", changed)
            self.assertEqual(changed.count("range_cap = 256.0"), 3)
            backup = path.with_name(path.name + ".techquest-before-0334.bak")
            self.assertEqual(backup.read_text(), original)
            self.assertFalse(cataclysm_range.migrate_default_boss_ranges(path))
            self.assertEqual(backup.read_text(), original)
            self.assertEqual(path.read_text(), changed)

    def test_client_and_server_upgrades_use_same_migration(self):
        cfg = build_pack.load_cfg()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "pack.mrpack"
            build_pack.make_mrpack(cfg, [], pack)
            old = "[mobs.ender_golem.cap_config]\nrange_cap = 8.0\n"
            for side in ("client", "server"):
                target = root / side
                config = target / "config/cataclysm-common.toml"
                config.parent.mkdir(parents=True)
                config.write_text(old)
                if side == "client":
                    with zipfile.ZipFile(pack) as archive:
                        install_client.install_guide_overrides(archive, target)
                else:
                    install_server.install_guide_overrides(pack, target)
                self.assertEqual(config.read_text(),
                                 "[mobs.ender_golem.cap_config]\nrange_cap = 256.0\n")
                self.assertEqual((config.with_name(config.name + ".techquest-before-0334.bak")).read_text(), old)

    def test_mixin_retained_in_classfile_not_runtime_visible(self):
        # Sponge Mixin scans RuntimeInvisibleAnnotations for @Mixin.
        # A RUNTIME-retained @Mixin stub compiles but fails the real client.
        stub = (STUBS / "org/spongepowered/asm/mixin/Mixin.java").read_text()
        self.assertIn("RetentionPolicy.CLASS", stub)
        self.assertNotIn("RetentionPolicy.RUNTIME", stub)
        javap = shutil.which("javap")
        if javap:
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / CLASS
                target.parent.mkdir(parents=True)
                target.write_bytes(BINARY.read_bytes())
                output = subprocess.check_output(
                    [javap, "-v", "-p", str(target)], text=True)
                invisible = output.split("RuntimeInvisibleAnnotations:")
                self.assertGreaterEqual(len(invisible), 2)
                self.assertIn("org.spongepowered.asm.mixin.Mixin", invisible[-1])

    def test_bootstrap_zips_copy_migration_helper(self):
        workflow = (ROOT / ".github/workflows/build-alpha.yml").read_text()
        self.assertEqual(
            workflow.count('z.write("scripts/cataclysm_range.py")'), 2)

    def test_gui_applies_migration_to_only_defaults(self):
        gui = (ROOT / "windows-installer/Program.cs").read_text()
        self.assertIn("MigrateCataclysmBossRangeCaps(gameDirectory)", gui)
        self.assertIn("File.Copy(configPath, backup, overwrite: false)", gui)
        self.assertIn("range_cap = 123.0", gui)  # Windows --self-test preserves user override
        self.assertNotIn("entity-broadcast-range-percentage=200", gui)


if __name__ == "__main__":
    unittest.main()

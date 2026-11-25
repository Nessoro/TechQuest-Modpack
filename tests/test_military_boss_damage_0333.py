"""Check scoped damage-type tag in the reproducible TechQuest Compatibility payload."""
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack

ROOT = Path(__file__).resolve().parents[1]
TAG = "data/cataclysm/tags/damage_type/bypasses_hurt_time.json"
EXPECTED = {
    "superbwarfare:gunfire", "superbwarfare:gunfire_headshot",
    "incoming:strike", "incoming:shockwave", "incoming:kinetic",
    "incoming:debris", "incoming:fragment", "incoming:nuclear_blast",
    "incoming:player_nuclear_blast",
}


class MilitaryBossDamageTests(unittest.TestCase):
    def test_only_pinned_damage_types(self):
        data = json.loads((ROOT / "compat/techquest-compat" / TAG).read_text())
        self.assertIs(data["replace"], False)
        self.assertEqual(set(data["values"]), EXPECTED)
        self.assertEqual(len(data["values"]), len(EXPECTED))
        self.assertFalse(any("bypasses_invulnerability" in value for value in data["values"]))

    def test_tag_embedded_in_mrpack_compatibility_jar(self):
        cfg = build_pack.load_cfg()
        self.assertEqual(cfg["version"], "0.3.3.3")
        packed = build_pack.compatibility_jar()
        with zipfile.ZipFile(io.BytesIO(packed)) as jar:
            self.assertEqual(json.loads(jar.read(TAG))["replace"], False)
            self.assertEqual(set(json.loads(jar.read(TAG))["values"]), EXPECTED)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "test.mrpack"
            build_pack.make_mrpack(cfg, [], target)
            with zipfile.ZipFile(target) as mrpack:
                self.assertEqual(mrpack.read("overrides/mods/" + build_pack.COMPAT_JAR_NAME), packed)

    def test_no_global_invulnerability_override(self):
        root = ROOT / "compat/techquest-compat/data/minecraft/tags/damage_type"
        self.assertFalse((root / "bypasses_invulnerability.json").exists())
        self.assertFalse((root / "bypasses_cooldown.json").exists())


if __name__ == "__main__":
    unittest.main()

"""TechQuest/Horizon Port Lab static tests. No Java JARs are executed."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import port_inventory
import build_demo_hmod

class PortLabTests(unittest.TestCase):
    def test_inventory_complete_but_unverified(self):
        report = port_inventory.build_report(port_inventory.SOURCE)
        cfg = json.loads(port_inventory.SOURCE.read_text(encoding="utf-8"))
        expected = sum(len(cfg.get(k, [])) for k in (
            "mods", "manual_mods", "external_mods", "optional_local_mods"
        ))
        self.assertEqual(report["summary"]["source_entries"], expected)
        self.assertGreater(expected, 60)
        self.assertFalse(report["horizon_coverage_measured"])
        self.assertEqual(report["ported_third_party_mods"], 0)
        self.assertTrue(all(row["horizon_status"] == "unverified" for row in report["entries"]))
        mods = {row["id"]: row for row in report["entries"]}
        self.assertNotIn("lootr", mods)
        self.assertNotIn("iceandfire-ce", mods)
        self.assertIn("wyrmroost", mods)
        self.assertEqual(mods["create"]["decision"], "native_logic_rewrite")
        self.assertEqual(mods["terralith"]["decision"], "inspect_data_assets")
        self.assertEqual(mods["sodium"]["decision"], "replace_or_skip")
        self.assertEqual(mods["forgematica"]["decision"], "client_native_rewrite")
        self.assertEqual(mods["Industrial Craft 2: Nostalgia"]["decision"], "manual_source_review")

    def test_prototype_zip_structure_and_determinism(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "test.hmod"
            build_demo_hmod.package(output=target)
            data1 = target.read_bytes()
            with zipfile.ZipFile(target) as archive:
                self.assertIsNone(archive.testzip())
                paths = set(archive.namelist())
                self.assertIn("horizon-mod.toml", paths)
                self.assertIn(
                    "data/techquest_expedition_marker/horizon/block/expedition_marker.json",
                    paths,
                )
                self.assertFalse(any(p.endswith(".jar") or p.endswith(".class") for p in paths))
                block = json.loads(archive.read(
                    "data/techquest_expedition_marker/horizon/block/expedition_marker.json"
                ))
                self.assertEqual(block["template"], "minecraft:amethyst_block")
                recipe = json.loads(archive.read(
                    "data/techquest_expedition_marker/recipe/expedition_marker.json"
                ))
                self.assertEqual(recipe["result"]["id"],
                                 "techquest_expedition_marker:expedition_marker")
            build_demo_hmod.package(output=target)
            self.assertEqual(data1, target.read_bytes())

if __name__ == "__main__":
    unittest.main()

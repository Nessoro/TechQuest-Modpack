"""Synthetic fixtures for the DragonRise evidence collector; not game tests."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.inspect_dragonrise_recipes import (
    DR_FILENAME, scan_jar, runtime_evidence,
)


class DragonRiseAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jar = self.root / DR_FILENAME
        with zipfile.ZipFile(self.jar, "w") as z:
            z.writestr("META-INF/neoforge.mods.toml", '[[mods]]\nmodId="fixture"\nversion="1.5.1"\n')
            z.writestr("fixture/Items.class", b"synthetic class")
            z.writestr("assets/fixture/lang/en_us.json", json.dumps({"item.fixture.fake": "Not registration proof"}))
            z.writestr("data/fixture/recipe/example.json", json.dumps({"type": "fixture:assembly", "result": {"id": "fixture:actual"}}))
            z.writestr("data/fixture/tags/item/example.json", json.dumps({"values": ["fixture:actual"]}))
            z.writestr("data/fixture/vehicles/example.json", "{}")

    def test_static_evidence_not_registry(self):
        data = scan_jar(self.jar, DR_FILENAME)
        self.assertEqual(data["mod_ids_from_metadata"], ["fixture"])
        self.assertFalse(data["independent_sha512_verified"])
        self.assertEqual(data["serializer_counts"], {"fixture:assembly": 1})
        self.assertEqual(data["recipes"][0]["recipe_id_candidate"], "fixture:example")
        self.assertEqual(data["localization"][0]["keys"], ["item.fixture.fake"])
        self.assertIn("data/fixture/vehicles/example.json", data["data_json_paths"])
        self.assertNotIn("registered_item_inventory", data)

    def test_checksum_and_filename(self):
        correct = hashlib.sha512(self.jar.read_bytes()).hexdigest()
        self.assertTrue(scan_jar(self.jar, DR_FILENAME, correct)["independent_sha512_verified"])
        with self.assertRaisesRegex(ValueError, "SHA-512 mismatch"):
            scan_jar(self.jar, DR_FILENAME, "0" * 128)
        with self.assertRaisesRegex(ValueError, "Expected original filename"):
            scan_jar(self.jar, "wrong.jar")

    def test_runtime_registry_ids_not_translation_keys(self):
        path = self.root / "registries.json"
        path.write_text(json.dumps({
            "minecraft:item": {"entries": {"fixture:actual": {}, "other:item": {}}},
            "minecraft:block": {"entries": {}},
        }), encoding="utf-8")
        data = runtime_evidence(path, ["fixture"])
        self.assertEqual(data["registered_item_inventory"][0]["registry_id"], "fixture:actual")
        self.assertEqual(len(data["registered_item_inventory"]), 1)
        self.assertIsNone(data["registered_item_inventory"][0]["player_facing"])
        self.assertEqual(data["registered_item_inventory"][0]["implementation_status"], "unreviewed")
        self.assertIsNone(data["registries"]["minecraft:creative_mode_tab"])

    def test_empty_registry_rejected(self):
        path = self.root / "registries.json"
        path.write_text(json.dumps({"minecraft:item": {"entries": {}},
                                    "minecraft:block": {"entries": {}}}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "No DragonRise"):
            runtime_evidence(path, ["fixture"])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from scripts.dragonrise_acceptance import CHECKS, validate_acceptance
from scripts.smoke_dragonrise_server import expected_recipes, validate_report


class DragonRiseAcceptanceTests(unittest.TestCase):
    def test_expected_manifest_counts(self):
        recipes = expected_recipes()
        self.assertEqual(len(recipes), 196)
        self.assertEqual(recipes["techquest:dragonrise/item/generator_deployer"]["ingredients"]["superbwarfare:steel_block"], 4)

    def test_no_evidence_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            result = validate_acceptance(Path(directory) / "absent", {"r": {}}, "hash")
            self.assertFalse(result["runtime_verified"])
            self.assertIsNone(result["obtainable_coverage_percent"])

    def test_reject_mismatched_decode(self):
        expected = {"r": {"kind":"vehicle", "target":"dragonrise_reforge:refale",
                          "serializer":"superbwarfare:vehicle_assembling",
                          "count":1, "ingredients":{"minecraft:iron_ingot":2}}}
        report = {"dragonrise_present":True, "expected":1, "loaded":1, "errors":[],
                  "original_sbw_recipe_ids":["superbwarfare:original"],
                  "observations":{"r":{"item":"superbwarfare:container",
                    "serializer":"superbwarfare:vehicle_assembling",
                    "deployment_entity":"dragonrise_reforge:refale",
                    "count":1, "decoded_ingredients":{"minecraft:iron_ingot":1}}}}
        with self.assertRaisesRegex(ValueError, "ingredient"):
            validate_report(report, True, expected)

    def test_synthetic_evidence_requires_all_phases_and_every_recipe(self):
        expected = {"r": {"kind":"item", "target":"dragonrise_reforge:test",
                          "serializer":"minecraft:crafting_shapeless", "count":1,
                          "ingredients":{"minecraft:iron_ingot":1}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            def put(name, value):
                (path / name).write_text(json.dumps(value))
            (path / "recipe-fingerprint.txt").write_text("fixture")
            put("expected.json", expected)
            for phase, present in (("absent",False),("present_existing_world",True),("present_restart",True)):
                put(phase+".json",{"dragonrise_present":present,"expected":1,"loaded":int(present),
                   "errors":[],"original_sbw_recipe_ids":["superbwarfare:original"],
                   "observations":{"r":{"item":"dragonrise_reforge:test","serializer":"minecraft:crafting_shapeless",
                       "count":1,"decoded_ingredients":{"minecraft:iron_ingot":1}}} if present else {}})
            self.assertTrue(validate_acceptance(path, expected, "fixture")["server_decode_verified"])
            self.assertFalse(validate_acceptance(path, expected, "fixture")["runtime_verified"])
            evidence = {"result":"pass","evidence":"synthetic unit-test fixture only"}
            put("manual-acceptance.json",{"recipe_fingerprint":"fixture","review":evidence,
                "checks":{k:evidence for k in CHECKS},"obtainability":{}})
            self.assertFalse(validate_acceptance(path, expected, "fixture")["runtime_verified"])
            put("manual-acceptance.json",{"recipe_fingerprint":"fixture","review":evidence,
                "checks":{k:evidence for k in CHECKS},"obtainability":{"r":evidence}})
            self.assertTrue(validate_acceptance(path, expected, "fixture")["runtime_verified"])
            self.assertFalse(validate_acceptance(path, expected, "different")["runtime_verified"])

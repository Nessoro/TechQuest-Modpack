import copy
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "terralith_worldgen", Path(__file__).parents[1] / "tools/prepare_terralith_worldgen.py")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


def legacy(mapper="type_1"):
    return {"type": "minecraft:weird_scaled_sampler", "input": "test:input",
            "noise": "test:noise", "rarity_value_mapper": mapper}


def evaluate(expr, value, xyz, noise):
    if expr == "test:input":
        return value
    if isinstance(expr, (int, float)):
        return expr
    kind = expr["type"]
    if kind == "minecraft:interval_select":
        sample = evaluate(expr["input"], value, xyz, noise)
        branch = next((i for i, t in enumerate(expr["thresholds"]) if sample < t),
                      len(expr["functions"]) - 1)
        return evaluate(expr["functions"][branch], value, xyz, noise)
    if kind == "minecraft:mul":
        return (evaluate(expr["argument1"], value, xyz, noise)
                * evaluate(expr["argument2"], value, xyz, noise))
    if kind == "minecraft:abs":
        return abs(evaluate(expr["argument"], value, xyz, noise))
    if kind == "minecraft:noise":
        x, y, z = xyz
        return noise(x * expr["xz_scale"], y * expr["y_scale"], z * expr["xz_scale"])
    raise AssertionError("unexpected expression")


class TerralithWorldgenTests(unittest.TestCase):
    def test_rarity_boundaries_from_official_1_21_1_methods(self):
        # Actual QuantizedSpaghettiRarity results, including exact boundaries.
        cases = {
            "type_1": [(-2, .75), (-.5, 1), (0, 1.5), (.5, 2), (2, 2)],
            "type_2": [(-2, .5), (-.75, .75), (-.5, 1), (.5, 2), (.75, 3), (2, 3)],
        }
        for mapper, rows in cases.items():
            result, count = adapter.expand(legacy(mapper))
            self.assertEqual(count, 1)
            for value, rarity in rows:
                with self.subTest(mapper=mapper, value=value):
                    self.assertEqual(evaluate(result, value, (0, 0, 0), lambda *p: -.25),
                                     rarity * .25)

    def test_nonconstant_noise_uses_all_three_coordinates_and_rarity(self):
        noise = lambda x, y, z: math.sin(x) + math.cos(y) - math.tanh(z)
        for mapper, value, rarity in [("type_1", -.6, .75), ("type_1", .2, 1.5),
                                      ("type_2", -.9, .5), ("type_2", .9, 3)]:
            result, _ = adapter.expand(legacy(mapper))
            for xyz in [(17, -23, 61), (-11, 3, -7), (0, 0, 0)]:
                expected = rarity * abs(noise(*(v / rarity for v in xyz)))
                self.assertAlmostEqual(evaluate(result, value, xyz, noise), expected, places=12)

    def test_originals_and_unrelated_nodes_are_preserved(self):
        source = {"unrelated": {"type": "custom:keep", "argument": [1, 2]},
                  "nested": [legacy()]}
        before = copy.deepcopy(source)
        result, count = adapter.expand(source)
        self.assertEqual(source, before)
        self.assertEqual(result["unrelated"], before["unrelated"])
        self.assertEqual(count, 1)

    def test_unknown_mapper_fields_and_inline_noise_require_review(self):
        for replacement in [{"rarity_value_mapper": "new_mapper"}, {"extra": True},
                            {"noise": {"firstOctave": -3}}]:
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                adapter.expand({**legacy(), **replacement})

    def test_air_carver_order_and_duplicates_are_preserved(self):
        source = {"carvers": {"air": ["minecraft:cave", "minecraft:canyon", "minecraft:cave"]}}
        before = copy.deepcopy(source)
        result, count = adapter.normalize_carvers(source)
        self.assertEqual(result["carvers"], before["carvers"]["air"])
        self.assertEqual(source, before)
        self.assertEqual(count, 1)

    def test_new_carvers_and_empty_steps_keep_their_meaning(self):
        current = {"carvers": ["minecraft:cave"]}
        self.assertEqual(adapter.normalize_carvers(current), (current, 0))
        self.assertEqual(adapter.normalize_carvers({"carvers": {}}), ({"carvers": []}, 1))

    def test_liquid_step_or_unknown_carver_shapes_require_review(self):
        for steps in ({"air": [], "liquid": ["test:liquid"]}, {"custom": []}, {"air": "test:cave"}):
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                adapter.normalize_carvers({"carvers": steps})

    def test_only_reviewed_comment_marker_is_removed_from_biome_or_list(self):
        source = {"type": "minecraft:biome", "biome_is": [
            "terralith:alpha_islands", adapter.DOCUMENTATION_BIOME, "other:unresolved"]}
        original = copy.deepcopy(source)
        result, count = adapter.normalize_marker(source)
        self.assertEqual(result["biome_is"], ["terralith:alpha_islands", "other:unresolved"])
        self.assertEqual(count, 1)
        self.assertEqual(source, original)

    def test_marker_only_predicate_remains_an_empty_false_or_list(self):
        result, count = adapter.normalize_marker(
            {"type": "minecraft:biome", "biome_is": [adapter.DOCUMENTATION_BIOME]})
        self.assertEqual(result["biome_is"], [])
        self.assertEqual(count, 1)

    def test_order_migration_keeps_all_features_and_other_steps(self):
        source = {"features": [["test:other"]] + [[] for _ in range(8)]
                  + [["test:before", adapter.CANE, adapter.PUMPKIN, "test:after"]]}
        original = copy.deepcopy(source)
        result, count = adapter.normalize_feature_order(source)
        self.assertEqual(count, 1)
        self.assertEqual(source, original)
        self.assertEqual(result["features"][:9], original["features"][:9])
        self.assertCountEqual(result["features"][9], original["features"][9])
        self.assertEqual(result["features"][9],
                         ["test:before", adapter.PUMPKIN, adapter.CANE, "test:after"])

    def test_interleaved_feature_pair_is_not_silently_reordered(self):
        source = {"features": [[] for _ in range(9)] + [[adapter.CANE, "test:middle", adapter.PUMPKIN]]}
        with self.assertRaises(ValueError):
            adapter.normalize_feature_order(source)

    def test_current_feature_order_is_unchanged(self):
        source = {"features": [[] for _ in range(9)] + [[adapter.PUMPKIN, adapter.CANE]]}
        self.assertEqual(adapter.normalize_feature_order(source), (source, 0))

    def test_worldgen_tags_are_selected_with_their_definitions(self):
        self.assertTrue(adapter.selected(Path('data/terralith/tags/worldgen/biome/test.json')))
        self.assertFalse(adapter.selected(Path('data/minecraft/advancement/test.json')))

    def fixture(self, base):
        work = base / "work"
        source = work / "mods/terralith/carry"
        source.mkdir(parents=True)
        (source / "horizon-mod.toml").write_text('id="terralith"\nversion="2.6.2"\n')
        field = source / "data/terralith/worldgen/density_function/test.json"
        field.parent.mkdir(parents=True)
        field.write_text(json.dumps(legacy()))
        dimension = work / "mods/terralith/outside/data/minecraft/dimension/overworld.json"
        dimension.parent.mkdir(parents=True)
        dimension.write_text('{}')
        return work, field

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output = base / "existing-world"
            output.mkdir()
            sentinel = output / "level.dat"
            sentinel.write_bytes(b"keep")
            with self.assertRaises(ValueError):
                adapter.prepare(base / "missing-work", base / "tool", output)
            self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_new_output_inside_an_existing_world_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "level.dat").write_bytes(b"keep")
            with self.assertRaises(ValueError):
                adapter.prepare(base / "missing-work", base / "tool", base / "datapacks/new")
            self.assertFalse((base / "datapacks").exists())

    def test_upgrader_failure_leaves_no_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            work, field = self.fixture(base)
            before = field.read_bytes()
            with patch.object(adapter.subprocess, "run",
                              side_effect=subprocess.CalledProcessError(2, "tool")):
                with self.assertRaises(subprocess.CalledProcessError):
                    adapter.prepare(work, base / "tool", base / "output")
            self.assertFalse((base / "output").exists())
            self.assertEqual(field.read_bytes(), before)
            self.assertFalse(list(base.glob('.terralith-worldgen-*')))

    def test_report_does_not_claim_gameplay_and_sources_are_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            work, field = self.fixture(base)
            before = field.read_bytes()
            def fake_upgrade(args, **kwargs):
                Path(args[-1]).mkdir()
                return SimpleNamespace(stdout="upgraded trial\n")
            with patch.object(adapter.subprocess, "run", side_effect=fake_upgrade):
                report = adapter.prepare(work, base / "tool", base / "output")
            self.assertEqual(report["expanded_samplers"], 1)
            self.assertEqual(field.read_bytes(), before)
            self.assertFalse(report["server_boot_tested"])
            self.assertFalse(report["natural_generation_verified"])
            self.assertFalse(report["gameplay_ported"])

    def test_symlink_source_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            work, field = self.fixture(base)
            outside = base / "unrelated"
            outside.write_text(field.read_text())
            field.unlink()
            field.symlink_to(outside)
            with self.assertRaises(ValueError):
                adapter.prepare(work, base / "tool", base / "output")
            self.assertFalse((base / "output").exists())


if __name__ == "__main__":
    unittest.main()

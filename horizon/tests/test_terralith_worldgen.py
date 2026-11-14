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

    def test_nonforced_tree_preserves_the_seven_original_soils(self):
        source = {"type": "minecraft:tree", "config": {
            "dirt_provider": {"type": "minecraft:simple_state_provider", "state": {"id": "minecraft:dirt"}},
            "decorators": [], "trunk_placer": {"type": "test:keep"}}}
        before = copy.deepcopy(source)
        result, count = adapter.normalize_trees(source)
        provider = result["config"]["below_trunk_provider"]
        self.assertEqual(count, 1)
        self.assertEqual(source, before)
        self.assertNotIn("fallback", provider)
        self.assertEqual(provider["rules"][0]["if_true"]["type"], "minecraft:not")
        self.assertCountEqual(provider["rules"][0]["if_true"]["predicate"]["blocks"],
                              ["minecraft:dirt", "minecraft:coarse_dirt", "minecraft:podzol",
                               "minecraft:muddy_mangrove_roots", "minecraft:moss_block",
                               "minecraft:rooted_dirt", "minecraft:mud"])
        self.assertEqual(result["config"]["trunk_placer"], before["config"]["trunk_placer"])
        self.assertNotIn("dirt_provider", result["config"])

    def test_forced_tree_keeps_its_unconditional_provider(self):
        source = {"type": "minecraft:tree", "config": {
            "force_dirt": True, "dirt_provider": {
                "type": "minecraft:simple_state_provider", "state": {"id": "minecraft:rooted_dirt"}}}}
        result, count = adapter.normalize_trees(source)
        self.assertEqual(result["config"]["below_trunk_provider"], source["config"]["dirt_provider"])
        self.assertNotIn("force_dirt", result["config"])
        self.assertEqual(count, 1)

    def test_tree_provider_conflicts_or_random_providers_need_review(self):
        configs = [
            {"dirt_provider": {"type": "minecraft:weighted_state_provider", "entries": []}},
            {"dirt_provider": {"type": "minecraft:simple_state_provider", "state": "minecraft:dirt"},
             "below_trunk_provider": {"id": "minecraft:stone"}},
            {"dirt_provider": {"type": "minecraft:simple_state_provider", "state": "minecraft:dirt"},
             "force_dirt": "false"},
        ]
        for config in configs:
            with self.subTest(config=config), self.assertRaises(ValueError):
                adapter.normalize_trees({"type": "minecraft:tree", "config": config})

    def test_disk_provider_keeps_fallback_rules_and_source(self):
        provider = {"fallback": {"type": "minecraft:simple_state_provider", "state": "minecraft:dirt"},
                    "rules": [{"if_true": {"type": "minecraft:matching_blocks", "blocks": ["minecraft:stone"]},
                               "then": {"type": "minecraft:simple_state_provider", "state": "minecraft:clay"}},
                              {"if_true": {"type": "minecraft:true"},
                               "then": {"type": "minecraft:simple_state_provider", "state": "minecraft:sand"}}]}
        source = {"type": "minecraft:disk", "config": {"radius": 4, "state_provider": provider}}
        original = copy.deepcopy(source)
        result, count = adapter.normalize_disk_providers(source)
        self.assertEqual(source, original)
        self.assertEqual(count, 1)
        current = result["config"]["state_provider"]
        self.assertEqual(current["type"], "minecraft:rule_based")
        self.assertEqual(current["fallback"], original["config"]["state_provider"]["fallback"])
        self.assertEqual(current["rules"], original["config"]["state_provider"]["rules"])
        self.assertEqual(adapter.normalize_disk_providers(result), (result, 0))

    def test_unknown_disk_record_or_rule_fields_need_review(self):
        for provider in ({"fallback": {}, "rules": [], "extra": 1},
                         {"fallback": {}, "rules": "invalid"},
                         {"fallback": {}, "rules": [{"if_true": {}, "then": {}, "extra": 1}]}):
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                adapter.normalize_disk_providers(
                    {"type": "minecraft:disk", "config": {"state_provider": provider}})

    def test_direct_state_provider_is_not_reinterpreted_as_legacy_record(self):
        source = {"type": "minecraft:disk", "state_provider": {"id": "minecraft:clay"}}
        self.assertEqual(adapter.normalize_disk_providers(source), (source, 0))

    def test_noise_records_deduplicate_but_keep_occurrence_count(self):
        spec = {"firstOctave": -4, "amplitudes": [1, 1]}
        source = {"type": "minecraft:dual_noise_provider", "seed": 2**63-1,
                  "scale": .5, "noise": spec, "slow_noise": copy.deepcopy(spec),
                  "states": ["minecraft:dirt", "minecraft:stone"]}
        original = copy.deepcopy(source)
        records = {}
        self.assertEqual(adapter.collect_noise_parameters(source, records), 2)
        self.assertEqual(len(records), 1)
        converted = {next(iter(records)): {"base_octave": -4, "octave_count": 2,
                                          "base_amplitude": .875}}
        result, count = adapter.inline_noise_parameters(source, converted)
        self.assertEqual(count, 2)
        self.assertEqual(source, original)
        for field in ("seed", "scale", "states", "type"):
            self.assertEqual(result[field], source[field])
        self.assertEqual(result["noise"], converted[next(iter(records))])
        self.assertEqual(result["slow_noise"], result["noise"])

    def test_unknown_noise_parameter_fields_are_not_discarded(self):
        for spec in ({"firstOctave": -4, "amplitudes": [1], "salt": 7},
                     {"firstOctave": -4, "amplitudes": [float('nan')]},
                     {"firstOctave": True, "amplitudes": [1]}):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                adapter.noise_parameter_key(spec)

    def test_density_noise_and_nonstring_type_are_not_provider_parameters(self):
        source = [{"type": "minecraft:noise", "noise": "minecraft:temperature", "xz_scale": 1},
                  {"type": None, "seed": 0, "scale": 1}]
        records = {}
        self.assertEqual(adapter.collect_noise_parameters(source, records), 0)
        self.assertEqual(records, {})
        self.assertEqual(adapter.inline_noise_parameters(source, {}), (source, 0))

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

    def test_patch_composition_retains_placed_child_without_mutating_source(self):
        child = {"feature": "test:configured", "placement": [
            {"type": "minecraft:block_predicate_filter", "predicate": {"type": "minecraft:true"}}]}
        patch = {"type": "minecraft:random_patch", "tries": 7,
                 "xz_spread": 12, "y_spread": 16, "feature": child}
        before = copy.deepcopy(patch)
        result, count = adapter.normalize_patches(patch)
        self.assertEqual(count, 1)
        self.assertEqual(patch, before)
        self.assertEqual(result["features"][0]["feature"]["features"], [child])
        self.assertFalse(adapter.has_legacy_patch(result))
        self.assertEqual(adapter.normalize_patches(result), (result, 0))

    def test_zero_spread_retains_random_sampling_and_named_placed_feature(self):
        patch = {"type": "minecraft:flower", "tries": 1,
                 "xz_spread": 0, "y_spread": 0, "feature": "test:placed"}
        result, _ = adapter.normalize_patches(patch)
        attempt = result["features"][0]
        self.assertEqual(attempt["feature"]["features"], ["test:placed"])
        for axis in ("x", "y", "z"):
            self.assertIsInstance(attempt["placement"][1][axis], dict)
            self.assertEqual(attempt["placement"][1][axis]["type"], "minecraft:trapezoid")

    def test_patch_beyond_composition_bounds_is_preserved_and_reportable(self):
        for fields in ({"y_spread": 32}, {"xz_spread": 32}, {"tries": 4097}):
            patch = {"type": "minecraft:random_patch", "tries": 1,
                     "xz_spread": 7, "y_spread": 3, "feature": "test:placed", **fields}
            self.assertEqual(adapter.normalize_patches(patch), (patch, 0))
            self.assertTrue(adapter.has_legacy_patch(patch))

    def test_wide_patch_individual_offsets_stay_in_engine_bounds(self):
        patch = {"type": "minecraft:random_patch", "tries": 7,
                 "xz_spread": 7, "y_spread": 25, "feature": "test:placed"}
        result, count = adapter.normalize_patches(patch)
        self.assertEqual(count, 1)
        self.assertFalse(adapter.has_legacy_patch(result))
        offsets = result["features"][0]["placement"][1:]
        self.assertEqual(len(offsets), 6)
        for offset in offsets:
            for axis in ("x", "y", "z"):
                if isinstance(offset[axis], dict):
                    values = [entry["data"] for entry in offset[axis]["distribution"]]
                    self.assertGreaterEqual(min(values), -16)
                    self.assertLessEqual(max(values), 16)

    def test_patch_unknown_fields_and_invalid_values_require_review(self):
        for fields in ({"tries": True}, {"y_spread": -1}, {"xz_spread": 2.5},
                       {"salt": 42}, {"feature": []}):
            patch = {"type": "minecraft:random_patch", "tries": 1,
                     "xz_spread": 7, "y_spread": 3, "feature": "test:placed", **fields}
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                adapter.normalize_patches(patch)

    def test_omitted_multiface_block_uses_original_default_and_keeps_options(self):
        feature = {"type": "minecraft:multiface_growth", "can_be_placed_on": ["minecraft:stone"],
                   "can_place_on_floor": True, "search_range": 9, "chance_of_spreading": .99}
        before = copy.deepcopy(feature)
        result, count = adapter.normalize_multiface({"feature": feature})
        self.assertEqual(feature, before)
        self.assertEqual(count, 1)
        self.assertEqual(result["feature"], {**before, "block": "minecraft:glow_lichen"})
        self.assertEqual(adapter.normalize_multiface(result), (result, 0))

    def test_explicit_multiface_block_is_preserved(self):
        feature = {"type": "minecraft:multiface_growth", "block": "minecraft:sculk_vein",
                   "can_be_placed_on": ["minecraft:stone"]}
        self.assertEqual(adapter.normalize_multiface(feature), (feature, 0))

    def test_unflattened_multiface_is_not_given_a_top_level_default(self):
        with self.assertRaises(ValueError):
            adapter.normalize_multiface({"type": "minecraft:multiface_growth", "config": {
                "can_be_placed_on": ["minecraft:stone"]}})

    def test_legacy_roots_disable_added_terrain_test_and_keep_children(self):
        source = {"type": "minecraft:root_system", "root_replaceable": "#test:soil",
                  "allowed_tree_position": {"type": "minecraft:true"},
                  "feature": {"feature": "test:tree", "placement": []},
                  "required_vertical_space_for_tree": 7, "root_column_max_height": 100}
        before = copy.deepcopy(source)
        result, count = adapter.normalize_roots(source)
        self.assertEqual(source, before)
        self.assertEqual(count, 1)
        self.assertEqual(result, {**before, "level_test_distance": 0, "max_level_deviation": 0})
        self.assertEqual(adapter.normalize_roots(result), (result, 0))

    def test_explicit_root_terrain_checks_are_not_overwritten(self):
        source = {"type": "minecraft:root_system", "level_test_distance": 8, "max_level_deviation": 2}
        self.assertEqual(adapter.normalize_roots(source), (source, 0))
        del source["max_level_deviation"]
        with self.assertRaises(ValueError):
            adapter.normalize_roots(source)

    def test_legacy_configured_reference_is_inlined_without_rewriting_placed_ids(self):
        definition = {"type": "minecraft:random_patch", "config": {"tries": 96}}
        definitions = {"minecraft:patch_grass": definition}
        source = {"features": [["minecraft:patch_grass"]],
                  "nested": [{"feature": "patch_grass", "placement": []},
                             {"feature": "test:patch_grass", "placement": []}],
                  "unrelated": {"feature": "minecraft:patch_grass"}}
        before = copy.deepcopy(source)
        result, count = adapter.inline_legacy_features(source, definitions)
        self.assertEqual(count, 1)
        self.assertEqual(source, before)
        self.assertEqual(result["features"], before["features"])
        self.assertEqual(result["nested"][1], before["nested"][1])
        self.assertEqual(result["unrelated"], before["unrelated"])
        self.assertEqual(result["nested"][0]["feature"], definition)
        result["nested"][0]["feature"]["config"]["tries"] = 1
        self.assertEqual(definition["config"]["tries"], 96)

    def test_unverified_legacy_server_is_rejected_before_zip_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "untrusted.jar"
            path.write_bytes(b"not the pinned official server")
            with self.assertRaisesRegex(ValueError, "official Minecraft 1.21.1"):
                adapter.load_legacy_features(path)

    def test_legacy_server_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "target.jar").write_bytes(b"input")
            (root / "link.jar").symlink_to(root / "target.jar")
            with self.assertRaisesRegex(ValueError, "symlink"):
                adapter.load_legacy_features(root / "link.jar")

    def test_dripstone_keeps_distributions_and_uses_merged_tag(self):
        source = {"type": "minecraft:dripstone_cluster", "height": {"type": "minecraft:uniform", "min_inclusive": 1, "max_inclusive": 7},
                  "dripstone_block_layer_thickness": 1,
                  "chance_of_dripstone_column_at_max_distance_from_center": .4,
                  "max_distance_from_edge_affecting_chance_of_dripstone_column": 2}
        before = copy.deepcopy(source)
        result, clusters, large = adapter.normalize_dripstone(source)
        self.assertEqual((clusters, large), (1, 0))
        self.assertEqual(source, before)
        self.assertEqual(result["height"], before["height"])
        self.assertEqual(result["speleothem_block_layer_thickness"], 1)
        self.assertEqual(result["chance_of_speleothem_at_max_distance_from_center"], .4)
        self.assertEqual(result["max_distance_from_edge_affecting_chance_of_speleothem"], 2)
        self.assertEqual(result["replaceable_blocks"], "#minecraft:dripstone_replaceable_blocks")
        self.assertEqual(adapter.normalize_dripstone(result), (result, 0, 0))

    def test_large_dripstone_keeps_explicit_replacement_set(self):
        source = {"type": "minecraft:large_dripstone", "column_radius": 2}
        result, clusters, large = adapter.normalize_dripstone(source)
        self.assertEqual((clusters, large), (0, 1))
        self.assertEqual(result["column_radius"], 2)
        custom = {**source, "replaceable_blocks": "#test:ice"}
        self.assertEqual(adapter.normalize_dripstone(custom), (custom, 0, 0))

    def test_conflicting_cluster_materials_require_review(self):
        source = {"type": "minecraft:dripstone_cluster", "base_block": "test:custom"}
        with self.assertRaises(ValueError):
            adapter.normalize_dripstone(source)

    def test_basalt_typo_preserves_original_codec_default_without_mutating_source(self):
        source = {"type": "minecraft:netherrack_replace_blobs", "radius": 0,
                  "state": {"id": "minecraft:smooth_basalt"},
                  "target": {"Name": "minecraft:basalt", "Properites": {"axis": "y"}}}
        before = copy.deepcopy(source)
        result, count = adapter.normalize_basalt_seed(source)
        self.assertEqual(source, before)
        self.assertEqual(count, 1)
        self.assertEqual(result["target"], {"id": "minecraft:basalt", "properties": {"axis": "y"}})
        self.assertEqual(result["state"], before["state"])
        self.assertEqual(result["radius"], 0)
        self.assertEqual(adapter.normalize_basalt_seed(result), (result, 0))

    def test_other_misspelled_block_states_require_review(self):
        source = {"type": "minecraft:netherrack_replace_blobs",
                  "target": {"Name": "minecraft:basalt", "Properites": {"axis": "x"}}}
        with self.assertRaises(ValueError):
            adapter.normalize_basalt_seed(source)

    def test_forest_rock_preserves_state_and_legacy_soils_with_dynamic_tags(self):
        source = {"type": "minecraft:forest_rock", "state": {"id": "minecraft:mossy_cobblestone"}}
        before = copy.deepcopy(source)
        result, count = adapter.normalize_forest_rocks(source)
        self.assertEqual(source, before)
        self.assertEqual(count, 1)
        self.assertEqual(result["state"], before["state"])
        predicates = result["can_place_on"]["predicates"]
        self.assertEqual({p["blocks"] for p in predicates if isinstance(p["blocks"], str)},
                         {"#minecraft:dirt", "#minecraft:base_stone_overworld"})
        self.assertIn("minecraft:mycelium", predicates[1]["blocks"])
        self.assertIn("minecraft:muddy_mangrove_roots", predicates[1]["blocks"])
        self.assertNotIn("minecraft:sand", predicates[1]["blocks"])
        self.assertEqual(adapter.normalize_forest_rocks(result), (result, 0))

    def test_nether_vegetation_preserves_weights_and_direct_states(self):
        source = {"type": "minecraft:nether_forest_vegetation", "spread_width": 8, "spread_height": 4,
                  "state_provider": {"type": "minecraft:weighted", "entries": [
                      {"data": "minecraft:stone", "weight": 3},
                      {"data": {"id": "minecraft:dirt"}, "weight": 7}]}}
        before = copy.deepcopy(source)
        result, count = adapter.normalize_nether_vegetation(source)
        self.assertEqual(source, before)
        self.assertEqual(count, 1)
        def collect(value):
            if isinstance(value, dict):
                if value.get("type") == "minecraft:weighted_random_selector":
                    return [value]
                return sum((collect(v) for v in value.values()), [])
            if isinstance(value, list):
                return sum((collect(v) for v in value), [])
            return []
        choices = collect(result)[0]["features"]
        self.assertEqual([v["weight"] for v in choices], [3, 7])
        self.assertEqual([v["data"]["feature"]["to_place"] for v in choices],
                         [{"id": "minecraft:stone"}, {"id": "minecraft:dirt"}])

    def test_other_vegetation_providers_require_review(self):
        with self.assertRaisesRegex(ValueError, "non-weighted"):
            adapter.normalize_nether_vegetation({"type": "minecraft:nether_forest_vegetation",
                "spread_width": 8, "spread_height": 4, "state_provider": {"id": "minecraft:stone"}})

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

    def test_new_output_cannot_pollute_the_source_work(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            with self.assertRaises(ValueError):
                adapter.prepare(work, work / "tool", work / "new-artifact")
            self.assertFalse((work / "new-artifact").exists())

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

"""Static contracts only: no assertion of in-game obtainability."""
import json
import re
import unittest
import zipfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "compat/techquest-compat/data/techquest/recipe/dragonrise"
AUDIT = json.loads((ROOT / "compat/dragonrise_inventory.json").read_text(encoding="utf-8"))
ENTRIES = AUDIT["entries"]
TARGETS = [e for e in ENTRIES if e.get("recipe_id")]
KNOWN = set(["create:electron_tube","create:precision_mechanism","dragonrise_reforge:kevlar","ic2:advanced_circuit","ic2:circuit","mekanism:advanced_control_circuit","mekanism:alloy_atomic","mekanism:alloy_reinforced","mekanism:elite_control_circuit","mekanism:ultimate_control_circuit","minecraft:copper_ingot","minecraft:glass_pane","minecraft:glowstone_dust","minecraft:iron_ingot","minecraft:leather","minecraft:paper","minecraft:red_dye","minecraft:string","superbwarfare:armor_plate","superbwarfare:cemented_carbide_block","superbwarfare:heavy_armament_module","superbwarfare:large_battery_pack","superbwarfare:large_motor","superbwarfare:large_propeller","superbwarfare:light_armament_module","superbwarfare:medium_armament_module","superbwarfare:motor","superbwarfare:propeller","superbwarfare:steel_block","superbwarfare:track","superbwarfare:wheel"])
REGEX = re.compile(r"(?:(\d+) )?([a-z0-9_]+:[a-z0-9_./-]+)")

class DragonRiseCraftingTest(unittest.TestCase):
    def test_inventory_and_coverage(self):
        self.assertEqual(len({(e["kind"], e["registry_id"]) for e in ENTRIES}), len(ENTRIES))
        self.assertEqual(len({e["recipe_id"] for e in TARGETS}), len(TARGETS))
        self.assertEqual(len(TARGETS), AUDIT["stats"]["new_recipes"])
        self.assertEqual(len(TARGETS), AUDIT["stats"]["static_player_facing_targets"])
        self.assertTrue(all(e.get("reason") for e in ENTRIES if not e.get("recipe_id")))
        self.assertIsNone(AUDIT["stats"]["obtainable_coverage_percent"])
        for kind, key in [("item","registered_items"),("block","registered_blocks")]:
            self.assertEqual(sum(e["kind"] == kind for e in ENTRIES), AUDIT["stats"][key])
        self.assertEqual(sum(e["kind"] in ("entity","vehicle") for e in ENTRIES), AUDIT["stats"]["registered_entities"])

    def test_recipe_contract_and_no_cycles(self):
        actual = {p.relative_to(BASE).as_posix()[:-5]: p for p in BASE.rglob("*.json")}
        expected = {e["recipe_id"].split("dragonrise/",1)[1]:e for e in TARGETS}
        self.assertEqual(set(actual), set(expected))
        graph = {}
        outputs = {e["registry_id"] for e in TARGETS if e["kind"] == "item"}
        for key, e in expected.items():
            r = json.loads(actual[key].read_text(encoding="utf-8"))
            conditions = r["neoforge:conditions"]
            mods = {c["modid"] for c in conditions if c["type"] == "neoforge:mod_loaded"}
            self.assertTrue({"dragonrise_reforge","superbwarfare"} <= mods)
            if r["type"] == "superbwarfare:vehicle_assembling":
                self.assertIn(r["category"], {"land","aircraft","civilian","water","defense","misc"})
                self.assertEqual(r["result"], {"entity" if e["kind"] == "vehicle" else "item":e["registry_id"]})
                ingredients = []
                for s in r["inputs"]:
                    match = REGEX.fullmatch(s)
                    self.assertIsNotNone(match, s)
                    self.assertGreater(int(match.group(1) or 1), 0)
                    ingredients.append(match.group(2))
            else:
                self.assertIn(r["type"], {"minecraft:crafting_shaped","minecraft:crafting_shapeless"})
                self.assertEqual(r["result"]["id"], e["registry_id"])
                self.assertGreater(r["result"]["count"], 0)
                ingredients = [v["item"] for v in (r["key"].values() if "key" in r else r["ingredients"])]
                if "pattern" in r:
                    self.assertLessEqual(len(r["pattern"]),3)
                    self.assertEqual({len(row) for row in r["pattern"]}, {len(r["pattern"][0])})
                    self.assertEqual(set("".join(r["pattern"]))-{" "},set(r["key"]))
            self.assertTrue(ingredients)
            for i in ingredients:
                self.assertIn(i, KNOWN)
                if i.startswith(("create:","ic2:","mekanism:")):
                    self.assertIn(i.split(":")[0],mods)
                if i.startswith("dragonrise_reforge:"):
                    self.assertIn(i,outputs)
            if e["kind"]=="item":
                graph[e["registry_id"]] = set(ingredients) & outputs
        def visit(node, seen):
            self.assertNotIn(node,seen)
            for n in graph.get(node, ()):
                visit(n,seen|{node})
        for node in graph:
            visit(node,set())

    def test_compat_jar_contains_all_recipes(self):
        import build_pack
        with zipfile.ZipFile(io.BytesIO(build_pack.compatibility_jar())) as z:
            for e in TARGETS:
                rid=e["recipe_id"].split(":",1)[1]
                self.assertIn("data/techquest/recipe/"+rid+".json",z.namelist())
            self.assertFalse(any(n.startswith("data/superbwarfare/recipe/dragonrise/") for n in z.namelist()))

if __name__ == "__main__":
    unittest.main()

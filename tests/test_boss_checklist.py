"""Regression tests for shared LAN boss kills and survival hunt guide."""
import io
import json
import unittest
import zipfile

from scripts.boss_checklist import (
    BOSSES, EXTRA_BOSSES, LEGENDARY_GUIDES, NAMESPACE, OBJECTIVE,
    boss_checklist_datapack, guide_book_components,
)
from scripts.guide_assets import guide_overrides


class BossChecklistTests(unittest.TestCase):
    def setUp(self):
        self.packed = boss_checklist_datapack()
        self.archive = zipfile.ZipFile(io.BytesIO(self.packed))

    def read_json(self, filename):
        return json.loads(self.archive.read(filename).decode("utf-8"))

    def read_text(self, filename):
        return self.archive.read(filename).decode("utf-8")

    def test_reproducible_1211_datapack(self):
        self.assertEqual(self.packed, boss_checklist_datapack())
        self.assertEqual(self.read_json("pack.mcmeta")["pack"]["pack_format"], 48)
        self.assertEqual(self.archive.testzip(), None)
        self.assertIn("data/minecraft/tags/function/load.json", self.archive.namelist())
        self.assertIn("data/minecraft/tags/function/tick.json", self.archive.namelist())

    def test_unchanged_legendary_ids_and_existing_world_scoreboard(self):
        self.assertEqual(len(BOSSES), 14)
        ids = [row[0] for row in BOSSES]
        self.assertEqual(len(set(ids)), 14)
        self.assertIn("posessed_paladin", ids)
        self.assertIn("endersent", ids)
        self.assertIn("annihilation_pursuer", ids)
        self.assertEqual(OBJECTIVE, "tqb_kills")
        for entity_id, _, group, _, category in BOSSES:
            advancement = self.read_json(
                "data/" + NAMESPACE + "/advancement/" + entity_id + ".json")
            self.assertEqual(advancement["parent"], NAMESPACE + ":" + group)
            self.assertEqual(
                advancement["criteria"]["kill"]["conditions"]["entity"]["type"],
                "legendary_monsters:" + entity_id)
            self.assertEqual(advancement["rewards"]["function"],
                             NAMESPACE + ":kill/" + entity_id)
            self.assertEqual(advancement["display"]["frame"],
                             "goal" if category == "miniboss" else "challenge")
            self.assertIn("Око", LEGENDARY_GUIDES["frostbitten_golem"] if entity_id == "frostbitten_golem" else "Око")
            self.assertEqual(
                self.read_text("data/" + NAMESPACE + "/function/kill/"
                               + entity_id + ".mcfunction"),
                "scoreboard players set #" + entity_id + " " + OBJECTIVE + " 1\n")

    def test_new_bosses_have_unique_types_and_advancements(self):
        self.assertEqual(len(EXTRA_BOSSES), 20)
        keys = [entry[0] for entry in EXTRA_BOSSES]
        ids = [entry[1] for entry in EXTRA_BOSSES]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(keys).intersection(row[0] for row in BOSSES), set())
        for key, entity_type, _, group, _, category, hint in EXTRA_BOSSES:
            advancement = self.read_json(
                "data/" + NAMESPACE + "/advancement/" + key + ".json")
            self.assertEqual(advancement["parent"], NAMESPACE + ":" + group)
            self.assertEqual(advancement["criteria"]["kill"]["trigger"],
                             "minecraft:player_killed_entity")
            self.assertEqual(
                advancement["criteria"]["kill"]["conditions"]["entity"]["type"],
                entity_type)
            self.assertIn(hint, advancement["display"]["description"])
            self.assertEqual(advancement["rewards"]["function"],
                             NAMESPACE + ":kill/" + key)
            self.assertEqual(advancement["display"]["frame"],
                             "goal" if category == "miniboss" else "challenge")

    def test_worldwide_sync_and_late_joiners(self):
        load = self.read_text("data/" + NAMESPACE + "/function/load.mcfunction")
        tick = self.read_text("data/" + NAMESPACE + "/function/tick.mcfunction")
        sync = self.read_text("data/" + NAMESPACE + "/function/sync.mcfunction")
        self.assertIn("scoreboard objectives add " + OBJECTIVE + " dummy", load)
        self.assertIn("matches 20.. run function " + NAMESPACE + ":sync", tick)
        self.assertEqual(sync.count("run advancement grant @a only "),
                         len(BOSSES) + len(EXTRA_BOSSES))
        for key in [row[0] for row in BOSSES] + [row[0] for row in EXTRA_BOSSES]:
            self.assertIn(
                "execute if score #" + key + " " + OBJECTIVE
                + " matches 1.. run advancement grant @a only "
                + NAMESPACE + ":" + key, sync)

    def test_book_granted_once_and_craftable_replacement(self):
        components = guide_book_components()
        pages = components["minecraft:written_book_content"]["pages"]
        self.assertEqual(len(pages), len(BOSSES) + len(EXTRA_BOSSES) + 4)
        self.assertLessEqual(len(pages), 100)
        for page in pages:
            self.assertIn("text", json.loads(page["raw"]))
        self.assertTrue(any("Eye Of Frost" in page["raw"] for page in pages))
        self.assertTrue(any("Burning Arena" in page["raw"] for page in pages))
        self.assertTrue(any("Soul Star" in page["raw"] for page in pages))
        self.assertTrue(any("Silver Dungeon" in page["raw"] for page in pages))
        advancement = self.read_json(
            "data/" + NAMESPACE + "/advancement/receive_guide.json")
        self.assertEqual(advancement["rewards"]["loot"],
                         [NAMESPACE + ":hunt_guide"])
        loot = self.read_json("data/" + NAMESPACE + "/loot_table/hunt_guide.json")
        self.assertEqual(loot["pools"][0]["entries"][0]["functions"][0]["components"],
                         components)
        recipe = self.read_json("data/" + NAMESPACE + "/recipe/hunt_guide.json")
        self.assertEqual(recipe["result"]["components"], components)
        self.assertEqual(recipe["ingredients"],
                         [{"item": "minecraft:book"}, {"item": "minecraft:ender_eye"}])

    def test_builder_ships_zip_unchanged(self):
        path = "config/openloader/packs/techquest_boss_checklist.zip"
        self.assertEqual(guide_overrides()[path], self.packed)


if __name__ == "__main__":
    unittest.main()

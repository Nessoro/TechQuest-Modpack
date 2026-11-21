"""Structural regression checks for the TechQuest shared boss checklist."""
import io
import json
import unittest
import zipfile

from scripts.boss_checklist import BOSSES, NAMESPACE, OBJECTIVE, boss_checklist_datapack
from scripts.guide_assets import guide_overrides


class BossChecklistTests(unittest.TestCase):
    def setUp(self):
        self.packed = boss_checklist_datapack()
        self.archive = zipfile.ZipFile(io.BytesIO(self.packed))

    def read_json(self, filename):
        return json.loads(self.archive.read(filename).decode("utf-8"))

    def test_deterministic_and_minecraft_1211_format(self):
        self.assertEqual(self.packed, boss_checklist_datapack())
        self.assertEqual(self.read_json("pack.mcmeta")["pack"]["pack_format"], 48)
        self.assertIn("data/minecraft/tags/function/load.json", self.archive.namelist())
        self.assertIn("data/minecraft/tags/function/tick.json", self.archive.namelist())

    def test_all_14_entity_ids_and_kill_rewards(self):
        ids = [row[0] for row in BOSSES]
        self.assertEqual(len(ids), 14)
        self.assertEqual(len(set(ids)), 14)
        self.assertIn("posessed_paladin", ids)
        self.assertIn("endersent", ids)
        self.assertIn("annihilation_pursuer", ids)
        for entity_id, _, group, _, category in BOSSES:
            advancement = self.read_json(
                "data/" + NAMESPACE + "/advancement/" + entity_id + ".json"
            )
            self.assertEqual(advancement["parent"], NAMESPACE + ":" + group)
            self.assertEqual(advancement["criteria"]["kill"]["trigger"],
                             "minecraft:player_killed_entity")
            self.assertEqual(advancement["criteria"]["kill"]["conditions"]["entity"]["type"],
                             "legendary_monsters:" + entity_id)
            self.assertEqual(advancement["rewards"]["function"],
                             NAMESPACE + ":kill/" + entity_id)
            self.assertEqual(advancement["display"]["frame"],
                             "goal" if category == "miniboss" else "challenge")
            kill = self.archive.read(
                "data/" + NAMESPACE + "/function/kill/" + entity_id + ".mcfunction"
            ).decode("utf-8")
            self.assertEqual(kill, "scoreboard players set #" + entity_id
                             + " " + OBJECTIVE + " 1\n")

    def test_world_progress_replicates_to_online_players(self):
        load = self.archive.read(
            "data/" + NAMESPACE + "/function/load.mcfunction"
        ).decode("utf-8")
        tick = self.archive.read(
            "data/" + NAMESPACE + "/function/tick.mcfunction"
        ).decode("utf-8")
        sync = self.archive.read(
            "data/" + NAMESPACE + "/function/sync.mcfunction"
        ).decode("utf-8")
        self.assertIn("scoreboard objectives add " + OBJECTIVE + " dummy", load)
        self.assertIn("matches 20.. run function " + NAMESPACE + ":sync", tick)
        self.assertEqual(sync.count("run advancement grant @a only "), len(BOSSES))
        for entity_id, *_ in BOSSES:
            self.assertIn("execute if score #" + entity_id + " " + OBJECTIVE
                          + " matches 1.. run advancement grant @a only "
                          + NAMESPACE + ":" + entity_id, sync)
        self.assertNotIn("scoreboard objectives setdisplay", sync)

    def test_pack_is_shipped_in_client_and_server_overrides(self):
        path = "config/openloader/packs/techquest_boss_checklist.zip"
        self.assertEqual(guide_overrides()[path], self.packed)


if __name__ == "__main__":
    unittest.main()

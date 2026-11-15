"""Review guards for Oritech 1.2.13 and Fluidic Tanks 1.1.1, NeoForge 1.21.1.

These tests validate official Modrinth metadata pinned in modlist.json and packaging,
not in-world fluid loss, machine ticks, dedicated server startup or gameplay compatibility.
"""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack

ROOT = Path(__file__).resolve().parents[1]
NEW = {
    "4sYI62kA": ("oritech", "1.2.13", "BR0KKypH",
                "oritech-neoforge-1.21.1-1.2.13.jar",
                "9a688409643075051d759da1b7dc732dd97f5f3ae584a12c5908689858af145373a69046d9c1881e6e0f41916c742e2850512296e05dbcd39fc0f214ecfc3cdf",
                {"client": "required", "server": "required"}),
    "b1ZV3DIJ": ("b1ZV3DIJ", "4.0.6", "dJgL278E",
                "athena-neoforge-1.21.1-4.0.6.jar",
                "ab40a306a26ce834daae921a1e87768cd2538a4bfe27a4480f97af854084cc334e7416b1bd0b7583834a32a86951283f29fd4b1df7b98a967a6b26a3ec05e2cf",
                {"client": "required", "server": "unsupported"}),
    "yAyrQXJ6": ("fluidic-tanks", "1.1.1", "991No08g",
                "fluidic_tanks-1.1.1.jar",
                "aced593ef1c018d1cb6807b8f2e6b1b6acb8cc4358e388fbed49bed7be798abeb2a5348a5382454e1b5d9595d7ba364b079ceab29f5b3b3b2d668f4a764c6161",
                {"client": "required", "server": "required"}),
}


class OritechFluidTanksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.mods = cls.cfg["mods"]
        cls.pins = cls.cfg["modrinth_lock"]

    def test_platform_and_existing_mods_preserved(self):
        self.assertEqual(("1.21.1", "neoforge", "21.1.264"),
                         (self.cfg["minecraft"], self.cfg["loader"], self.cfg["loader_version"]))
        self.assertEqual(77, len(self.mods))
        for slug in ("ae2", "refined-storage", "refined-storage-jei-integration",
                     "open-parties-and-claims", "mekanism", "modern-industrialization",
                     "create", "buildcraft-community-edition", "geckolib",
                     "architectury-api", "jei"):
            self.assertEqual(1, sum(m["project"] == slug for m in self.mods), slug)
        self.assertEqual("2.0.9", self.pins["KDvYkUg3"]["version"])
        self.assertEqual("19.64.0.455", self.pins["u6dRKJwZ"]["version"])
        self.assertFalse(any(m["project"] == "xycraft-world" for m in self.mods))

    def test_exact_official_releases_with_correct_sides(self):
        for project, (slug, version, vid, filename, sha, sides) in NEW.items():
            with self.subTest(project=project):
                rows = [m for m in self.mods if m["project"] == slug]
                self.assertEqual(1, len(rows))
                self.assertTrue(rows[0]["required"])
                self.assertEqual(vid, rows[0]["version_id"])
                self.assertEqual(sides, rows[0]["environment"])
                lock = self.pins[project]
                self.assertEqual(version, lock["version"])
                self.assertEqual(vid, lock["version_id"])
                self.assertEqual(filename, lock["filename"])
                self.assertEqual(sha, lock["sha512"])
                self.assertEqual(sides, lock["environment"])
        self.assertTrue(next(m for m in self.mods if m["project"] == "b1ZV3DIJ")["client_only"])

    def test_required_dependencies_no_duplicate_libraries(self):
        for slug in ("geckolib", "architectury-api", "b1ZV3DIJ",
                     "oritech", "fluidic-tanks"):
            self.assertEqual(1, sum(m["project"] == slug for m in self.mods), slug)
        self.assertIn("8BmcQJ2H", self.pins)  # GeckoLib
        self.assertIn("lhGA9TYQ", self.pins)  # Architectury API

    def test_mrpack_records_exact_jars_without_redistribution(self):
        entries = []
        for project, (slug, ver, vid, filename, sha, env) in NEW.items():
            entries.append({
                "filename": filename,
                "environment": env,
                "file": {
                    "filename": filename,
                    "url": ("https://cdn.modrinth.com/data/" + project +
                            "/versions/" + vid + "/" + filename),
                    "size": 1000,
                    "hashes": {"sha512": sha},
                },
            })
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "new-mods.mrpack"
            build_pack.make_mrpack(self.cfg, entries, path)
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                index = json.loads(z.read("modrinth.index.json"))
                rows = {r["path"]: r for r in index["files"]}
                for _, (_, _, _, filename, sha, env) in NEW.items():
                    row = rows["mods/" + filename]
                    self.assertEqual(sha, row["hashes"]["sha512"])
                    self.assertEqual(env, row["env"])
                    self.assertNotIn("overrides/mods/" + filename, z.namelist())


if __name__ == "__main__":
    unittest.main()

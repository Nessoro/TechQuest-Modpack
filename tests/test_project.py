import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))

    def test_version(self):
        self.assertEqual(self.cfg["minecraft"], "1.21.1")
        self.assertEqual(self.cfg["loader"], "neoforge")

    def test_priorities(self):
        slugs = {m["project"] for m in self.cfg["mods"]}
        self.assertIn("buildcraft-community-edition", slugs)
        self.assertIn("create", slugs)
        self.assertTrue(any("Industrial Craft" in m["name"] for m in self.cfg["manual_mods"]))

    def test_no_duplicate_projects(self):
        slugs = [m["project"] for m in self.cfg["mods"]]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_issues_templates(self):
        for fn in ("bug_report.yml", "mod_request.yml", "config.yml"):
            self.assertTrue((ROOT / ".github" / "ISSUE_TEMPLATE" / fn).is_file())

    def test_site(self):
        html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn("TechQuest", html)
        self.assertIn("window.TQ_MODS", html)
        self.assertIn("bug-form", html)
        self.assertIn("mod-form", html)
        self.assertIn("Nessoro/TechQuest-Modpack", html)

if __name__ == "__main__":
    unittest.main()

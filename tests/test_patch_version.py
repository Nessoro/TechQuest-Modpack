"""Regression: a TechQuest patch must have one version across all deliverables.

The release-facing EXE and .mrpack filenames are always TechQuest_<version>;
no mod name, platform/channel suffix, or stale micro-patch label.
"""
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack

ROOT = Path(__file__).resolve().parents[1]


class TechQuestPatchVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        cls.version = cls.cfg["version"]

    def test_patch_version_is_numeric_and_unique_for_this_candidate(self):
        self.assertRegex(self.version, r"^0\.3\.3\.[1-9][0-9]*$")
        self.assertEqual("0.3.3.3", self.version)

    def test_pack_manifest_uses_matching_patch_version(self):
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder) / ("TechQuest_" + self.version + ".mrpack")
            n = build_pack.make_mrpack(self.cfg, [], pack)
            self.assertEqual(0, n)
            with zipfile.ZipFile(pack) as archive:
                self.assertIsNone(archive.testzip())
                index = json.loads(archive.read("modrinth.index.json"))
                self.assertEqual(self.version, index["versionId"])

    def test_windows_metadata_and_interface_match_modrinth_manifest(self):
        csproj = (ROOT / "windows-installer" / "TechQuestInstaller.csproj").read_text(encoding="utf-8")
        source = (ROOT / "windows-installer" / "Program.cs").read_text(encoding="utf-8")
        self.assertIn("<Version>" + self.version + "</Version>", csproj)
        self.assertIn('private const string PackVersion = "' + self.version + '";', source)
        self.assertIn('GetProperty("versionId").GetString() != PackVersion', source)
        self.assertNotIn("TechQuest 0.3.3-micro3", source)

    def test_ci_creates_and_checks_versioned_artifacts(self):
        workflow = (ROOT / ".github" / "workflows" / "build-alpha.yml").read_text(encoding="utf-8")
        self.assertIn("TechQuest_" + self.version + ".mrpack", workflow)
        self.assertIn("dist/TechQuest_" + self.version + ".exe", workflow)
        self.assertIn("security-work/installer/TechQuest_" + self.version + ".exe", workflow)
        self.assertIn("if($index.versionId -ne '" + self.version + "')", workflow)
        self.assertNotIn("TechQuest_1.21.1_0.3.3_ALPHA.mrpack", workflow)
        builder = (ROOT / "build_pack.py").read_text(encoding="utf-8")
        self.assertIn('("TechQuest_" + cfg["version"] + ".mrpack")', builder)

    def test_website_and_readme_show_same_patch(self):
        site = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn('"version": "' + self.version + '"', site)
        self.assertIn("TechQuest_" + self.version + ".exe", readme)
        self.assertIn("TechQuest_" + self.version + ".mrpack", readme)


if __name__ == "__main__":
    unittest.main()

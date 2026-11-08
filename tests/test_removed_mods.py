"""Regression checks: mods rejected by the owner must never enter the pack again."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_pack
from scripts.guide_assets import ENTRIES

ROOT = Path(__file__).resolve().parents[1]
REMOVED = {"mcheli-modern-port": "ZwSE3PTi", "timeless-and-classics-zero": "SzzJttH8", "parcool": "Fsvx2bdR"}


class RemovedModsTests(unittest.TestCase):
    def test_rejected_mods_absent_from_roots_lock_and_key_defaults(self):
        cfg = build_pack.load_cfg()
        roots = {m["project"] for m in cfg["mods"]}
        reasons = {m["project"]: m["reason"] for m in cfg["removed_mods"]}
        for slug, project_id in REMOVED.items():
            self.assertNotIn(slug, roots)
            self.assertNotIn(project_id, cfg["modrinth_lock"])
            self.assertEqual(reasons[slug], "не нужен")
        self.assertFalse(any("tacz" in name.lower() for name in
                             cfg["performance_profile"]["key_defaults"]))

    def test_mrpack_has_no_tacz_metadata_or_removed_guide_pages(self):
        cfg = build_pack.load_cfg()
        self.assertNotIn("aircraft_trial", ENTRIES)
        self.assertNotIn("tacz_weapons", ENTRIES)
        self.assertNotIn("parcool", ENTRIES)
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "test.mrpack"
            build_pack.make_mrpack(cfg, [], pack)
            with zipfile.ZipFile(pack) as archive:
                names = archive.namelist()
                self.assertNotIn("overrides/TECHQUEST_TACZ_OFFICIAL_GUNPACKS.json", names)
                self.assertFalse(any("tacz" in name.lower() or "mcheli" in name.lower()
                                     for name in names))

    def test_installer_and_site_cannot_advertise_removed_mods(self):
        src = (ROOT / "windows-installer/Program.cs").read_text(encoding="utf-8")
        self.assertNotIn("ImportOfficialTaczGunpacks", src)
        self.assertNotIn("Импорт TaCZ ZIP", src)
        self.assertIn("ImportAcceleratedMcWarfare", src)
        html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        for slug in REMOVED:
            self.assertNotIn("https://modrinth.com/mod/" + slug, html)


if __name__ == "__main__":
    unittest.main()

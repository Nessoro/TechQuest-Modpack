"""Guard against accidentally reintroducing the retired AMW optional import."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
import build_pack

ROOT = Path(__file__).resolve().parents[1]

class RetiredOptionalModTests(unittest.TestCase):
    def test_amw_absent_from_manifest_gui_and_site(self):
        cfg = build_pack.load_cfg()
        self.assertNotIn("acceleratedmcwarfare", json.dumps(cfg).lower())
        self.assertIn("dragonrise_reforge", [m["id"] for m in cfg.get("optional_local_mods", [])])
        for path in ("windows-installer/Program.cs", "docs/index.html"):
            source = (ROOT / path).read_text(encoding="utf-8").lower()
            self.assertNotIn("acceleratedmcwarfare", source)
            self.assertNotIn("importamw", source)
        self.assertTrue(any(m["project"] == "geckolib" for m in cfg["mods"]))

    def test_amw_absent_from_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder) / "test.mrpack"
            build_pack.make_mrpack(build_pack.load_cfg(), [], pack)
            with zipfile.ZipFile(pack) as archive:
                self.assertNotIn("acceleratedmcwarfare", "\n".join(archive.namelist()).lower())
                metadata = archive.read("overrides/TECHQUEST_OPTIONAL_LOCAL_MODS.json").decode()
                self.assertNotIn("acceleratedmcwarfare", metadata.lower())
                self.assertIn("dragonrise_reforge", metadata)

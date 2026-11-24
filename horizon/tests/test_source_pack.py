import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_source_pack import find_pack


class SourcePackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = self.root / "snapshot.json"
        self.cfg.write_text(json.dumps({"version": "0.3.3.1", "minecraft": "1.21.1",
                                        "loader": "neoforge", "loader_version": "21.1.264"}))

    def pack(self, version="0.3.3.1", loader="21.1.264", filename="TechQuest_0.3.3.1.mrpack"):
        path = self.root / filename
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("modrinth.index.json", json.dumps({
                "game": "minecraft", "versionId": version,
                "dependencies": {"minecraft": "1.21.1", "neoforge": loader}
            }))
        return path

    def test_matching_pack(self):
        path = self.pack()
        self.assertEqual(find_pack(self.root, self.cfg), path.resolve())

    def test_wrong_version(self):
        self.pack(version="0.3.3.2")
        with self.assertRaises(ValueError):
            find_pack(self.root, self.cfg)

    def test_wrong_loader(self):
        self.pack(loader="21.1.1")
        with self.assertRaises(ValueError):
            find_pack(self.root, self.cfg)

    def test_ambiguous_packs(self):
        self.pack()
        self.pack(filename="extra.mrpack")
        with self.assertRaises(ValueError):
            find_pack(self.root, self.cfg)

    def test_missing_pack(self):
        with self.assertRaises(ValueError):
            find_pack(self.root, self.cfg)

"""Fail-closed input checks for the partial spawner adapter (no game files)."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import stage_yung_dungeons as adapter


class SourceValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.jar = self.root / "fixture.jar"
        self.carry = self.root / "carry"

    def fixture(self, extra=None, chest_extra=None, include_chest=True):
        with zipfile.ZipFile(self.jar, "w") as archive:
            for mob in ("skeleton", "spider", "zombie"):
                name = f"data/betterdungeons/worldgen/processor_list/small_dungeon/small_dungeon_{mob}.json"
                processor = {"processor_type": "betterdungeons:mob_spawner_processor",
                             "spawner_mob": f"minecraft:{mob}"}
                if mob == "skeleton" and extra:
                    processor.update(extra)
                processors = [processor]
                if include_chest:
                    chest = {"processor_type": "betterdungeons:small_dungeon_chest_processor"}
                    if mob == "skeleton" and chest_extra:
                        chest.update(chest_extra)
                    processors.append(chest)
                archive.writestr(name, json.dumps({"processors": processors}))
                path = self.carry / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{"processors": []}')
        return hashlib.sha1(self.jar.read_bytes()).hexdigest()

    def test_changed_jar_is_rejected(self):
        self.fixture()
        with self.assertRaisesRegex(ValueError, "pinned"):
            adapter.replacements(self.jar, self.carry)

    def test_changed_source_processor_is_rejected(self):
        digest = self.fixture({"custom_spawn_rules": {}})
        with patch.object(adapter, "SOURCE_SHA1", digest):
            with self.assertRaisesRegex(ValueError, "unreviewed"):
                adapter.replacements(self.jar, self.carry)

    def test_changed_carried_rules_are_rejected(self):
        digest = self.fixture()
        path = next(self.carry.rglob("*.json"))
        path.write_text('{"processors": [{"processor_type": "minecraft:nop"}]}')
        with patch.object(adapter, "SOURCE_SHA1", digest):
            with self.assertRaisesRegex(ValueError, "carried rules differ"):
                adapter.replacements(self.jar, self.carry)

    def test_symlinked_source_is_rejected(self):
        self.fixture()
        link = self.root / "link.jar"
        link.symlink_to(self.jar)
        with self.assertRaisesRegex(ValueError, "symlink"):
            adapter.replacements(link, self.carry)

    def test_changed_chest_processor_is_rejected(self):
        digest = self.fixture(chest_extra={"chance": 1.0})
        with patch.object(adapter, "SOURCE_SHA1", digest):
            with self.assertRaisesRegex(ValueError, "unreviewed chest"):
                adapter.replacements(self.jar, self.carry)

    def test_missing_chest_processor_is_rejected(self):
        digest = self.fixture(include_chest=False)
        with patch.object(adapter, "SOURCE_SHA1", digest):
            with self.assertRaisesRegex(ValueError, "exactly one chest"):
                adapter.replacements(self.jar, self.carry)


if __name__ == "__main__":
    unittest.main()

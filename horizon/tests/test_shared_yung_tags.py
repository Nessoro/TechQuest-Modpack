"""Namespace ownership, lossless append semantics and fail-before-write assembly."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import assemble_shared_yung_tags as shared


class SharedTagsTests(unittest.TestCase):
    def prepare(self, root):
        originals = {}
        for module in shared.SOURCES:
            for tag in shared.TAGS:
                path = root / "mods" / module / "outside" / shared.tag_path(tag)
                path.parent.mkdir(parents=True, exist_ok=True)
                data = json.dumps({"replace": False, "values": [module + ":structure"]}).encode()
                path.write_bytes(data)
                originals[path] = data
        extra = root / "mods/terralith/outside/data/minecraft/worldgen/biome/forest.json"
        extra.parent.mkdir(parents=True)
        extra.write_text("{}")
        return originals

    def test_both_mods_survive_once_and_outside_files_remain_auditable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            originals = self.prepare(root)
            report = shared.assemble(root)
            for tag in shared.TAGS:
                merged = json.loads((root / "mods" / shared.MODULE / "carry" / shared.tag_path(tag)).read_text())
                self.assertEqual(merged["values"], ["betterdungeons:structure", "betterfortresses:structure"])
            for path, data in originals.items():
                self.assertEqual(path.read_bytes(), data)
            self.assertEqual(report["outside_status_counts"], {"recovered_shared_tag": 4, "needs_review": 1})
            self.assertFalse(report["runtime_tested"])
            self.assertFalse(report["gameplay_ported"])
            with self.assertRaisesRegex(ValueError, "overwrite"):
                shared.assemble(root)

    def test_unsupported_replace_policy_fails_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            originals = self.prepare(root)
            next(iter(originals)).write_text('{"replace":true,"values":["minecraft:a"]}')
            with self.assertRaisesRegex(ValueError, "append-only"):
                shared.assemble(root)
            self.assertFalse((root / "mods" / shared.MODULE).exists())

    def test_existing_namespace_owner_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.prepare(root)
            manifest = root / "mods/other/carry/horizon-mod.toml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('id="other"\nnamespaces=["yungsapi"]\n')
            with self.assertRaisesRegex(ValueError, "namespace owner"):
                shared.assemble(root)

    def test_duplicate_values_are_deduplicated_and_bad_shapes_rejected(self):
        data = b'{"values":["minecraft:a","minecraft:a"]}'
        self.assertEqual(shared.merge_tags([data, data])["values"], ["minecraft:a"])
        for payload in (b'{"values":[{"id":"minecraft:a"}]}', b'{"values":["../bad"]}',
                        b'{"values":[],"remove":[]}', b'{"values":[]}'):
            with self.assertRaises(ValueError):
                shared.merge_tags([payload])

    def test_symlink_source_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            originals = self.prepare(root)
            source = next(iter(originals))
            source.unlink()
            source.symlink_to(root / "unrelated.json")
            with self.assertRaisesRegex(ValueError, "Symlink"):
                shared.assemble(root)


if __name__ == "__main__":
    unittest.main()

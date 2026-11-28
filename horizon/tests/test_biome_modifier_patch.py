"""A core fix must never rewrite an unknown source or follow a source symlink."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import apply_biome_modifier_patch as patcher


class BiomeModifierPatchTests(unittest.TestCase):
    def test_unknown_source_stays_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); spec = json.loads((patcher.PATCH / "horizon-core-patch.json").read_text())
            (root / ".horizon-mixins-stage.json").write_text(json.dumps({"inputs": {spec["source_file"]: spec["source_sha256"]}}))
            target = root / spec["source_file"]; target.parent.mkdir(parents=True); target.write_bytes(b"unrecognized user source")
            with self.assertRaisesRegex(ValueError, "differs from reviewed pin"):
                patcher.apply(root)
            self.assertEqual(target.read_bytes(), b"unrecognized user source")

    def test_source_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); spec = json.loads((patcher.PATCH / "horizon-core-patch.json").read_text())
            (root / ".horizon-mixins-stage.json").write_text(json.dumps({"inputs": {spec["source_file"]: spec["source_sha256"]}}))
            witness = root / "witness"; witness.write_bytes(b"preserve")
            target = root / spec["source_file"]; target.parent.mkdir(parents=True); target.symlink_to(witness)
            with self.assertRaisesRegex(ValueError, "symlink"):
                patcher.apply(root)
            self.assertEqual(witness.read_bytes(), b"preserve")


if __name__ == "__main__": unittest.main()

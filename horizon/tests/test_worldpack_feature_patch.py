"""Refuse partial/unknown stages before modifying either core source."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import apply_worldpack_feature_patch as patcher


class WorldpackPatchTests(unittest.TestCase):
    def fixture(self, root):
        reviewed = root / "reviewed"
        reviewed.mkdir()
        sha = lambda data: hashlib.sha256(data).hexdigest()
        base = {"source_file": "src/content.rs", "source_sha256": sha(b"original"),
                "patched_sha256": sha(b"base correction")}
        (reviewed / "base").mkdir()
        (reviewed / "base/horizon-core-patch.json").write_text(json.dumps(base))
        spec = {"patch_file": "delta.patch", "patch_sha256": sha(b"reviewed delta"),
                "module_file": "module.rs", "module_target": "src/module.rs",
                "module_sha256": sha(b"reviewed module"), "sources": [
                    {"path": "src/content.rs", "source_sha256": sha(b"base correction"), "patched_sha256": sha(b"final content")},
                    {"path": "src/loading.rs", "source_sha256": sha(b"original loading"), "patched_sha256": sha(b"final loading")} ]}
        (reviewed / "horizon-core-patch.json").write_text(json.dumps(spec))
        (reviewed / "delta.patch").write_bytes(b"reviewed delta")
        (reviewed / "module.rs").write_bytes(b"reviewed module")
        stage = root / "stage"
        (stage / "src").mkdir(parents=True)
        (stage / "src/content.rs").write_bytes(b"original")
        (stage / "src/loading.rs").write_bytes(b"original loading")
        (stage / ".horizon-mixins-stage.json").write_text(json.dumps({"inputs": {
            "src/content.rs": base["source_sha256"], "src/loading.rs": spec["sources"][1]["source_sha256"]}}))
        return stage, reviewed

    def test_unknown_second_source_leaves_first_source_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            stage, reviewed = self.fixture(Path(temp))
            (stage / "src/loading.rs").write_bytes(b"user change")
            with patch.object(patcher, "PATCH", reviewed), patch.object(patcher, "BASE_PATCH", reviewed / "base"), patch.object(patcher, "apply_base") as base:
                with self.assertRaisesRegex(ValueError, "source differs"):
                    patcher.apply(stage)
                base.assert_not_called()
            self.assertEqual((stage / "src/content.rs").read_bytes(), b"original")
            self.assertEqual((stage / "src/loading.rs").read_bytes(), b"user change")
            self.assertFalse((stage / "src/module.rs").exists())

    def test_module_symlink_is_refused_before_base_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            stage, reviewed = self.fixture(Path(temp))
            witness = Path(temp) / "witness"
            witness.write_bytes(b"preserve")
            (stage / "src/module.rs").symlink_to(witness)
            with patch.object(patcher, "PATCH", reviewed), patch.object(patcher, "BASE_PATCH", reviewed / "base"), patch.object(patcher, "apply_base") as base:
                with self.assertRaisesRegex(ValueError, "symlink"):
                    patcher.apply(stage)
                base.assert_not_called()
            self.assertEqual(witness.read_bytes(), b"preserve")

    def test_completed_stage_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            stage, reviewed = self.fixture(Path(temp))
            for name, data in (("content.rs", b"final content"), ("loading.rs", b"final loading"), ("module.rs", b"reviewed module")):
                (stage / "src" / name).write_bytes(data)
            before = {p: p.stat().st_mtime_ns for p in stage.rglob("*") if p.is_file()}
            with patch.object(patcher, "PATCH", reviewed), patch.object(patcher, "BASE_PATCH", reviewed / "base"), patch.object(patcher, "apply_base") as base, patch.object(patcher.subprocess, "run") as run:
                self.assertFalse(patcher.apply(stage)["changed"])
                base.assert_not_called()
                run.assert_not_called()
            self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})


if __name__ == "__main__":
    unittest.main()

import importlib.util
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "inspect_bundle.py"
spec = importlib.util.spec_from_file_location("mcww3_inspector", MODULE)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


def fake_jar():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as jar:
        jar.writestr("META-INF/mods.toml", '''modLoader="javafml"
loaderVersion="[47,)"
license="All Rights Reserved"
[[mods]]
modId="ww3"
version="2.1-beta"
[[dependencies.ww3]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.21)"
''')
        # Synthetic header and strings, not executable third-party bytecode.
        jar.writestr("ww3/Fake.class", struct.pack(">IHH", 0xCAFEBABE, 0, 61) + b"net/minecraftforge/eventbus/Fake")
        jar.writestr("LICENSE", "synthetic license fixture")
    return stream.getvalue()


class InspectorTests(unittest.TestCase):
    def test_original_metadata_never_claims_successful_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "original.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("ww3.jar", fake_jar())
                archive.writestr("ww3-content-packs/core/model.glb", b"DO-NOT-REDISTRIBUTE-ASSET")
            report = inspector.inspect_bundle(bundle)
            self.assertFalse(report["port_completed"])
            self.assertFalse(report["runtime_tested"])
            self.assertFalse(report["distribution_permission_verified"])
            self.assertEqual(report["source_file_count"], 0)
            self.assertEqual(report["jars"][0]["declared_license"], "All Rights Reserved")
            self.assertEqual(report["jars"][0]["class_file_major_versions"], {"61": 1})
            self.assertEqual(report["jars"][0]["classes_referencing_api_namespace"], {"forge": 1})
            self.assertNotIn("DO-NOT-REDISTRIBUTE-ASSET", json.dumps(report))
            self.assertEqual({path.name for path in Path(tmp).iterdir()}, {"original.zip"})

    def test_source_file_presence_does_not_prove_buildable_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "original.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("ww3.jar", fake_jar())
                archive.writestr("example/Example.java", "class Example {}")
            report = inspector.inspect_bundle(bundle)
            self.assertTrue(report["source_files_detected"])
            self.assertFalse(report["buildable_source_project_verified"])
            self.assertFalse(report["port_completed"])

    def test_path_traversal_is_rejected_without_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(bundle, "w") as archive:
                archive.writestr("../ww3.jar", fake_jar())
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                inspector.inspect_bundle(bundle)

    def test_missing_mod_metadata_is_rejected(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as jar:
            jar.writestr("dummy", "not a mod")
        with self.assertRaisesRegex(ValueError, "No Forge/NeoForge metadata"):
            inspector.inspect_jar(data.getvalue(), "dummy.jar")

    def test_oversized_member_is_rejected(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as jar:
            jar.writestr("large", b"x" * 128)
        from unittest.mock import patch
        with zipfile.ZipFile(io.BytesIO(data.getvalue())) as jar:
            with patch.object(inspector, "LIMIT", 64):
                with self.assertRaisesRegex(ValueError, "limit"):
                    inspector.safe_members(jar)


if __name__ == "__main__":
    unittest.main()

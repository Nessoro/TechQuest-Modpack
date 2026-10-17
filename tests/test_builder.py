import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "build_pack.py"
spec = importlib.util.spec_from_file_location("techquest_builder", SOURCE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class BuilderTests(unittest.TestCase):
    def test_checksum_sha1(self):
        from hashlib import sha1
        payload = b"hello"
        builder.verify(payload, {"sha1":sha1(payload).hexdigest()})

    def test_reject_checksum_mismatch(self):
        with self.assertRaises(builder.BuildError):
            builder.verify(b"bad", {"sha1":"0"*40})

    def test_reject_no_integrity_hash(self):
        with self.assertRaises(builder.BuildError):
            builder.verify(b"payload", {})

    def test_filename_traversal_rejected(self):
        with self.assertRaises(builder.BuildError):
            builder.safe_filename("../sneaky.jar")

    def test_mrpack_manifest(self):
        cfg = {"version":"test","pack_name":"TechQuest Test","description":"Test",
               "minecraft":"1.21.1","loader_version":"21.1.259"}
        mod = {"filename":"test.jar", "environment":{"client":"required","server":"required"},
               "file":{"filename":"test.jar","url":"https://example.org/test.jar",
                       "size":123,"hashes":{"sha1":"a"*40}}}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "test.mrpack"
            self.assertEqual(builder.make_mrpack(cfg,[mod],out),1)
            with zipfile.ZipFile(out) as z:
                index=json.loads(z.read("modrinth.index.json"))
            self.assertEqual(index["dependencies"]["minecraft"],"1.21.1")
            self.assertEqual(index["files"][0]["path"],"mods/test.jar")

if __name__ == "__main__":
    unittest.main()

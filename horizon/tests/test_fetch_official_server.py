import hashlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fetch_official_server import download_server


class OfficialServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "server.jar"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as jar:
            jar.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")
        self.data = buf.getvalue()
        self.record = {"url": "https://piston-data.mojang.com/v1/objects/test/server.jar",
                       "size": len(self.data), "sha1": hashlib.sha1(self.data).hexdigest()}

    def fetch(self, record=None, data=None):
        return download_server(record or self.record, self.path,
                               lambda url: io.BytesIO(self.data if data is None else data))

    def test_verified_download(self):
        self.assertTrue(self.fetch()["server_jar_verified"])
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_hash_mismatch_leaves_no_output(self):
        with self.assertRaises(ValueError):
            self.fetch(dict(self.record, sha1="0" * 40))
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_truncated_download_leaves_no_output(self):
        with self.assertRaises(ValueError):
            self.fetch(data=self.data[:-1])
        self.assertFalse(self.path.exists())

    def test_oversized_download_leaves_no_output(self):
        with self.assertRaises(ValueError):
            self.fetch(data=self.data + b"x")
        self.assertFalse(self.path.exists())

    def test_existing_file_preserved(self):
        self.path.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            self.fetch()
        self.assertEqual(self.path.read_bytes(), b"existing")

    def test_unofficial_url_rejected(self):
        with self.assertRaises(ValueError):
            self.fetch(dict(self.record, url="https://example.org/server.jar"))

    def test_invalid_archive_rejected(self):
        data = b"not a jar"
        with self.assertRaises(zipfile.BadZipFile):
            self.fetch(dict(self.record, size=len(data), sha1=hashlib.sha1(data).hexdigest()), data)
        self.assertFalse(self.path.exists())

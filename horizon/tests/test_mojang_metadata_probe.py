import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from probe_mojang_metadata import MANIFEST, official_url, probe


class MetadataProbeTests(unittest.TestCase):
    def fixture(self, game_id="26.3", digest=None, catalog_id="26.3", client_url=None):
        url = "https://piston-meta.mojang.com/v1/packages/example/26.3.json"
        client = {"url": client_url or "https://piston-data.mojang.com/v1/objects/example/client.jar",
                  "sha1": "a" * 40, "size": 123}
        server = {"url": "https://piston-data.mojang.com/v1/objects/example/server.jar",
                  "sha1": "b" * 40, "size": 456}
        raw = json.dumps({"id": game_id, "downloads": {"client": client, "server": server},
                          "javaVersion": {"majorVersion": 25}}).encode()
        catalog = json.dumps({"versions": [{"id": catalog_id, "url": url,
                               "sha1": digest or hashlib.sha1(raw).hexdigest()}]}).encode()
        calls = []
        def fetch(address):
            calls.append(address)
            return {MANIFEST: catalog, url: raw}[address]
        return fetch, calls

    def test_exact_version_metadata_only(self):
        fetch, calls = self.fixture()
        result = probe("26.3", fetch)
        self.assertTrue(result["version_metadata_verified"])
        self.assertFalse(result["resources_prepared"])
        self.assertFalse(result["server_boot_tested"])
        self.assertEqual(len(calls), 2)

    def test_missing_version_no_fallback(self):
        fetch, calls = self.fixture(catalog_id="26.2")
        with self.assertRaises(ValueError):
            probe("26.3", fetch)
        self.assertEqual(len(calls), 1)

    def test_checksum_mismatch(self):
        fetch, _ = self.fixture(digest="0" * 40)
        with self.assertRaises(ValueError):
            probe("26.3", fetch)

    def test_wrong_metadata_id(self):
        fetch, _ = self.fixture(game_id="26.2")
        with self.assertRaises(ValueError):
            probe("26.3", fetch)

    def test_nonofficial_download_rejected(self):
        fetch, _ = self.fixture(client_url="https://piston-data.mojang.com.evil.test/client.jar")
        with self.assertRaises(ValueError):
            probe("26.3", fetch)

    def test_credentials_or_http_rejected(self):
        for url in ("http://piston-meta.mojang.com/catalog", "https://user@piston-meta.mojang.com/catalog"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                official_url(url)

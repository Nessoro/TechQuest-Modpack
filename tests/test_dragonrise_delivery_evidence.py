"""Fail-closed URL and authorization checks for the diagnostic-only probe."""
import os
import unittest
from unittest.mock import patch
from scripts import probe_dragonrise_delivery as probe

class DragonRiseDeliveryEvidenceTests(unittest.TestCase):
    def test_exact_url_only(self):
        self.assertTrue(probe.allowed("https://mediafilez.forgecdn.net/files/9208/25/"+probe.NAME))
        for url in (
            "http://mediafilez.forgecdn.net/files/9208/25/"+probe.NAME,
            "https://mediafilez.forgecdn.net.evil.example/files/9208/25/"+probe.NAME,
            "https://mediafilez.forgecdn.net/files/9208/26/"+probe.NAME,
            "https://mediafilez.forgecdn.net/files/9208/25/"+probe.NAME+"?token=test",
            "https://mediafilez.forgecdn.net@evil.example/files/9208/25/"+probe.NAME,
        ):
            self.assertFalse(probe.allowed(url))
    def test_missing_key_never_downloads(self):
        with patch.dict(os.environ, {"CURSEFORGE_API_KEY":""}), patch("urllib.request.build_opener") as opener:
            with self.assertRaisesRegex(ValueError,"API key unavailable"):
                probe.probe()
            opener.assert_not_called()

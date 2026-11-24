"""Fail-closed rules and download checks used by the isolated real-client runner."""
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import smoke_client_runtime as runtime


class ClientRuntimeChecks(unittest.TestCase):
    def test_linux_libraries_and_optional_account_features_are_selected_correctly(self):
        self.assertTrue(runtime.allowed([]))
        self.assertFalse(runtime.allowed([{"action": "allow", "os": {"name": "windows"}}]))
        self.assertTrue(runtime.allowed([{"action": "allow"}, {"action": "disallow", "os": {"name": "osx"}}]))
        self.assertFalse(runtime.allowed([{"action": "allow", "features": {"is_demo_user": True}}]))
        self.assertFalse(runtime.allowed([{"action": "allow", "os": {"name": "linux", "arch": "aarch64"}}]))

    def test_arguments_do_not_enable_quickplay_or_silently_accept_unknown_placeholders(self):
        args = ["--gameDir", "${game}", {"rules": [{"action": "allow", "features": {"has_quick_plays_support": True}}],
                                       "value": ["--quickPlayPath", "${unavailable}"]}]
        self.assertEqual(runtime.arguments(args, {"game": "/tmp/isolated"}), ["--gameDir", "/tmp/isolated"])
        with self.assertRaises(KeyError):
            runtime.arguments(["${unknown}"], {})

    def test_invalid_download_is_never_written_over_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "library.jar"
            target.write_bytes(b"existing")
            info = {"url": "https://example.test/library.jar", "sha1": hashlib.sha1(b"official").hexdigest()}
            with patch.object(runtime.urllib.request, "urlopen", return_value=io.BytesIO(b"tampered")):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    runtime.download(info, target)
            self.assertEqual(target.read_bytes(), b"existing")

    def test_client_runner_refuses_to_start_outside_isolated_ci(self):
        with patch.dict(runtime.os.environ, {}, clear=True), patch.object(runtime.subprocess, "Popen") as launch:
            with self.assertRaises(SystemExit):
                runtime.main()
            launch.assert_not_called()

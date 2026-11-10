import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "fetch_inputs", Path(__file__).parents[1] / "tools/fetch_minecraft_inputs.py")
fetcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetcher)


class InputDownloadTests(unittest.TestCase):
    def test_corrupt_download_does_not_replace_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input"
            path.write_bytes(b"previous")
            record = {"url": "https://piston-data.mojang.com/test", "size": 4,
                      "sha1": hashlib.sha1(b"good").hexdigest()}
            with patch.object(fetcher, "read_url", return_value=b"evil"):
                with self.assertRaises(ValueError):
                    fetcher.fetch(record, path)
            self.assertEqual(path.read_bytes(), b"previous")

    def test_verified_cache_does_not_need_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input"
            path.write_bytes(b"good")
            record = {"size": 4, "sha1": hashlib.sha1(b"good").hexdigest()}
            with patch.object(fetcher, "read_url", side_effect=AssertionError("network")):
                self.assertEqual(fetcher.fetch(record, path), b"good")

    def test_paths_cannot_escape_cache_including_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "cache"
            root.mkdir()
            (root / "link").symlink_to(root.parent, target_is_directory=True)
            for relative in ("../outside", "/outside", "link/outside"):
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    fetcher.destination(root, relative)

    def test_existing_launcher_is_refused_before_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "saves").mkdir()
            with patch.object(fetcher, "read_url", side_effect=AssertionError("network")):
                with self.assertRaises(ValueError):
                    fetcher.run(root, {"minecraft": {"version": "26.3", "java_major": 25}})


if __name__ == "__main__":
    unittest.main()

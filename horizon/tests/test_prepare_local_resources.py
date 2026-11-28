import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import prepare_local_resources as local


class PrepareLocalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.minecraft = self.root / "minecraft"
        self.upstream = self.root / "upstream"
        self.tools = self.root / "tools"
        self.java = self.root / "java"
        self.server = self.root / "server.jar"
        self.output = self.root / "prepared"
        version = self.minecraft / "versions/26.3"
        for folder in (version, self.minecraft / "libraries", self.minecraft / "assets/indexes",
                       self.minecraft / "assets/objects", self.upstream, self.tools, self.java / "bin"):
            folder.mkdir(parents=True)
        client = version / "26.3.jar"
        for path in (client, self.server, self.tools / "horizon-prepare",
                     self.java / "bin/java", self.java / "bin/javac"):
            path.write_bytes(path.name.encode())
        def entry(path):
            return {"size": path.stat().st_size, "sha1": hashlib.sha1(path.read_bytes()).hexdigest()}
        self.version_json = version / "26.3.json"
        self.version_json.write_text(json.dumps({"id": "26.3", "downloads": {
            "client": entry(client), "server": entry(self.server)}}))
        (self.tools / "build-result.json").write_text(json.dumps({
            "upstream_commit": local.UPSTREAM, "minecraft": "26.3", "platform": "linux-x86_64",
            "default_features": False, "sha256": {
                "horizon-prepare": local.digest(self.tools / "horizon-prepare", "sha256")}}))

    def commands(self):
        with patch.object(local.subprocess, "check_output", side_effect=[local.UPSTREAM + "\n", ""]):
            return local.build_commands(self.minecraft, self.upstream, self.tools,
                                        self.java, self.server, self.output)

    def test_explicit_local_commands_without_output_creation(self):
        prepare, check = self.commands()
        self.assertIn("--complete", prepare)
        self.assertEqual(prepare[prepare.index("--minecraft-dir") + 1], str(self.minecraft))
        self.assertEqual(check[-1], "--check")
        self.assertFalse(self.output.exists())

    def test_missing_client(self):
        (self.minecraft / "versions/26.3/26.3.jar").unlink()
        with self.assertRaisesRegex(ValueError, "JAR missing"):
            self.commands()

    def test_corrupt_server(self):
        self.server.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "JAR missing"):
            self.commands()

    def test_wrong_version(self):
        self.version_json.write_text('{"id":"26.2"}')
        with self.assertRaisesRegex(ValueError, "exactly 26.3"):
            self.commands()

    def test_tampered_preparer(self):
        (self.tools / "horizon-prepare").write_bytes(b"bad")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.commands()

    def test_existing_output_refused(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, "new directory"):
            self.commands()

    def test_nested_output_refused(self):
        self.output = self.minecraft / "prepared"
        with self.assertRaisesRegex(ValueError, "separate"):
            self.commands()

    def test_wrong_upstream_refused(self):
        with patch.object(local.subprocess, "check_output", return_value="wrong"):
            with self.assertRaisesRegex(ValueError, "pinned revision"):
                local.build_commands(self.minecraft, self.upstream, self.tools,
                                     self.java, self.server, self.output)


if __name__ == "__main__":
    unittest.main()

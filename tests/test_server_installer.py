import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = ROOT / "scripts" / "install_server.py"
spec = importlib.util.spec_from_file_location("techquest_server_installer", SOURCE)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class ServerInstallerTests(unittest.TestCase):
    def test_valid_version(self):
        self.assertEqual(installer.check_index({"game":"minecraft",
            "dependencies":{"minecraft":"1.21.1","neoforge":"21.1.259"}}), "21.1.259")

    def test_reject_wrong_version(self):
        with self.assertRaises(installer.packbuilder.BuildError):
            installer.check_index({"game":"minecraft",
                "dependencies":{"minecraft":"1.21.4","neoforge":"21.1.259"}})

    def test_excludes_client_only(self):
        f=lambda path, env: {"path":"mods/"+path,"env":env,
            "downloads":["https://example.org/"+path], "hashes":{"sha1":"a"*40}}
        index={"files":[f("client.jar",{"server":"unsupported"}),
                        f("server.jar",{"server":"required"})]}
        self.assertEqual([x["file"]["filename"] for x in installer.server_records(index)], ["server.jar"])

    def test_rejects_path_traversal(self):
        with self.assertRaises(installer.packbuilder.BuildError):
            list(installer.server_records({"files":[{
                "path":"mods/../escape.jar", "downloads":["https://example.org/test.jar"],
                "hashes":{"sha1":"a"*40}}]}))

    def test_does_not_overwrite_server_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"server.properties"
            p.write_text("max-players=2\n",encoding="utf-8")
            installer.prepare_properties(Path(tmp))
            self.assertEqual(p.read_text(), "max-players=2\n")

if __name__=="__main__":
    unittest.main()

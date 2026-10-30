import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("techquest_client_installer",
                                            ROOT/"scripts"/"install_client.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def sample_index():
    return {"game":"minecraft",
            "dependencies":{"minecraft":"1.21.1","neoforge":"21.1.259"},
            "files":[
                {"path":"mods/buildcraft.jar","hashes":{"sha1":"a"*40},
                 "env":{"client":"required","server":"required"},
                 "downloads":["https://example.org/buildcraft.jar"]},
                {"path":"mods/optimizer.jar","hashes":{"sha512":"b"*128},
                 "env":{"client":"required","server":"unsupported"},
                 "downloads":["https://example.org/optimizer.jar"]},
                {"path":"mods/serveronly.jar","hashes":{"sha1":"a"*40},
                 "env":{"client":"unsupported","server":"required"},
                 "downloads":["https://example.org/serveronly.jar"]},
            ]}
class InstallerTests(unittest.TestCase):
    def test_install_uses_only_client_mods(self):
        entries=mod.client_records(sample_index())
        self.assertEqual([x["file"]["filename"] for x in entries],
                         ["buildcraft.jar","optimizer.jar"])

    def test_reject_path_traversal(self):
        index=sample_index()
        index["files"][0]["path"]="mods/../danger.jar"
        with self.assertRaises(mod.build_pack.BuildError):
            mod.client_records(index)

    def test_reject_incorrect_minecraft_version(self):
        index=sample_index()
        index["dependencies"]["minecraft"]="1.21.4"
        with self.assertRaises(mod.build_pack.BuildError):
            mod.client_records(index)

    def test_existing_mods_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            archive=d/"p.mrpack"
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("modrinth.index.json",json.dumps(sample_index()))
            mods=d/"game"/"mods"
            mods.mkdir(parents=True)
            (mods/"already.jar").write_bytes(b"old")
            with self.assertRaises(mod.build_pack.BuildError):
                mod.install(archive,d/"game")
            self.assertEqual((mods/"already.jar").read_bytes(),b"old")

    def test_dry_run_never_creates_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            archive=d/"p.mrpack"
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("modrinth.index.json",json.dumps(sample_index()))
            self.assertEqual(mod.install(archive,d/"game",True),2)
            self.assertFalse((d/"game").exists())

if __name__=="__main__":
    unittest.main()

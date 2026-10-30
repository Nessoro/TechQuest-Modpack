"""Regressions: Lite leaves all gameplay mods untouched and adds only client optimizers."""
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("techquest_lite_builder",
                                                ROOT / "scripts" / "build_lite.py")
lite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lite)

def record(name, env="unsupported", project=None):
    return {"requested":project or name,"title":name,"version":"1.0",
            "filename":name + ".jar",
            "environment":{"client":"required","server":env},
            "file":{"url":"https://cdn.modrinth.com/data/"+name+".jar",
                    "size":150,"hashes":{"sha1":"a"*40}}}

def index():
    def f(name, server="required"):
        return {"path":"mods/"+name+".jar","hashes":{"sha1":"a"*40},
                "env":{"client":"required","server":server},
                "downloads":["https://cdn.modrinth.com/"+name],"fileSize":1024}
    return {"game":"minecraft","versionId":"0.1.0-alpha",
            "name":"Full","summary":"Full",
            "dependencies":{"minecraft":"1.21.1","neoforge":"21.1.259"},
            "files":[f("buildcraft"),f("industrialcraft"),f("create"),
                     f("iris-neoforge","unsupported"),f("sodium","unsupported")]}

class LiteBuilderTests(unittest.TestCase):
    def test_client_only_and_server_unchanged(self):
        src=index()
        old_server={f["path"] for f in src["files"]
                    if f["env"]["server"]!="unsupported"}
        updated,extra=lite.derive_index(
            src,{"mods":[{"requested":"create"}]},
            [record("immediatelyfast")],["iris"])
        new_server={f["path"] for f in updated["files"]
                    if f["env"]["server"]!="unsupported"}
        self.assertEqual(old_server,new_server)
        self.assertIn("mods/industrialcraft.jar",[f["path"] for f in updated["files"]])
        self.assertNotIn("mods/iris-neoforge.jar",[f["path"] for f in updated["files"]])
        self.assertEqual(len(extra),1)
        self.assertEqual(updated["files"][-1]["env"]["server"],"unsupported")

    def test_rejects_server_mod(self):
        with self.assertRaises(lite.build_pack.BuildError):
            lite.derive_index(index(),{"mods":[]},[record("newmob","required")],["iris"])

    def test_rejects_removing_gameplay_mods(self):
        with self.assertRaises(lite.build_pack.BuildError):
            lite.derive_index(index(),{"mods":[]},[record("optimization")],
                              ["iris","industrialcraft"])

    def test_deduplicates_existing_dependency(self):
        result,extras=lite.derive_index(index(),
              {"mods":[{"requested":"create"}]},
              [record("create"),record("immediatelyfast")],["iris"])
        self.assertEqual(len(extras),1)
        self.assertEqual(len([x for x in result["files"]
                        if x["path"]=="mods/create.jar"]),1)

    def test_preserves_existing_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            src=folder/"full.mrpack"
            dest=folder/"lite.mrpack"
            lock=folder/"versions-lock.json"
            with zipfile.ZipFile(src,"w") as z:
                z.writestr("modrinth.index.json",json.dumps(index()))
                z.writestr("overrides/description.txt","not touched")
            lock.write_text(json.dumps({"mods":[]}),encoding="utf-8")
            cfg={"loader":"neoforge","minecraft":"1.21.1",
                 "lite_profile":{"exclude_projects":["iris"],
                                 "extra_client_mods":[{"project":"immediatelyfast"}]}}
            with patch.object(lite.build_pack,"resolve_manifest",
                              return_value=([record("immediatelyfast")],[])):
                lite.build_lite(src,lock,dest,cfg)
            with zipfile.ZipFile(dest) as z:
                self.assertEqual(z.read("overrides/description.txt"),b"not touched")
                self.assertIn("overrides/TECHQUEST_LITE_SETTINGS.txt",z.namelist())
                d=json.loads(z.read("modrinth.index.json"))
                self.assertEqual(d["versionId"],"0.1.0-alpha-lite")

if __name__=="__main__":
    unittest.main()

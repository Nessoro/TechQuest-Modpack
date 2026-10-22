"""Prevent explicit pins from being ignored by transitive dependency resolution."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "build_pack.py"
spec = importlib.util.spec_from_file_location("techquest_pin_resolver", SOURCE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class ResolverPinsTests(unittest.TestCase):
    def test_pins_take_precedence_over_transitive_versions(self):
        def version(project, number, date, dependencies=None):
            return {"id": project + "-" + number, "project_id": project,
                "version_number": number, "version_type": "release",
                "date_published": date, "dependencies": dependencies or [],
                "files":[{"filename": project+"-"+number+".jar", "primary": True,
                          "url":"https://example.org/"+project+".jar", "size":2048,
                          "hashes":{"sha1":"a"*40}}]}
        versions = {
            "parent":[version("parent", "1.0", "2026-01-01",
                         [{"dependency_type":"required","project_id":"library"}])],
            "library":[version("library", "2.0", "2026-07-01"),
                       version("library", "1.0-fixed", "2026-01-01")],
        }
        def fake_get_json(path, args=None):
            bits=path.split("/")
            project=bits[2]
            if len(bits)==4 and bits[3]=="version":
                return versions[project]
            return {"id": project, "title": project, "project_type":"mod",
                    "client_side":"required", "server_side":"required"}
        cfg={"loader":"neoforge","minecraft":"1.21.1",
             "mods":[{"project":"parent","required":True},
                     {"project":"library","required":True,"version_prefix":"1.0"}]}
        with patch.object(builder,"get_json",side_effect=fake_get_json):
            result,skipped=builder.resolve_manifest(cfg)
        self.assertFalse(skipped)
        self.assertEqual({x["requested"]:x["version"] for x in result}["library"],
                         "1.0-fixed")

if __name__=="__main__":
    unittest.main()

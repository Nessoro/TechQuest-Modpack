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

    def locked_fixture(self, exact_dependency=""):
        def version(identity, project, dependencies=()):
            return {"id": identity, "project_id": project, "version_number": identity,
                    "version_type": "release", "date_published": "2026-01-01" if "old" in identity else "2026-11-08",
                    "files": [{"filename": identity + ".jar", "hashes": {"sha1": "a" * 40, "sha512": "a" * 128}}],
                    "dependencies": list(dependencies)}
        dep = {"project_id": "LibraryID", "dependency_type": "required", "version_id": exact_dependency or None}
        def api(path, args=None):
            project = path.split("/")[2]
            library = project == "LibraryID"
            if path.endswith("/version"):
                return ([version("library-new", "LibraryID"), version("library-old", "LibraryID")] if library
                        else [version("parent-new", "ParentID"), version("parent-old", "ParentID", [dep])])
            return {"id": "LibraryID" if library else "ParentID", "title": project, "project_type": "mod",
                    "client_side": "required", "server_side": "required"}
        cfg = {"loader": "neoforge", "minecraft": "1.21.1", "mods": [{"project": "parent"}],
               "modrinth_lock": {project: {"version_id": version, "filename": version + ".jar", "sha512": "a" * 128,
                                            "environment": {"client": "required", "server": "required"}}
                                 for project, version in (("ParentID", "parent-old"), ("LibraryID", "library-old"))}}
        return cfg, api

    def test_project_locks_freeze_roots_and_unlisted_transitive_dependencies(self):
        cfg, api = self.locked_fixture()
        with patch.object(builder, "get_json", side_effect=api):
            records, skipped = builder.resolve_manifest(cfg)
        self.assertFalse(skipped)
        self.assertEqual({r["id"]: r["version_id"] for r in records},
                         {"ParentID": "parent-old", "LibraryID": "library-old"})

    def test_dependency_constraint_cannot_silently_override_a_lock(self):
        cfg, api = self.locked_fixture("library-new")
        with patch.object(builder, "get_json", side_effect=api):
            with self.assertRaisesRegex(builder.BuildError, "Exact version pin conflict"):
                builder.resolve_manifest(cfg)

    def test_lock_rejects_replaced_file_even_when_version_id_is_unchanged(self):
        cfg, api = self.locked_fixture()
        cfg["modrinth_lock"]["LibraryID"]["sha512"] = "b" * 128
        with patch.object(builder, "get_json", side_effect=api):
            with self.assertRaisesRegex(builder.BuildError, "file is missing or changed"):
                builder.resolve_manifest(cfg)

    def test_optional_failures_cannot_silently_shrink_a_locked_profile(self):
        cfg, api = self.locked_fixture("library-new")
        cfg["mods"][0]["required"] = False
        with patch.object(builder, "get_json", side_effect=api):
            with self.assertRaisesRegex(builder.BuildError, "Locked profile is incomplete"):
                builder.resolve_manifest(cfg)

if __name__=="__main__":
    unittest.main()

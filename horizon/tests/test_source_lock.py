"""Corruption/conflict controls for frozen source metadata; no third-party files."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from validate_source_lock import validate


class SourceLockTests(unittest.TestCase):
    def fixture(self):
        projects, versions, pins = [], [], {}
        for number in (1, 2):
            pid, vid = f"Project{number}", f"Version{number}"
            projects.append({"id": pid, "slug": f"project-{number}", "project_type": "mod",
                             "client_side": "required", "server_side": "required"})
            versions.append({"id": vid, "project_id": pid, "version_number": "1.0",
                             "game_versions": ["1.21.1"], "loaders": ["neoforge"],
                             "files": [{"filename": f"mod{number}.jar", "size": 2048,
                                        "hashes": {"sha512": str(number) * 128},
                                        "url": f"https://cdn.modrinth.com/data/{pid}/mod.jar"}],
                             "dependencies": []})
            pins[pid] = {"title": pid, "version": "1.0", "version_id": vid,
                         "filename": f"mod{number}.jar", "sha512": str(number) * 128,
                         "environment": {"client": "required", "server": "required"}}
        versions[0]["dependencies"] = [{"project_id": "Project2", "version_id": "Version2",
                                        "dependency_type": "required"}]
        source = {"minecraft": "1.21.1", "loader": "neoforge", "modrinth_lock": pins,
                  "mods": [{"project": "project-1", "required": True, "version_id": "Version1"}]}
        return source, projects, versions

    def test_missing_required_dependency_is_rejected(self):
        source, projects, versions = self.fixture()
        del source["modrinth_lock"]["Project2"]
        with self.assertRaisesRegex(ValueError, "required dependency"):
            validate(source, projects[:1], versions[:1])

    def test_tampered_hash_is_rejected(self):
        source, projects, versions = self.fixture()
        source["modrinth_lock"]["Project1"]["sha512"] = "f" * 128
        with self.assertRaisesRegex(ValueError, "file/hash"):
            validate(source, projects, versions)

    def test_exact_dependency_version_conflict_is_rejected(self):
        source, projects, versions = self.fixture()
        versions[0]["dependencies"][0]["version_id"] = "WrongVersion"
        with self.assertRaisesRegex(ValueError, "required dependency"):
            validate(source, projects, versions)

    def test_excluded_mod_hidden_by_id_is_rejected(self):
        source, projects, versions = self.fixture()
        source["mods"][0]["project"] = "Project1"
        projects[0]["slug"] = "parcool"
        with self.assertRaisesRegex(ValueError, "excluded mod"):
            validate(source, projects, versions)

    def test_missing_required_direct_project_is_rejected(self):
        source, projects, versions = self.fixture()
        source["mods"].append({"project": "missing-project", "required": True})
        with self.assertRaisesRegex(ValueError, "missing or duplicate"):
            validate(source, projects, versions)

    def test_missing_optional_project_is_explicit(self):
        source, projects, versions = self.fixture()
        source["mods"].append({"project": "missing-optional", "required": False})
        report = validate(source, projects, versions)
        self.assertEqual(report["unresolved_optional_direct_projects"], ["missing-optional"])
        self.assertEqual(report["declared_direct_modrinth_projects"], 2)
        self.assertEqual(report["resolved_direct_modrinth_projects"], 1)

    def test_wrong_loader_is_rejected(self):
        source, projects, versions = self.fixture()
        versions[0]["loaders"] = ["fabric"]
        with self.assertRaisesRegex(ValueError, "game/loader"):
            validate(source, projects, versions)

    def test_duplicate_metadata_is_rejected(self):
        source, projects, versions = self.fixture()
        with self.assertRaisesRegex(ValueError, "duplicate metadata"):
            validate(source, projects + [copy.deepcopy(projects[0])], versions)


if __name__ == "__main__":
    unittest.main()

import io
import json
import unittest
import zipfile

from scripts import audit_jar_metadata as audit


CFG = {"minecraft": "1.21.1", "loader_version": "21.1.264"}


def jar_bytes(metadata, nested=None):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as jar:
        jar.writestr("META-INF/neoforge.mods.toml", metadata)
        if nested:
            jar.writestr("META-INF/jarjar/metadata.json", json.dumps({"jars": [{"path": "nested.jar"}]}))
            jar.writestr("nested.jar", nested)
    return output.getvalue()


class MetadataTests(unittest.TestCase):
    def test_inclusive_exclusive_exact_and_union_ranges(self):
        for version, spec, expected in (
            ("1.21.1", "[1.21,1.21.1)", False),
            ("1.21.1", "[1.21,1.21.1]", True),
            ("1.21.1", "[1.21.1]", True),
            ("1.21.1", "[1.21]", False),
            ("21.1.264", "[21.1.265,)", False),
            ("21.1.264", "[21.0.0-beta,)", True),
            ("1.21.1", "(,1.20],[1.21.1,)", True),
        ):
            with self.subTest(version=version, spec=spec):
                self.assertEqual(audit.contains(version, spec), expected)

    def test_fml_121_bridge_accepts_jei_range_but_not_newer_game(self):
        rows = [{"mod_id": "jei", "origin": "jei.jar", "dependencies": [
            {"modId": "minecraft", "type": "required", "versionRange": "[1.21,1.21.1)"}]}]
        report = audit.check_records(rows, CFG, "client")
        self.assertFalse(report["errors"])
        self.assertEqual(report["fml_matrix_matches"][0]["accepted_as"], "1.21")
        rows[0]["dependencies"][0]["versionRange"] = "[1.22,)"
        self.assertTrue(audit.check_records(rows, CFG, "client")["errors"])
        rows[0]["dependencies"][0]["versionRange"] = "[1.21,1.21.1)"
        self.assertTrue(audit.check_records(rows, dict(CFG, loader_version="21.1.265"), "client")["errors"])

    def test_missing_required_library_is_checked_per_side(self):
        rows = [{"mod_id": "worldgen", "origin": "worldgen.jar", "dependencies": [
            {"modId": "library", "type": "required", "side": "SERVER"}]}]
        self.assertFalse(audit.check_records(rows, CFG, "client")["errors"])
        self.assertTrue(audit.check_records(rows, CFG, "server")["errors"])

    def test_nested_library_satisfies_dependency(self):
        library = jar_bytes('[[mods]]\nmodId="library"\n')
        parent = jar_bytes('[[mods]]\nmodId="parent"\n[[dependencies.parent]]\n'
                           'modId="library"\ntype="required"\n', library)
        rows = audit.read_metadata(parent, "parent.jar")
        self.assertEqual({row["mod_id"] for row in rows}, {"parent", "library"})
        self.assertFalse(audit.check_records(rows, CFG, "client")["errors"])

    def test_unknown_range_cannot_silently_pass(self):
        rows = [{"mod_id": "bad", "origin": "bad.jar", "dependencies": [
            {"modId": "minecraft", "versionRange": "[banana,)"}]}]
        self.assertTrue(audit.check_records(rows, CFG, "client")["errors"])

    def test_source_archive_with_mod_metadata_is_rejected(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as jar:
            jar.writestr("META-INF/neoforge.mods.toml", '[[mods]]\nmodId="forgematica"\n')
            jar.writestr("example/Main.java", "class Main {}")
        with self.assertRaisesRegex(ValueError, "Source-only JAR"):
            audit.read_metadata(output.getvalue(), "forgematica-sources.jar")


if __name__ == "__main__":
    unittest.main()

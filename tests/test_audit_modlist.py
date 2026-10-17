import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "audit_modlist.py"
spec = importlib.util.spec_from_file_location("techquest_audit_modlist", SOURCE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

class AuditTests(unittest.TestCase):
    def test_stable_release_preferred(self):
        versions = [
            {"version_number": "0.2-beta", "version_type": "beta", "date_published": "2026-10-16"},
            {"version_number": "0.1", "version_type": "release", "date_published": "2026-10-01"}
        ]
        self.assertEqual(audit.choose_version(versions)["version_number"], "0.1")

    def test_version_prefix_is_exact_enough(self):
        versions = [
            {"version_number": "8.0.23+1.21.11+neoforge", "version_type": "release", "date_published": "2026-10-16"},
            {"version_number": "8.0.23+1.21.1+neoforge", "version_type": "release", "date_published": "2026-10-01"}
        ]
        self.assertEqual(audit.choose_version(versions, "8.0.23+1.21.1+neoforge")["version_number"],
                         "8.0.23+1.21.1+neoforge")

    def test_missing_required_mod_is_reported(self):
        cfg = {"minecraft": "1.21.1", "loader": "neoforge", "loader_version": "21.1.259",
               "mods": [{"project": "core", "required": True},
                        {"project": "optional", "required": False}], "manual_mods": []}
        def fake_fetch(slug, *_):
            return [] if slug == "core" else [
                {"version_number": "1.0", "version_type": "release", "date_published": "2026-10-01"}
            ]
        with patch.object(audit.time, "sleep"):
            result = audit.audit(cfg, fake_fetch)
        self.assertEqual([row["status"] for row in result], ["missing", "available"])
        self.assertIn("Проблемных обязательных:** 1", audit.render_markdown(cfg, result))

if __name__ == "__main__":
    unittest.main()

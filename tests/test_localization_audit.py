"""Unit tests for offline locale coverage without downloading or launching Minecraft."""
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("l10n_audit", ROOT / "scripts" / "audit_localizations.py")
audit_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_mod)


class LocalizationAuditTests(unittest.TestCase):
    def test_detects_untranslated_keys_and_respects_overlay_jar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root / "one.jar", "w") as z:
                z.writestr("assets/example/lang/en_us.json", json.dumps({
                    "item.example.test": "Test item",
                    "gui.example.ok": "Ready",
                }))
                z.writestr("assets/example/lang/ru_ru.json", json.dumps({
                    "gui.example.ok": "Готово",
                }, ensure_ascii=False))
            report = audit_mod.audit(root)
            self.assertEqual(report["jar_count"], 1)
            self.assertEqual(report["total_missing_keys"], 1)
            self.assertEqual(report["namespaces"]["example"]["missing_keys"], ["item.example.test"])
            with zipfile.ZipFile(root / "two.jar", "w") as z:
                z.writestr("assets/example/lang/ru_ru.json", json.dumps({
                    "item.example.test": "Тестовый предмет",
                }, ensure_ascii=False))
            report = audit_mod.audit(root)
            self.assertEqual(report["total_missing_keys"], 0)
            self.assertEqual(report["namespaces"]["example"]["russian_keys"], 2)

    def test_corrupt_locale_is_reported_not_silently_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root / "bad.jar", "w") as z:
                z.writestr("assets/example/lang/en_us.json", '{"x":"One"}')
                z.writestr("assets/example/lang/ru_ru.json", '{"x":')
            report = audit_mod.audit(root)
            self.assertEqual(report["warning_count"], 1)
            self.assertEqual(report["namespaces"]["example"]["missing_count"], 1)

    def test_reports_placeholder_mismatch_without_claiming_missing_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with zipfile.ZipFile(root / "format.jar", "w") as z:
                z.writestr("assets/example/lang/en_us.json", json.dumps({
                    "message.example.count": "Found %1$d blocks in %2$s",
                    "message.example.safe": "Progress 100%%: %s",
                }))
                z.writestr("assets/example/lang/ru_ru.json", json.dumps({
                    "message.example.count": "Найдено %1$d блоков",
                    "message.example.safe": "Прогресс 100%%: %s",
                }, ensure_ascii=False))
            report = audit_mod.audit(root)
            self.assertEqual(report["total_missing_keys"], 0)
            self.assertEqual(report["total_placeholder_mismatches"], 1)
            self.assertEqual(report["namespaces"]["example"]["placeholder_mismatch_count"], 1)
            self.assertIn("message.example.count",
                          report["namespaces"]["example"]["placeholder_mismatches"])

    def test_empty_directory_must_not_look_like_full_translation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "No JARs"):
                audit_mod.audit(tmp)


if __name__ == "__main__":
    unittest.main()

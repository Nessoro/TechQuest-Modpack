"""Tests for the carried-YUNG official SDK validator (SDK is mocked here)."""
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import validate_yung_sdk as v


class ValidatorTests(unittest.TestCase):
    def test_missing_modules_do_not_claim_compatibility(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sdk = root / "fake-sdk"
            sdk.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            report = v.validate(root / "work", sdk)
            self.assertEqual(report["sdk_valid_count"], 0)
            self.assertEqual(report["sdk_invalid_count"], 4)
            self.assertFalse(report["all_sdk_valid"])
            self.assertTrue(all(m["result"] == "missing_carry" for m in report["modules"]))

    def test_successful_sdk_structure_never_claims_runtime(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            work = root / "work"
            for ident in v.IDS:
                carry = work / "mods" / ident / "carry"
                carry.mkdir(parents=True)
                (carry / "horizon-mod.toml").write_text(
                    f'id = "{ident}"\nname = "{ident}"\nversion = "0.1"\n'
                    'api = "0.2"\nside = "both"\ncapabilities = ["registries"]\n',
                    encoding="utf-8",
                )
            sdk = root / "fake-sdk"
            sdk.write_text(
                "#!" + sys.executable + "\n"
                "import json, pathlib, sys\n"
                "id = pathlib.Path.cwd().name\n"
                "if sys.argv[1] == 'build':\n"
                "  p = pathlib.Path('target/horizon-mod')\n"
                "  p.mkdir(parents=True, exist_ok=True)\n"
                "  (p/(id+'.hmod')).write_bytes(b'zip-placeholder')\n"
                "elif sys.argv[1] == 'check':\n"
                "  print(json.dumps({'ok': True, 'report': {'id': id, 'api':'0.2',"
                "'sha256':'test-sha','size':15}}))\n"
                "else:\n"
                "  sys.exit(1)\n",
                encoding="utf-8",
            )
            sdk.chmod(sdk.stat().st_mode | stat.S_IEXEC)
            report = v.validate(work, sdk)
            self.assertTrue(report["all_sdk_valid"])
            self.assertEqual(report["sdk_valid_count"], 4)
            self.assertFalse(report["horizon_runtime_tested"])
            self.assertFalse(report["third_party_code_migrated"])
            self.assertTrue(all(not m["runtime_tested"] and not m["gameplay_ported"] for m in report["modules"]))


if __name__ == "__main__":
    unittest.main()

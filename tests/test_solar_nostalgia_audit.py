"""Offline tests for the IC2 Nostalgia / Advanced Solar Panels static audit."""
import importlib.util
import io
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "techquest_solar_audit", ROOT / "scripts" / "audit_solar_nostalgia.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def stub_class(name):
    """Classfile constant-pool stub with one JVM CONSTANT_Class IC2 reference."""
    raw = name.encode("utf-8")
    return (bytes.fromhex("cafebabe") + struct.pack(">HHH", 0, 61, 3)
            + b"\x01" + struct.pack(">H", len(raw)) + raw
            + b"\x07\x00\x01")


def stub_jar(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for path, data in files.items():
            z.writestr(path, data)
    return buf.getvalue()


class SolarNostalgiaAuditTests(unittest.TestCase):
    def test_constant_pool_extraction_does_not_execute_java(self):
        name = "ic2/api/energy/tile/IEnergySource"
        self.assertEqual(audit.class_refs_from_bytecode(stub_class(name)), {name})
        self.assertEqual(audit.class_refs_from_bytecode(b"not a JVM class"), set())

    def test_static_inspection_detects_missing_ic2_class(self):
        required = "ic2/api/energy/tile/IEnergySource"
        ic2 = stub_jar({"META-INF/neoforge.mods.toml": '[[mods]]\nmodId="ic2"\n',
                        "ic2/core/Other.class": b"placeholder"})
        solar = stub_jar({"META-INF/neoforge.mods.toml": '[[mods]]\nmodId="advanced_solar_panels"\n',
                          "dev/solar/Main.class": stub_class(required)})
        report = audit.inspect(ic2, solar, "https://example.invalid/verified.jar")
        self.assertEqual(report["solar_ic2_missing_classes"], [required])
        self.assertFalse(report["static_class_linkage_possible"])
        self.assertFalse(report["ready_for_distribution"])
        self.assertEqual(report["runtime_compatible"], "NOT_TESTED")

    def test_static_inspection_detects_present_ic2_class(self):
        required = "ic2/api/energy/tile/IEnergySource"
        ic2 = stub_jar({"META-INF/neoforge.mods.toml": 'modId = "ic2"',
                        required + ".class": b"placeholder"})
        solar = stub_jar({"META-INF/neoforge.mods.toml": 'modId = "advanced_solar_panels"',
                          "dev/solar/Main.class": stub_class(required)})
        report = audit.inspect(ic2, solar, "https://example.invalid/verified.jar")
        self.assertEqual(report["solar_ic2_missing_classes"], [])
        self.assertTrue(report["static_class_linkage_possible"])
        self.assertFalse(report["ready_for_distribution"])

    def test_pack_keeps_current_ic2_and_does_not_install_untested_solar(self):
        cfg = json.loads((ROOT / "modlist.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["minecraft"], "1.21.1")
        self.assertEqual(cfg["loader_version"], "21.1.264")
        self.assertTrue(any(m["name"] == "Industrial Craft 2: Nostalgia" and m["required"]
                            for m in cfg["manual_mods"]))
        self.assertFalse(any("solar-panel" in row["project"] for row in cfg["mods"]))
        self.assertNotIn("advanced_solar_panels-1.1.8-1.21.1.jar",
                         {row.get("file_name") for row in cfg.get("manual_mods", [])})
        import build_pack
        self.assertTrue(hasattr(build_pack, "compatibility_jar"))


if __name__ == "__main__":
    unittest.main()

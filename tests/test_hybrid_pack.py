import hashlib
import io
import tempfile
import unittest
import json
from unittest.mock import patch
import zipfile
from pathlib import Path
import build_pack


def fake_runtime():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as jar:
        jar.writestr("META-INF/neoforge.mods.toml", 'modId="techquest_hybrid"\nversion="0.2.9-SNAPSHOT"')
        jar.writestr("dev/techquest/hybrid/HybridWarfareMod.class", b"test fixture")
    return buffer.getvalue()


class HybridPackTests(unittest.TestCase):
    def test_pack_roundtrip_and_checksum(self):
        data = fake_runtime()
        with tempfile.TemporaryDirectory() as folder:
            pack = Path(folder) / "test.mrpack"
            build_pack.make_mrpack(build_pack.load_cfg(), [], pack, hybrid_data=data)
            with zipfile.ZipFile(pack) as archive:
                self.assertEqual(build_pack.hybrid_from_pack(archive, required=True), data)
                self.assertEqual(archive.read(build_pack.HYBRID_DIGEST_ENTRY).strip(),
                                 hashlib.sha256(data).hexdigest().encode("ascii"))

    def test_reject_wrong_digest_or_duplicate_or_missing(self):
        data = fake_runtime()
        for case in ("wrong", "duplicate", "missing"):
            with self.subTest(case=case):
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as archive:
                    if case != "missing":
                        archive.writestr("overrides/mods/" + build_pack.HYBRID_JAR_NAME, data)
                    if case == "duplicate":
                        archive.writestr("overrides/mods/techquest-hybrid-warfare-old.jar", data)
                    archive.writestr(build_pack.HYBRID_DIGEST_ENTRY,
                        "0" * 64 if case == "wrong" else hashlib.sha256(data).hexdigest())
                with zipfile.ZipFile(buf) as archive:
                    with self.assertRaises(build_pack.BuildError):
                        build_pack.hybrid_from_pack(archive, required=True)

    def test_legacy_pack_and_invalid_runtime(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w"):
            pass
        with zipfile.ZipFile(buf) as archive:
            self.assertIsNone(build_pack.hybrid_from_pack(archive))
            with self.assertRaises(build_pack.BuildError):
                build_pack.hybrid_from_pack(archive, required=True)
        with self.assertRaises(build_pack.BuildError):
            build_pack.validate_hybrid_jar(b"not a jar")


class HybridPackageAuditTests(unittest.TestCase):
    def test_exact_composition_and_hashes(self):
        from scripts.audit_micro3_packages import audit

        data = fake_runtime()
        compat = build_pack.compatibility_jar()
        hybrid_name = build_pack.HYBRID_JAR_NAME
        compat_name = build_pack.COMPAT_JAR_NAME
        version = build_pack.load_cfg()["version"]

        for case in ("valid", "missing_client", "missing_server", "missing_override",
                     "wrong_client", "wrong_server", "wrong_digest", "wrong_compiled",
                     "extra_client", "extra_server", "extra_override", "duplicate_override",
                     "duplicate_index", "old_hybrid_index", "side_override"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as folder:
                output = Path(folder)
                index = {"versionId": version, "game": "minecraft",
                         "dependencies": {"minecraft": "1.21.1", "neoforge": "21.1.264"},
                         "files": [{"path": "mods/client-only.jar", "env": {"server": "unsupported"}},
                                   {"path": "mods/shared.jar"}]}
                if case in ("duplicate_index", "old_hybrid_index"):
                    index["files"].append({"path": "mods/" + (
                        hybrid_name if case == "duplicate_index" else
                        "techquest-hybrid-warfare-old.jar")})
                with zipfile.ZipFile(output / ("TechQuest_" + version + ".mrpack"), "w") as archive:
                    archive.writestr("modrinth.index.json", json.dumps(index))
                    archive.writestr("overrides/mods/" + compat_name, compat)
                    if case != "missing_override":
                        archive.writestr("overrides/mods/" + hybrid_name, data)
                    archive.writestr(build_pack.HYBRID_DIGEST_ENTRY,
                        "0" * 64 if case == "wrong_digest" else hashlib.sha256(data).hexdigest())
                    if case in ("extra_override", "duplicate_override"):
                        archive.writestr("overrides/mods/" + (
                            "unexpected.jar" if case == "extra_override" else
                            hybrid_name.upper()), data)
                    if case == "side_override":
                        archive.writestr("server-overrides/mods/" + hybrid_name, data)
                for side in ("client", "server"):
                    mods = output / side / "mods"
                    mods.mkdir(parents=True)
                    (mods / compat_name).write_bytes(compat)
                    (mods / "shared.jar").write_bytes(b"fixture")
                    if side == "client":
                        (mods / "client-only.jar").write_bytes(b"fixture")
                    if case != "missing_" + side:
                        (mods / hybrid_name).write_bytes(b"wrong" if case == "wrong_" + side else data)
                    if case == "extra_" + side:
                        (mods / "unexpected.JAR").write_bytes(b"fixture")
                with patch.object(build_pack, "compiled_hybrid_jar",
                                  return_value=b"wrong" if case == "wrong_compiled" else data):
                    if case == "valid":
                        result = audit(output)
                        self.assertEqual(result["hybrid_sha256"], hashlib.sha256(data).hexdigest())
                        self.assertIn(hybrid_name, result["client_mods"])
                        self.assertIn(hybrid_name, result["server_mods"])
                    else:
                        with self.assertRaises((ValueError, build_pack.BuildError)):
                            audit(output)

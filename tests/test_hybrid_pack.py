import hashlib
import io
import tempfile
import unittest
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

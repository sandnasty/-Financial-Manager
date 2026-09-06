from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("build_tool", ROOT / "tools/build.py")
assert SPEC and SPEC.loader
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class ReproducibleBuildTest(unittest.TestCase):
    def test_two_builds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = pathlib.Path(directory) / "one.zip"
            second = pathlib.Path(directory) / "two.zip"
            first_digest = BUILD.build(first)
            second_digest = BUILD.build(second)
            self.assertEqual(first_digest, second_digest)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_archive_has_normalized_metadata_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact = pathlib.Path(directory) / "artifact.zip"
            digest = BUILD.build(artifact)
            self.assertEqual(digest, hashlib.sha256(artifact.read_bytes()).hexdigest())
            with zipfile.ZipFile(artifact) as archive:
                self.assertIn("build-manifest.json", archive.namelist())
                self.assertIn("financial_manager/app.py", archive.namelist())
                self.assertIn("financial_manager/notification_settings.py", archive.namelist())
                self.assertIn("financial_manager/market_data.py", archive.namelist())
                self.assertIn(
                    "schemas/market-data/v1/market-data-record.schema.json",
                    archive.namelist(),
                )
                self.assertTrue(all(item.date_time == BUILD.FIXED_ZIP_TIME for item in archive.infolist()))


if __name__ == "__main__":
    unittest.main()

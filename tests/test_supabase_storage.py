"""
Unit tests for Supabase Storage Manager and dynamic bucket routing.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from ingestion.models import SensorType
from storage.manager import SupabaseStorageManager
from storage.emulator import MockSupabaseStorage


class TestSupabaseStorage(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_storage = MockSupabaseStorage(base_dir=self.temp_dir)
        self.manager = SupabaseStorageManager(use_mock=True, mock_storage=self.mock_storage)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_path_builders(self):
        self.assertEqual(
            self.manager.build_raw_path("R01", SensorType.OHRC, "product_1.zip"),
            "R01/OHRC/product_1.zip"
        )
        self.assertEqual(
            self.manager.build_raw_path("R02", SensorType.TMC_2, "triplet.zip"),
            "R02/TMC2/triplet.zip"
        )
        self.assertEqual(
            self.manager.build_raw_path("R10", SensorType.IIRS, "cube.zip"),
            "R10/IIRS/cube.zip"
        )
        self.assertEqual(
            self.manager.build_raw_path("R99", SensorType.LROC, "lroc.zip"),
            "R99/LROC/lroc.zip"
        )

    def test_upload_and_signed_url(self):
        sample_file = Path(self.temp_dir) / "sample_archive.zip"
        sample_file.write_bytes(b"PK\x03\x04sample_archive_content")

        res = self.manager.upload_raw_archive(
            archive_path=sample_file,
            region_code="R01",
            sensor=SensorType.OHRC
        )

        self.assertEqual(res["bucket"], "lunar-raw")
        self.assertEqual(res["storage_path"], "R01/OHRC/sample_archive.zip")
        self.assertTrue(self.mock_storage.exists("lunar-raw", "R01/OHRC/sample_archive.zip"))

        signed_url = self.manager.generate_signed_url("lunar-raw", res["storage_path"], expires_in_seconds=1800)
        self.assertIn("R01/OHRC/sample_archive.zip", signed_url)
        self.assertIn("token=", signed_url)


if __name__ == "__main__":
    unittest.main()

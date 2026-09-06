"""
Unit tests for 4-image region completeness validation.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from ingestion.models import SensorType
from pipeline.uploader import LunarDatasetUploader
from storage.manager import SupabaseStorageManager
from storage.emulator import MockSupabaseStorage, MockSupabaseDB
from database.connection import SupabaseDBConnection
from database.repository import SupabaseLunarRepository
from database.validation import DatasetValidator, RegionDatasetStatus
from tests.make_synthetic_dataset import create_synthetic_datasets


class TestRegionValidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_storage = MockSupabaseStorage(base_dir=Path(self.temp_dir) / "storage")
        self.mock_db = MockSupabaseDB()

        self.storage_manager = SupabaseStorageManager(use_mock=True, mock_storage=self.mock_storage)
        self.conn = SupabaseDBConnection(use_mock=True, mock_db=self.mock_db)
        self.repo = SupabaseLunarRepository(db_connection=self.conn)

        self.uploader = LunarDatasetUploader(
            storage_manager=self.storage_manager,
            repository=self.repo,
            temp_extract_dir=Path(self.temp_dir) / "extract"
        )
        self.validator = DatasetValidator(repository=self.repo)
        self.synthetic_zips = create_synthetic_datasets(Path(self.temp_dir) / "sample_zips")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_region_is_incomplete(self):
        res = self.validator.validate_region_dataset("R01")
        self.assertEqual(res.status, RegionDatasetStatus.INCOMPLETE)
        self.assertFalse(res.is_complete)
        self.assertEqual(len(res.missing_sensors), 4)
        self.assertIn("MISSING", res.summary_message)

    def test_partial_region_missing_one_sensor(self):
        # Upload OHRC, TMC-2, LROC (omit IIRS)
        self.uploader.upload_dataset(self.synthetic_zips["OHRC"], "R01", SensorType.OHRC)
        self.uploader.upload_dataset(self.synthetic_zips["TMC-2"], "R01", SensorType.TMC_2)
        self.uploader.upload_dataset(self.synthetic_zips["LROC"], "R01", SensorType.LROC)

        res = self.validator.validate_region_dataset("R01")
        self.assertEqual(res.status, RegionDatasetStatus.INCOMPLETE)
        self.assertFalse(res.is_complete)
        self.assertEqual(res.missing_sensors, ["IIRS"])
        self.assertIn("R01 -> MISSING IIRS", res.summary_message)

    def test_complete_4_image_region(self):
        # Upload all 4 required products to R01
        self.uploader.upload_dataset(self.synthetic_zips["OHRC"], "R01", SensorType.OHRC)
        self.uploader.upload_dataset(self.synthetic_zips["TMC-2"], "R01", SensorType.TMC_2)
        self.uploader.upload_dataset(self.synthetic_zips["IIRS"], "R01", SensorType.IIRS)
        self.uploader.upload_dataset(self.synthetic_zips["LROC"], "R01", SensorType.LROC)

        res = self.validator.validate_region_dataset("R01")
        self.assertEqual(res.status, RegionDatasetStatus.COMPLETE)
        self.assertTrue(res.is_complete)
        self.assertEqual(len(res.missing_sensors), 0)
        self.assertEqual(res.summary_message, "R01 -> COMPLETE")

    def test_full_database_validation_report(self):
        # Upload all 4 to R01, 3 to R02
        self.uploader.upload_dataset(self.synthetic_zips["OHRC"], "R01", SensorType.OHRC)
        self.uploader.upload_dataset(self.synthetic_zips["TMC-2"], "R01", SensorType.TMC_2)
        self.uploader.upload_dataset(self.synthetic_zips["IIRS"], "R01", SensorType.IIRS)
        self.uploader.upload_dataset(self.synthetic_zips["LROC"], "R01", SensorType.LROC)

        report = self.validator.generate_database_validation_report()
        self.assertGreaterEqual(report["total_regions"], 10)
        self.assertEqual(report["complete_regions_count"], 1)
        self.assertIn("R01", report["complete_regions"])
        self.assertIn("R02", report["missing_ohrc"])


if __name__ == "__main__":
    unittest.main()

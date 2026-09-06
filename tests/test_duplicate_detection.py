"""
Unit tests for SHA-256 duplicate detection and duplicate upload rejection.
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
from tests.make_synthetic_dataset import create_synthetic_datasets


class TestDuplicateDetection(unittest.TestCase):

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
        self.synthetic_zips = create_synthetic_datasets(Path(self.temp_dir) / "sample_zips")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_first_upload_succeeds_and_second_upload_returns_duplicate(self):
        ohrc_zip = self.synthetic_zips["OHRC"]

        # First upload: Should succeed
        res1 = self.uploader.upload_dataset(
            archive_path=ohrc_zip,
            region_code="R01",
            sensor=SensorType.OHRC
        )
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertTrue(res1["metadata_recorded"])

        initial_image_count = len(self.repo.get_all_images())
        self.assertEqual(initial_image_count, 1)

        # Second upload: Same file should return DUPLICATE_FILE
        res2 = self.uploader.upload_dataset(
            archive_path=ohrc_zip,
            region_code="R01",
            sensor=SensorType.OHRC
        )
        self.assertEqual(res2["status"], "DUPLICATE_FILE")
        self.assertIn("already exists", res2["message"])
        self.assertEqual(res2["existing_record"]["sha256"], res1["sha256"])

        # DB image count should not increase
        final_image_count = len(self.repo.get_all_images())
        self.assertEqual(final_image_count, initial_image_count)


if __name__ == "__main__":
    unittest.main()

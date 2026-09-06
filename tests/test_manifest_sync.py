"""
Unit tests for manifest to Supabase synchronization.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from pipeline.sync import ManifestSynchronizer
from storage.manager import SupabaseStorageManager
from storage.emulator import MockSupabaseStorage, MockSupabaseDB
from database.connection import SupabaseDBConnection
from database.repository import SupabaseLunarRepository
from orchestrator.pipeline import LunarPipelineOrchestrator
from ingestion.models import SensorType
from tests.make_synthetic_dataset import create_synthetic_datasets


class TestManifestSync(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mock_storage = MockSupabaseStorage(base_dir=Path(self.temp_dir) / "storage")
        self.mock_db = MockSupabaseDB()

        self.storage_manager = SupabaseStorageManager(use_mock=True, mock_storage=self.mock_storage)
        self.conn = SupabaseDBConnection(use_mock=True, mock_db=self.mock_db)
        self.repo = SupabaseLunarRepository(db_connection=self.conn)

        self.synchronizer = ManifestSynchronizer(
            repository=self.repo,
            storage_manager=self.storage_manager
        )

        # Generate a test manifest by running orchestrator locally
        self.synthetic_zips = create_synthetic_datasets(Path(self.temp_dir) / "sample_zips")
        self.reports_dir = Path(self.temp_dir) / "reports"
        orchestrator = LunarPipelineOrchestrator(
            raw_dir=Path(self.temp_dir) / "raw",
            extracted_dir=Path(self.temp_dir) / "extract",
            reports_dir=self.reports_dir
        )
        orchestrator.run({
            SensorType.OHRC: self.synthetic_zips["OHRC"],
            SensorType.TMC_2: self.synthetic_zips["TMC-2"],
            SensorType.IIRS: self.synthetic_zips["IIRS"],
            SensorType.LROC: self.synthetic_zips["LROC"]
        })

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sync_manifest_json(self):
        manifest_json = self.reports_dir / "dataset_manifest.json"
        self.assertTrue(manifest_json.exists())

        res = self.synchronizer.sync_manifest(manifest_json, default_region_code="R01")
        self.assertEqual(res["total_records"], 4)
        self.assertEqual(res["inserted_images"], 4)
        self.assertEqual(res["metadata_synced"], 4)
        self.assertEqual(len(res["errors"]), 0)

        # Re-syncing should not duplicate
        res2 = self.synchronizer.sync_manifest(manifest_json, default_region_code="R01")
        self.assertEqual(res2["inserted_images"], 0)
        self.assertEqual(res2["skipped_duplicates"], 4)


if __name__ == "__main__":
    unittest.main()

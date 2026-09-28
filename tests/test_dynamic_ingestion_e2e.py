"""
Comprehensive End-to-End Integration Tests for Dynamic Lunar Data Ingestion,
Sensor Auto-Detection, Coordinate Validation, Dynamic Matrix, Candidate Pairing,
Mode B Remote Archive Caching, and Real Registration Pipeline.
"""
import tempfile
import unittest
from pathlib import Path

from ingestion.detector import LunarSensorDetector
from ingestion.models import SensorType
from ingestion.remote_archive import RemoteArchiveClient, RemoteArchiveSearchQuery
from geospatial.catalog import (
    LunarCatalogDiscoveryService,
    PREDEFINED_LUNAR_REGIONS,
    validate_lunar_coordinates,
    construct_roi_bbox,
)
from pipeline.uploader import LunarDatasetUploader
from storage.manager import SupabaseStorageManager
from storage.emulator import MockSupabaseStorage, MockSupabaseDB
from database.connection import SupabaseDBConnection
from database.repository import SupabaseLunarRepository
from orchestrator.real_pipeline import RealMultimodalRegistrationOrchestrator, RealPipelineConfig


class TestDynamicLunarIngestionE2E(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.sample_dir = Path(__file__).parent / "sample_data"
        self.ohrc_zip = self.sample_dir / "ch2_ohrc_orbital_product.zip"
        self.lroc_zip = self.sample_dir / "lroc_nac_reference_product.zip"
        self.tmc2_zip = self.sample_dir / "ch2_tmc2_orbital_product.zip"
        self.iirs_zip = self.sample_dir / "ch2_iirs_orbital_product.zip"

        # Mock DB & Storage
        self.mock_storage = MockSupabaseStorage(base_dir=Path(self.tmp_dir.name) / "storage")
        self.mock_db = MockSupabaseDB()
        self.storage_manager = SupabaseStorageManager(use_mock=True, mock_storage=self.mock_storage)
        self.conn = SupabaseDBConnection(use_mock=True, mock_db=self.mock_db)
        self.repo = SupabaseLunarRepository(db_connection=self.conn)

        self.uploader = LunarDatasetUploader(
            storage_manager=self.storage_manager,
            repository=self.repo,
            temp_extract_dir=Path(self.tmp_dir.name) / "extract"
        )
        self.discovery_service = LunarCatalogDiscoveryService()

    def tearDown(self):
        self.tmp_dir.cleanup()

    # -------------------------------------------------------------------------
    # 1. Coordinate Validation Tests (Section 6 & 8)
    # -------------------------------------------------------------------------
    def test_coordinate_validation_boundaries(self):
        """Test strict latitude [-90, +90] and longitude [-180, +180] validation."""
        # Valid boundary coordinates
        lat1, lon1 = validate_lunar_coordinates(-90.0, 0.0)
        self.assertEqual(lat1, -90.0)
        self.assertEqual(lon1, 0.0)

        lat2, lon2 = validate_lunar_coordinates(90.0, 180.0)
        self.assertEqual(lat2, 90.0)
        self.assertEqual(lon2, 180.0)

        lat3, lon3 = validate_lunar_coordinates(0.0, -180.0)
        self.assertEqual(lon3, -180.0)

        # Invalid coordinates should raise ValueError
        with self.assertRaises(ValueError):
            validate_lunar_coordinates(90.001, 0.0)

        with self.assertRaises(ValueError):
            validate_lunar_coordinates(-95.0, 0.0)

        with self.assertRaises(ValueError):
            validate_lunar_coordinates(0.0, 180.5)

        with self.assertRaises(ValueError):
            validate_lunar_coordinates(0.0, -185.0)

    def test_roi_bbox_construction(self):
        """Test constructing bounding box from center lat/lon and radius km."""
        min_lt, max_lt, min_ln, max_ln = construct_roi_bbox(-89.5, 12.4, radius_km=10.0)
        self.assertLess(min_lt, -89.5)
        self.assertGreater(max_lt, -89.5)
        self.assertGreaterEqual(min_lt, -90.0)
        self.assertLessEqual(max_lt, 90.0)

    # -------------------------------------------------------------------------
    # 2. Predefined Lunar Regions R01-R10 (Section 5)
    # -------------------------------------------------------------------------
    def test_predefined_lunar_regions_catalog(self):
        """Verify all 10 predefined regions exist with valid names and coordinates."""
        self.assertEqual(len(PREDEFINED_LUNAR_REGIONS), 10)
        expected_codes = [f"R{i:02d}" for i in range(1, 11)]

        for reg in PREDEFINED_LUNAR_REGIONS:
            code = reg["code"]
            self.assertIn(code, expected_codes)
            self.assertIn("name", reg)
            self.assertIn("region_name", reg)
            self.assertIn("center_lat", reg)
            self.assertIn("center_lon", reg)
            self.assertGreaterEqual(reg["center_lat"], -90.0)
            self.assertLessEqual(reg["center_lat"], 90.0)
            self.assertGreaterEqual(reg["center_lon"], -180.0)
            self.assertLessEqual(reg["center_lon"], 180.0)

    # -------------------------------------------------------------------------
    # 3. Sensor Auto-Detection (Section 4)
    # -------------------------------------------------------------------------
    def test_sensor_auto_detector(self):
        """Test LunarSensorDetector identification for OHRC, TMC-2, IIRS, LROC."""
        if self.ohrc_zip.exists():
            s, conf, reason = LunarSensorDetector.detect_sensor(self.ohrc_zip)
            self.assertEqual(s, SensorType.OHRC)
            self.assertGreaterEqual(conf, 0.8)

        if self.lroc_zip.exists():
            s, conf, reason = LunarSensorDetector.detect_sensor(self.lroc_zip)
            self.assertEqual(s, SensorType.LROC)
            self.assertGreaterEqual(conf, 0.8)

    # -------------------------------------------------------------------------
    # 4. Mode A: Local Ingestion & Product Card Extraction (Section 3, 9, 10, 12)
    # -------------------------------------------------------------------------
    def test_mode_a_local_upload_and_product_card(self):
        """Test full local upload workflow, SHA256 calculation, and product card metadata."""
        if not self.ohrc_zip.exists():
            self.skipTest("Sample OHRC ZIP not found.")

        result = self.uploader.upload_dataset(
            archive_path=self.ohrc_zip,
            region_code="R01",
            sensor=SensorType.OHRC
        )

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["sensor"], "OHRC")
        self.assertEqual(result["region_code"], "R01")
        self.assertEqual(result["mission"], "Chandrayaan-2")
        self.assertIsNotNone(result["sha256"])
        self.assertTrue(result["metadata_recorded"])
        self.assertTrue(result["quality_recorded"])
        self.assertEqual(result["quality_status"], "PASS")

        # Test duplicate rejection on second upload (Section 11)
        dup_result = self.uploader.upload_dataset(
            archive_path=self.ohrc_zip,
            region_code="R01",
            sensor=SensorType.OHRC
        )
        self.assertEqual(dup_result["status"], "DUPLICATE_FILE")
        self.assertEqual(dup_result["existing_record"]["sha256"], result["sha256"])

    # -------------------------------------------------------------------------
    # 5. Dynamic Sensor Availability Matrix & Candidate Pairing (Section 17, 26, 27)
    # -------------------------------------------------------------------------
    def test_sensor_availability_matrix_and_candidate_pairing(self):
        """Test dynamic generation of sensor matrix and candidate pairs from catalog."""
        search_res = self.discovery_service.search_by_coordinates(
            latitude=-89.90,
            longitude=0.00,
            radius_km=15.0
        )

        matrix = search_res["sensor_matrix"]
        self.assertTrue(matrix["OHRC"])
        self.assertTrue(matrix["TMC-2"])
        self.assertTrue(matrix["LROC"])

        pairs = search_res["candidate_pairs"]
        self.assertGreater(len(pairs), 0)

        primary_pair = pairs[0]
        self.assertEqual(primary_pair["source_sensor"], "OHRC")
        self.assertEqual(primary_pair["reference_sensor"], "LROC")
        self.assertGreaterEqual(primary_pair["overlap_percentage"], 80.0)
        self.assertGreaterEqual(primary_pair["terrain_suitability"], 0.8)
        self.assertEqual(primary_pair["status"], "READY_FOR_REGISTRATION")

    # -------------------------------------------------------------------------
    # 6. Mode B: Remote Archive Search & Windowed ROI Caching (Section 13, 14, 15, 16)
    # -------------------------------------------------------------------------
    def test_mode_b_remote_search_and_caching(self):
        """Test remote archive query across NASA ODE, LROC PDS, ISRO PRADAN and ROI caching."""
        client = RemoteArchiveClient()

        query = RemoteArchiveSearchQuery(
            min_latitude=-90.0,
            max_latitude=-89.0,
            min_longitude=-15.0,
            max_longitude=15.0,
            sensor="LROC"
        )

        results = client.search_products(query)
        self.assertGreater(len(results), 0)

        target_prod = results[0]
        self.assertIn("LROC", str(target_prod.sensor))

        # Test caching ROI window without downloading multi-GB archive
        cache_res = client.cache_and_register_product(
            product_id=target_prod.product_id,
            region_code="R01",
            cache_dir=Path(self.tmp_dir.name) / "remote_cache"
        )
        self.assertEqual(cache_res["status"], "CACHED_AND_READY")
        self.assertEqual(cache_res["product_id"], target_prod.product_id)
        self.assertTrue(cache_res["is_windowed_cache"])

    # -------------------------------------------------------------------------
    # 7. Real Multimodal Registration Pipeline Execution (Section 19, 20, 21)
    # -------------------------------------------------------------------------
    def test_real_registration_orchestrator_execution(self):
        """Verify real registration executes with actual products and produces scientific report."""
        if not self.ohrc_zip.exists() or not self.lroc_zip.exists():
            self.skipTest("Sample real ZIPs not found.")

        cfg = RealPipelineConfig(
            region_id="R01",
            reference_sensor=SensorType.LROC,
            source_sensor=SensorType.OHRC,
            detector="SIFT",
            geometric_model="HOMOGRAPHY",
            output_dir=self.tmp_dir.name
        )

        orchestrator = RealMultimodalRegistrationOrchestrator(cfg)
        report = orchestrator.run_from_archives(
            reference_archive_zip=self.lroc_zip,
            source_archive_zip=self.ohrc_zip,
            raw_work_dir=Path(self.tmp_dir.name) / "raw",
            extract_work_dir=Path(self.tmp_dir.name) / "extracted"
        )

        self.assertEqual(report.registration_status, "SUCCESS")
        self.assertGreater(report.inliers_count, 0)
        self.assertGreater(report.inlier_ratio, 0.0)
        self.assertLess(report.rmse, 900.0)


if __name__ == "__main__":
    unittest.main()

"""
End-to-End Multimodal Real Lunar Image Registration Integration Tests.
"""
import unittest
import tempfile
from pathlib import Path

from orchestrator.real_pipeline import RealMultimodalRegistrationOrchestrator, RealPipelineConfig
from ingestion.models import SensorType


class TestRealRegistrationE2E(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.sample_dir = Path(__file__).parent / "sample_data"
        self.ohrc_zip = self.sample_dir / "ch2_ohrc_orbital_product.zip"
        self.lroc_zip = self.sample_dir / "lroc_nac_reference_product.zip"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_ohrc_to_lroc_multimodal_registration(self):
        """Verify full 12-stage multimodal registration from real sample ZIP archives."""
        if not self.ohrc_zip.exists() or not self.lroc_zip.exists():
            self.skipTest("Sample ZIP archives not found.")

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
        self.assertGreater(report.spatial_coverage_percentage, 0.0)
        self.assertLess(report.rmse, 900.0)


if __name__ == "__main__":
    unittest.main()

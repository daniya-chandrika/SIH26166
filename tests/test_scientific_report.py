"""
Unit Tests for Scientific Report Generator.
"""
import unittest
import tempfile
from pathlib import Path

from reports.scientific_report import ScientificReportGenerator


class TestScientificReport(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_markdown_report_structure(self):
        """Verify report contains all 14 required scientific sections."""
        config = {
            "scenario": "combined",
            "seed": 42,
            "detector": "SIFT",
            "model": "HOMOGRAPHY",
            "reference_sensor": "LROC NAC",
            "source_sensor": "OHRC"
        }
        metrics = {
            "registration_status": "SUCCESS",
            "reprojection_rmse_px": 0.85,
            "mae": 0.04,
            "ssim": 0.78,
            "psnr_db": 28.5,
            "mutual_information": 0.95,
            "normalized_cross_correlation": 0.82,
            "initial_keypoints_ref": 1500,
            "initial_keypoints_src": 1600,
            "candidate_matches": 450,
            "filtered_matches": 380,
            "inliers_count": 310,
            "inlier_ratio": 0.815,
            "spatial_coverage_percentage": 92.0,
            "occupied_grid_cells": 59,
            "total_grid_cells": 64,
            "subpixel_mean_displacement_px": 0.42,
            "subpixel_convergence_rate": 0.88,
            "ground_truth_metrics": {
                "translation_error_px": 0.25,
                "rotation_error_deg": 0.05,
                "scale_error": 1.002,
                "corner_reprojection_rmse_px": 0.35,
                "matrix_frobenius_norm_diff": 0.001
            }
        }
        transform_data = {
            "model": "HOMOGRAPHY",
            "estimator": "USAC_MAGSAC",
            "matrix": [[1.0, 0.0, 5.0], [0.0, 1.0, 2.0], [0.0, 0.0, 1.0]]
        }

        md = ScientificReportGenerator.generate_markdown_report(
            experiment_id="SIH26166_TEST_EXP_01",
            config=config,
            metrics=metrics,
            transform_data=transform_data,
            is_synthetic=True
        )

        self.assertIn("1. Experiment Information", md)
        self.assertIn("2. Input Products & Sensor Configuration", md)
        self.assertIn("3. Physical & Photometric Metadata", md)
        self.assertIn("4. Geographic Footprint & Overlap Validation", md)
        self.assertIn("5. Quality Assurance", md)
        self.assertIn("6. Preprocessing & Normalization", md)
        self.assertIn("7. Correspondence & Feature Detection", md)
        self.assertIn("8. Matching Statistics & Spatial Distribution", md)
        self.assertIn("9. Geometric Transformation", md)
        self.assertIn("10. Ground-Truth Control Points", md)
        self.assertIn("11. Multi-Dimensional Scientific Accuracy Metrics", md)
        self.assertIn("12. Failure Detection & Convergence Analysis", md)
        self.assertIn("13. Output Artifacts & Visualizations", md)
        self.assertIn("14. Reproducibility & Provenance Information", md)
        self.assertIn("[SYNTHETIC BENCHMARK DATASET]", md)

    def test_save_report_to_disk(self):
        """Verify saving report file to run directory."""
        run_dir = Path(self.tmp_dir.name)
        p = ScientificReportGenerator.save_report(
            run_dir=run_dir,
            experiment_id="EXP_DISK_TEST",
            config={"scenario": "scale"},
            metrics={"registration_status": "SUCCESS"},
            transform_data={"model": "HOMOGRAPHY"},
            is_synthetic=False
        )
        self.assertTrue(p.exists())
        self.assertIn("[AUTHENTIC ORBITAL FLIGHT DATA]", p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

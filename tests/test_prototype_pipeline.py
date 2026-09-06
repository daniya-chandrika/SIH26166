"""
Unit tests for Full 12-Stage Prototype Registration Pipeline (Phases 19-20).
"""
import unittest
from pathlib import Path
import tempfile
import shutil
import numpy as np

from prototype.data_interface import ImagePair
from orchestrator.prototype_pipeline import (
    PrototypeRegistrationOrchestrator,
    PrototypePipelineConfig
)


class TestPrototypePipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_pipeline_success(self):
        """Verify full 12-stage orchestrator succeeds end-to-end and saves artifacts."""
        cfg = PrototypePipelineConfig(
            scenario="rotation_translation",
            seed=42,
            image_width=128,
            image_height=128,
            detector="SIFT",
            geometric_model="HOMOGRAPHY",
            output_dir=str(self.temp_dir)
        )
        orchestrator = PrototypeRegistrationOrchestrator(cfg)
        report = orchestrator.run()

        self.assertEqual(report.registration_status, "SUCCESS")
        self.assertGreater(report.inliers_count, 0)
        self.assertGreater(report.spatial_coverage_percentage, 50.0)
        self.assertIsNotNone(report.ground_truth_metrics)

        # Verify run directory structure
        run_dirs = list(self.temp_dir.glob("SIH26166_EXP_*"))
        self.assertEqual(len(run_dirs), 1)
        run_dir = run_dirs[0]

        self.assertTrue((run_dir / "config.json").exists())
        self.assertTrue((run_dir / "metrics.json").exists())
        self.assertTrue((run_dir / "transform.json").exists())
        self.assertTrue((run_dir / "ground_truth.json").exists())
        self.assertTrue((run_dir / "logs.txt").exists())
        self.assertTrue((run_dir / "visualizations").exists())
        self.assertTrue((run_dir / "registered").exists())
        self.assertTrue((run_dir / "registered" / "registered.png").exists())

    def test_pipeline_with_orb_detector(self):
        """Verify prototype pipeline executes with ORB detector."""
        cfg = PrototypePipelineConfig(
            scenario="scale",
            seed=10,
            image_width=128,
            image_height=128,
            detector="ORB",
            geometric_model="AFFINE",
            output_dir=str(self.temp_dir)
        )
        orchestrator = PrototypeRegistrationOrchestrator(cfg)
        report = orchestrator.run()

        self.assertEqual(report.registration_status, "SUCCESS")
        self.assertEqual(report.geometric_model, "AFFINE")

    def test_pipeline_failure_handling_blank_image(self):
        """Verify pipeline handles blank image gracefully with REGISTRATION_FAILED status."""
        blank = np.zeros((128, 128), dtype=np.float32)
        blank_pair = ImagePair(
            reference=blank,
            source=blank,
            scenario_name="blank_test",
            name="blank_pair"
        )
        cfg = PrototypePipelineConfig(output_dir=str(self.temp_dir))
        orchestrator = PrototypeRegistrationOrchestrator(cfg)
        report = orchestrator.run(input_pair=blank_pair)

        self.assertEqual(report.registration_status, "REGISTRATION_FAILED")
        self.assertIsNotNone(report.failure_reason)


if __name__ == "__main__":
    unittest.main()

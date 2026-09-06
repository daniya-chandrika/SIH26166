"""
Unit tests for Image Warping, Registration, Metrics, and Evaluation (Phases 16-17).
"""
import unittest
import numpy as np
from pathlib import Path
import tempfile
import shutil

from geometry.base import TransformationResult
from registration.warp import ImageWarper
from registration.pipeline import RegistrationPipeline
from evaluation.metrics import RegistrationMetricsCalculator
from evaluation.reporter import EvaluationReporter
from evaluation.visualization import RegistrationVisualizer


class TestRegistrationAndEvaluation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_image_warper_identity(self):
        """Verify identity matrix produces identical warped image."""
        img = np.random.rand(64, 64).astype(np.float32)
        H_eye = np.eye(3, dtype=np.float64)

        warped, mask = ImageWarper.warp_source_to_reference(
            source_image=img,
            H_matrix=H_eye,
            reference_shape=(64, 64)
        )

        np.testing.assert_allclose(warped, img, atol=1e-5)
        self.assertTrue(mask.all())

    def test_registration_pipeline_difference_map(self):
        """Verify registration generates difference map and overlays."""
        ref = np.full((64, 64), 0.5, dtype=np.float32)
        src = np.full((64, 64), 0.8, dtype=np.float32)
        H_eye = np.eye(3, dtype=np.float64)

        transform_res = TransformationResult(
            transformation_type="HOMOGRAPHY",
            matrix=H_eye,
            inliers_count=10,
            inlier_ratio=1.0,
            residual_rmse=0.0
        )

        pipeline = RegistrationPipeline()
        out = pipeline.register(src, ref, transform_res)

        self.assertEqual(out.registered_image.shape, (64, 64))
        self.assertAlmostEqual(float(out.difference_map[0, 0]), 0.3, places=4)

    def test_metrics_calculator_identical_images(self):
        """Verify identical images yield SSIM = 1.0, NCC = 1.0, RMSE = 0.0, PSNR = 100."""
        img = np.random.rand(64, 64).astype(np.float32)
        calc = RegistrationMetricsCalculator()
        metrics = calc.evaluate(img, img)

        self.assertAlmostEqual(metrics.rmse_pixels, 0.0, places=5)
        self.assertAlmostEqual(metrics.mae_pixels, 0.0, places=5)
        self.assertAlmostEqual(metrics.ssim, 1.0, places=3)
        self.assertAlmostEqual(metrics.normalized_cross_correlation, 1.0, places=3)
        self.assertEqual(metrics.psnr_db, 100.0)

    def test_visualization_generation(self):
        """Verify visualizer creates all expected diagnostic PNG files."""
        ref = np.random.rand(64, 64).astype(np.float32)
        src = np.random.rand(64, 64).astype(np.float32)
        reg = np.random.rand(64, 64).astype(np.float32)
        diff = np.abs(ref - reg)

        ref_pts = np.array([[10, 10], [20, 20], [30, 30]], dtype=np.float32)
        src_pts = np.array([[12, 12], [22, 22], [32, 32]], dtype=np.float32)
        inlier_mask = np.array([True, True, False])

        calc = RegistrationMetricsCalculator()
        base_metrics = calc.evaluate(reg, ref)

        from evaluation.metrics import FullEvaluationReport
        report = FullEvaluationReport(
            rmse=base_metrics.rmse_pixels,
            mae=base_metrics.mae_pixels,
            ssim=base_metrics.ssim,
            psnr_db=base_metrics.psnr_db,
            mutual_information=base_metrics.mutual_information,
            normalized_cross_correlation=base_metrics.normalized_cross_correlation,
            initial_keypoints_ref=50,
            initial_keypoints_src=60,
            candidate_matches=30,
            filtered_matches=25,
            inliers_count=2,
            inlier_ratio=0.8,
            spatial_coverage_percentage=50.0,
            occupied_grid_cells=8,
            total_grid_cells=16,
            reprojection_rmse_px=0.5,
            geometric_model="HOMOGRAPHY",
            estimator="USAC_MAGSAC",
            subpixel_mean_displacement_px=0.1,
            subpixel_convergence_rate=1.0,
            registration_status="SUCCESS"
        )

        vis_paths = RegistrationVisualizer.generate_all_visualizations(
            ref_img=ref,
            src_img=src,
            reg_img=reg,
            diff_map=diff,
            ref_pts=ref_pts,
            src_pts=src_pts,
            inliers_mask=inlier_mask,
            report=report,
            output_dir=self.temp_dir
        )

        self.assertEqual(len(vis_paths), 5)
        for p in vis_paths:
            self.assertTrue(p.exists())


if __name__ == "__main__":
    unittest.main()

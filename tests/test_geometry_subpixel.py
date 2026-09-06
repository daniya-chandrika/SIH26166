"""
Unit tests for Robust Geometry Estimation and Sub-pixel Refinement (Phases 14-15).
"""
import unittest
import numpy as np

from geometry.models import GeometricModelType
from geometry.robust import RobustGeometryFitter
from geometry.estimator import RobustGeometricEstimator
from subpixel.refinement import SubpixelRefiner


class TestGeometryAndSubpixel(unittest.TestCase):

    def test_fit_homography_exact_points(self):
        """Verify homography estimation recovers known ground truth transformation."""
        src_pts = np.array([
            [10.0, 10.0],
            [100.0, 10.0],
            [100.0, 100.0],
            [10.0, 100.0],
            [55.0, 55.0]
        ], dtype=np.float32)

        # Shift by (15, 25)
        dst_pts = src_pts + np.array([15.0, 25.0], dtype=np.float32)

        H, inliers, method = RobustGeometryFitter.fit_homography(src_pts, dst_pts)

        self.assertIsNotNone(H)
        self.assertEqual(H.shape, (3, 3))
        self.assertEqual(np.sum(inliers), 5)

        # Verify translation in matrix
        self.assertAlmostEqual(H[0, 2], 15.0, places=3)
        self.assertAlmostEqual(H[1, 2], 25.0, places=3)

    def test_fit_affine_exact_points(self):
        """Verify affine estimation recovers known translation."""
        src_pts = np.array([
            [10.0, 10.0],
            [100.0, 10.0],
            [50.0, 80.0],
            [20.0, 90.0]
        ], dtype=np.float32)
        dst_pts = src_pts + np.array([8.0, -12.0], dtype=np.float32)

        H, inliers, method = RobustGeometryFitter.fit_affine(src_pts, dst_pts)

        self.assertIsNotNone(H)
        self.assertEqual(H.shape, (3, 3))
        self.assertEqual(np.sum(inliers), 4)
        self.assertAlmostEqual(H[0, 2], 8.0, places=3)
        self.assertAlmostEqual(H[1, 2], -12.0, places=3)

    def test_insufficient_points_failure_handling(self):
        """Verify estimator returns clean failure with < 4 points."""
        src_pts = np.array([[10.0, 10.0], [20.0, 20.0]], dtype=np.float32)
        dst_pts = np.array([[12.0, 12.0], [22.0, 22.0]], dtype=np.float32)

        estimator = RobustGeometricEstimator(model_type=GeometricModelType.HOMOGRAPHY)
        res = estimator.estimate_transformation(src_pts, dst_pts)

        self.assertIsNone(res.matrix)
        self.assertEqual(res.inliers_count, 0)
        self.assertEqual(res.estimator, "INSUFFICIENT_POINTS")

    def test_subpixel_refiner(self):
        """Verify SubpixelRefiner executes template cross-correlation and finds peak."""
        # Create identical patches with smooth Gaussian crater feature centered at (30.0, 30.0)
        y, x = np.mgrid[:64, :64]
        ref_img = np.exp(-((x - 30.0)**2 + (y - 30.0)**2) / (2.0 * 5.0**2)).astype(np.float32)
        src_img = np.copy(ref_img)

        src_pts = np.array([[30.0, 30.0]], dtype=np.float32)
        ref_pts = np.array([[30.0, 30.0]], dtype=np.float32)

        refiner = SubpixelRefiner(patch_size=11, search_radius=3)
        sub_res = refiner.refine(src_img, ref_img, src_pts, ref_pts)

        self.assertEqual(len(sub_res.refined_ref_points), 1)
        self.assertAlmostEqual(sub_res.refined_ref_points[0][0], 30.0, places=1)
        self.assertAlmostEqual(sub_res.refined_ref_points[0][1], 30.0, places=1)
        self.assertGreaterEqual(sub_res.convergence_rate, 0.99)


if __name__ == "__main__":
    unittest.main()

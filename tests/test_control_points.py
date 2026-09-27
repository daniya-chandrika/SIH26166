"""
Unit Tests for Control Points and Ground-Truth Evaluation Subsystem.
"""
import unittest
import numpy as np

from evaluation.control_points import (
    ControlPoint,
    ControlPointType,
    ControlPointManager,
    ControlPointEvaluationResult
)


class TestControlPoints(unittest.TestCase):

    def test_control_point_classification(self):
        """Verify distinct point classifications (GROUND_TRUTH vs ALGORITHMIC_INLIER)."""
        cp_gt = ControlPoint(
            source_x=100.0, source_y=150.0,
            reference_x=110.0, reference_y=155.0,
            point_type=ControlPointType.GROUND_TRUTH,
            annotator="SURVEYOR"
        )
        cp_inl = ControlPoint(
            source_x=200.0, source_y=250.0,
            reference_x=210.0, reference_y=255.0,
            point_type=ControlPointType.ALGORITHMIC_INLIER,
            annotator="RANSAC"
        )

        manager = ControlPointManager([cp_gt, cp_inl])
        gt_pts = manager.get_ground_truth_points()
        inl_pts = manager.get_algorithmic_inliers()

        self.assertEqual(len(gt_pts), 1)
        self.assertEqual(gt_pts[0].point_type, ControlPointType.GROUND_TRUTH)
        self.assertEqual(len(inl_pts), 1)
        self.assertEqual(inl_pts[0].point_type, ControlPointType.ALGORITHMIC_INLIER)

    def test_evaluate_transformation_accuracy(self):
        """Verify ground-truth RMSE and residual calculation against known transformation."""
        # 10 ground truth points translated by tx=+10, ty=+5
        src_pts = np.array([[10, 10], [50, 50], [100, 80], [150, 200]], dtype=np.float32)
        ref_pts = src_pts + np.array([10.0, 5.0], dtype=np.float32)

        manager = ControlPointManager()
        manager.add_points_from_arrays(
            src_points=src_pts,
            ref_points=ref_pts,
            point_type=ControlPointType.GROUND_TRUTH,
            annotator="SYNTHETIC_GT"
        )

        # Exact transformation matrix: tx=10, ty=5
        H_exact = np.array([
            [1.0, 0.0, 10.0],
            [0.0, 1.0, 5.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        res_exact = manager.evaluate_transformation(H_exact, tolerance_px=0.5)
        self.assertEqual(res_exact.evaluation_type, "GROUND_TRUTH_BASED")
        self.assertAlmostEqual(res_exact.rmse_px, 0.0, places=4)
        self.assertEqual(res_exact.passed_tolerance_percentage, 100.0)

        # Inexact transformation matrix with +1.0px shift error
        H_shifted = np.array([
            [1.0, 0.0, 11.0],
            [0.0, 1.0, 5.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        res_shifted = manager.evaluate_transformation(H_shifted, tolerance_px=0.5)
        self.assertAlmostEqual(res_shifted.rmse_px, 1.0, places=3)
        self.assertEqual(res_shifted.passed_tolerance_percentage, 0.0)

    def test_serialization_and_deserialization(self):
        """Verify JSON round-trip serialization of control points."""
        cp = ControlPoint(
            source_x=12.5, source_y=34.5,
            reference_x=15.0, reference_y=37.0,
            point_type=ControlPointType.MANUAL_CHECK,
            annotator="EXPERT_1",
            confidence=0.95
        )
        manager = ControlPointManager([cp])
        data = manager.to_list()
        restored_manager = ControlPointManager.from_list(data)

        self.assertEqual(len(restored_manager.points), 1)
        self.assertEqual(restored_manager.points[0].source_x, 12.5)
        self.assertEqual(restored_manager.points[0].point_type, ControlPointType.MANUAL_CHECK)


if __name__ == "__main__":
    unittest.main()

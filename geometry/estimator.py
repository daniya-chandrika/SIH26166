"""
Robust Geometric Estimator for SIH26166.
Orchestrates Homography / Affine transformation estimation, inlier filtering,
and reprojection RMSE computation.
"""
from typing import Optional, Dict, Any
import numpy as np

from geometry.base import GeometricEstimatorBase, TransformationResult
from geometry.models import GeometricModelType
from geometry.robust import RobustGeometryFitter


class RobustGeometricEstimator(GeometricEstimatorBase):
    """
    Computes robust coordinate mapping between source and reference lunar frames.
    """

    def __init__(
        self,
        model_type: GeometricModelType = GeometricModelType.HOMOGRAPHY,
        min_inliers_required: int = 6,
        max_reprojection_error_pixels: float = 3.0
    ):
        self.model_type = model_type
        self.min_inliers_required = min_inliers_required
        self.max_reprojection_error_pixels = max_reprojection_error_pixels

    @staticmethod
    def compute_reprojection_rmse(
        src_points: np.ndarray,
        dst_points: np.ndarray,
        H: np.ndarray,
        inliers_mask: Optional[np.ndarray] = None
    ) -> float:
        """
        Calculate Root Mean Squared Reprojection Error (RMSE) on inlier correspondences.
        """
        if inliers_mask is not None:
            src_inliers = src_points[inliers_mask]
            dst_inliers = dst_points[inliers_mask]
        else:
            src_inliers = src_points
            dst_inliers = dst_points

        if len(src_inliers) == 0:
            return 0.0

        # Convert to homogeneous coords
        ones = np.ones((len(src_inliers), 1), dtype=np.float64)
        src_homo = np.hstack([src_inliers, ones])  # (K, 3)

        # Map to reference: p_est = H * p_src
        projected = (H @ src_homo.T).T  # (K, 3)
        # Normalize by z coordinate
        z = projected[:, 2:3]
        z[np.abs(z) < 1e-12] = 1e-12
        projected_xy = projected[:, :2] / z

        # Residual Euclidean distance
        residuals = np.linalg.norm(dst_inliers - projected_xy, axis=1)
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        return rmse

    def estimate_transformation(
        self,
        src_points: np.ndarray,
        dst_points: np.ndarray,
        confidence_scores: Optional[np.ndarray] = None,
        max_reprojection_error_pixels: Optional[float] = None
    ) -> TransformationResult:
        reproj_thresh = max_reprojection_error_pixels or self.max_reprojection_error_pixels
        total_pts = len(src_points)

        if not RobustGeometryFitter.check_minimal_points(total_pts, self.model_type):
            return TransformationResult(
                transformation_type=self.model_type.value,
                matrix=None,
                inliers_count=0,
                inlier_ratio=0.0,
                inliers_mask=np.zeros((total_pts,), dtype=bool),
                residual_rmse=0.0,
                estimator="INSUFFICIENT_POINTS"
            )

        if self.model_type == GeometricModelType.HOMOGRAPHY:
            H, inlier_mask, estimator_name = RobustGeometryFitter.fit_homography(
                src_points, dst_points, max_reprojection_error=reproj_thresh
            )
        else:
            H, inlier_mask, estimator_name = RobustGeometryFitter.fit_affine(
                src_points, dst_points, max_reprojection_error=reproj_thresh
            )

        if H is None or inlier_mask is None:
            return TransformationResult(
                transformation_type=self.model_type.value,
                matrix=None,
                inliers_count=0,
                inlier_ratio=0.0,
                inliers_mask=np.zeros((total_pts,), dtype=bool),
                residual_rmse=0.0,
                estimator="ESTIMATION_FAILED"
            )

        inliers_count = int(np.sum(inlier_mask))
        inlier_ratio = float(inliers_count / total_pts) if total_pts > 0 else 0.0

        if inliers_count < self.min_inliers_required:
            return TransformationResult(
                transformation_type=self.model_type.value,
                matrix=None,
                inliers_count=inliers_count,
                inlier_ratio=inlier_ratio,
                inliers_mask=inlier_mask,
                residual_rmse=0.0,
                estimator="INSUFFICIENT_INLIERS"
            )

        # Compute reprojection RMSE
        rmse = self.compute_reprojection_rmse(src_points, dst_points, H, inliers_mask=inlier_mask)

        return TransformationResult(
            transformation_type=self.model_type.value,
            matrix=H,
            inliers_count=inliers_count,
            inlier_ratio=inlier_ratio,
            inliers_mask=inlier_mask,
            residual_rmse=rmse,
            estimator=estimator_name
        )

"""
Robust Estimation Wrappers for SIH26166.
Supports RANSAC and USAC_MAGSAC for Affine and Homography models.
"""
from typing import Tuple, Optional
import numpy as np
import cv2

from geometry.models import GeometricModelType


class RobustGeometryFitter:
    """
    Fits robust geometric models to keypoint correspondences while suppressing spatial outliers.
    """

    @staticmethod
    def check_minimal_points(points_count: int, model_type: GeometricModelType) -> bool:
        """Verify sufficient correspondences exist for estimation."""
        if model_type == GeometricModelType.HOMOGRAPHY:
            return points_count >= 4
        elif model_type in [GeometricModelType.AFFINE, GeometricModelType.RIGID]:
            return points_count >= 3
        return False

    @classmethod
    def fit_homography(
        cls,
        src_points: np.ndarray,
        dst_points: np.ndarray,
        max_reprojection_error: float = 3.0,
        confidence: float = 0.995,
        max_iters: int = 2000
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], str]:
        """
        Estimate 3x3 Projective Homography matrix mapping src_points to dst_points.
        Returns: (H_matrix, inlier_mask, estimator_name)
        """
        if len(src_points) < 4:
            return None, None, "NONE"

        # Try USAC_MAGSAC if available, else standard RANSAC
        method = getattr(cv2, "USAC_MAGSAC", cv2.RANSAC)
        estimator_name = "USAC_MAGSAC" if hasattr(cv2, "USAC_MAGSAC") else "RANSAC"

        try:
            H, mask = cv2.findHomography(
                src_points,
                dst_points,
                method=method,
                ransacReprojThreshold=max_reprojection_error,
                maxIters=max_iters,
                confidence=confidence
            )
            if H is not None and mask is not None:
                # Normalize matrix so H_33 == 1
                if abs(H[2, 2]) > 1e-12:
                    H = H / H[2, 2]
                return H, mask.ravel().astype(bool), estimator_name
        except Exception:
            pass

        # Fallback to standard RANSAC
        try:
            H, mask = cv2.findHomography(
                src_points,
                dst_points,
                method=cv2.RANSAC,
                ransacReprojThreshold=max_reprojection_error,
                maxIters=max_iters,
                confidence=confidence
            )
            if H is not None and mask is not None:
                if abs(H[2, 2]) > 1e-12:
                    H = H / H[2, 2]
                return H, mask.ravel().astype(bool), "RANSAC"
        except Exception:
            pass

        return None, None, "FAILED"

    @classmethod
    def fit_affine(
        cls,
        src_points: np.ndarray,
        dst_points: np.ndarray,
        max_reprojection_error: float = 3.0,
        confidence: float = 0.995,
        max_iters: int = 2000
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], str]:
        """
        Estimate 2x3 (converted to 3x3) Affine matrix mapping src_points to dst_points.
        Returns: (H_matrix_3x3, inlier_mask, estimator_name)
        """
        if len(src_points) < 3:
            return None, None, "NONE"

        try:
            A_2x3, mask = cv2.estimateAffine2D(
                src_points,
                dst_points,
                method=cv2.RANSAC,
                ransacReprojThreshold=max_reprojection_error,
                maxIters=max_iters,
                confidence=confidence
            )
            if A_2x3 is not None and mask is not None:
                # Expand 2x3 affine matrix to 3x3 projective matrix
                H_3x3 = np.eye(3, dtype=np.float64)
                H_3x3[:2, :] = A_2x3
                return H_3x3, mask.ravel().astype(bool), "RANSAC_AFFINE"
        except Exception:
            pass

        return None, None, "FAILED"

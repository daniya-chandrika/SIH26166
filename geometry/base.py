"""
Geometric Estimation and Spatial Transformation Interface.
[Placeholder for Phase 12: Robust Geometric Estimation & RANSAC]
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class TransformationResult:
    transformation_type: str        # 'HOMOGRAPHY', 'AFFINE', 'RIGID', 'TPS', 'SPLINE'
    matrix: Optional[np.ndarray] = None    # 3x3 homography or affine matrix
    inliers_count: int = 0
    inlier_ratio: float = 0.0
    inliers_mask: Optional[np.ndarray] = None
    residual_rmse: float = 0.0
    estimator: str = "RANSAC"


class GeometricEstimatorBase(ABC):
    """
    Abstract interface for robust geometric model estimation (RANSAC, MAGSAC++, USAC).
    """

    @abstractmethod
    def estimate_transformation(
        self,
        src_points: np.ndarray,
        dst_points: np.ndarray,
        confidence_scores: Optional[np.ndarray] = None,
        max_reprojection_error_pixels: float = 3.0
    ) -> TransformationResult:
        """Estimate optimal coordinate transformation matrix filtering out spatial outliers."""
        pass

"""
Ground Truth Transformation Verification and Metric Benchmark for SIH26166.
Compares estimated transformation matrices against analytical ground-truth matrices.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple
import numpy as np


@dataclass
class GroundTruthComparisonMetrics:
    translation_error_px: float
    rotation_error_deg: float
    scale_error: float
    corner_reprojection_rmse_px: float
    matrix_frobenius_norm_diff: float
    ground_truth_rotation_deg: float
    estimated_rotation_deg: float
    ground_truth_scale: float
    estimated_scale: float
    ground_truth_translation_px: Tuple[float, float]
    estimated_translation_px: Tuple[float, float]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ground_truth_translation_px"] = list(self.ground_truth_translation_px)
        d["estimated_translation_px"] = list(self.estimated_translation_px)
        return d


class GroundTruthTransform:
    """
    Encapsulates ground truth 3x3 transformation matrix and provides verification tools.
    """

    def __init__(self, matrix: np.ndarray, parameters: Optional[Dict[str, Any]] = None):
        self.matrix = matrix.astype(np.float64)
        if abs(self.matrix[2, 2]) > 1e-12:
            self.matrix = self.matrix / self.matrix[2, 2]
        self.parameters = parameters or {}

    @staticmethod
    def decompose_matrix(H: np.ndarray) -> Dict[str, Any]:
        """
        Decompose affine/homography 3x3 matrix into scale, rotation, and translation components.
        """
        H_norm = H / H[2, 2] if abs(H[2, 2]) > 1e-12 else H
        a11 = H_norm[0, 0]
        a12 = H_norm[0, 1]
        a21 = H_norm[1, 0]
        a22 = H_norm[1, 1]
        tx = H_norm[0, 2]
        ty = H_norm[1, 2]

        # Estimated scale
        sx = np.sqrt(a11 ** 2 + a21 ** 2)
        sy = np.sqrt(a12 ** 2 + a22 ** 2)
        scale = (sx + sy) / 2.0

        # Estimated rotation angle
        rotation_rad = np.arctan2(a21, a11)
        rotation_deg = np.degrees(rotation_rad) % 360.0

        return {
            "scale": float(scale),
            "scale_x": float(sx),
            "scale_y": float(sy),
            "rotation_deg": float(rotation_deg),
            "translation_x": float(tx),
            "translation_y": float(ty),
        }

    def compare(
        self,
        H_est: np.ndarray,
        image_width: int = 512,
        image_height: int = 512
    ) -> GroundTruthComparisonMetrics:
        """
        Quantitatively compare estimated transformation H_est with ground truth H_gt.
        """
        H_gt_norm = self.matrix / self.matrix[2, 2] if abs(self.matrix[2, 2]) > 1e-12 else self.matrix
        H_est_norm = H_est / H_est[2, 2] if abs(H_est[2, 2]) > 1e-12 else H_est

        # 1. Decompose both
        decomp_gt = self.decompose_matrix(H_gt_norm)
        decomp_est = self.decompose_matrix(H_est_norm)

        # Translation error
        gt_tx, gt_ty = decomp_gt["translation_x"], decomp_gt["translation_y"]
        est_tx, est_ty = decomp_est["translation_x"], decomp_est["translation_y"]
        trans_err = float(np.sqrt((est_tx - gt_tx) ** 2 + (est_ty - gt_ty) ** 2))

        # Rotation error (handling angular wraparound)
        rot_diff = abs(decomp_est["rotation_deg"] - decomp_gt["rotation_deg"]) % 360.0
        if rot_diff > 180.0:
            rot_diff = 360.0 - rot_diff
        rot_err = float(rot_diff)

        # Scale error
        scale_err = float(abs(decomp_est["scale"] - decomp_gt["scale"]))

        # 2. Corner Reprojection Error
        # Reference test points: 4 corners + center
        corners = np.array([
            [0.0, 0.0, 1.0],
            [image_width, 0.0, 1.0],
            [image_width, image_height, 1.0],
            [0.0, image_height, 1.0],
            [image_width / 2.0, image_height / 2.0, 1.0]
        ], dtype=np.float64).T  # Shape (3, 5)

        # Transform with GT: p_ref_gt = H_gt * p_src
        p_gt = H_gt_norm @ corners
        p_gt = p_gt[:2] / p_gt[2:3]

        # Transform with Est: p_ref_est = H_est * p_src
        p_est = H_est_norm @ corners
        p_est = p_est[:2] / p_est[2:3]

        corner_diffs = np.linalg.norm(p_est - p_gt, axis=0)
        corner_rmse = float(np.sqrt(np.mean(corner_diffs ** 2)))

        # 3. Frobenius Norm of Matrix Difference
        frobenius_diff = float(np.linalg.norm(H_est_norm - H_gt_norm, 'fro'))

        return GroundTruthComparisonMetrics(
            translation_error_px=trans_err,
            rotation_error_deg=rot_err,
            scale_error=scale_err,
            corner_reprojection_rmse_px=corner_rmse,
            matrix_frobenius_norm_diff=frobenius_diff,
            ground_truth_rotation_deg=decomp_gt["rotation_deg"],
            estimated_rotation_deg=decomp_est["rotation_deg"],
            ground_truth_scale=decomp_gt["scale"],
            estimated_scale=decomp_est["scale"],
            ground_truth_translation_px=(gt_tx, gt_ty),
            estimated_translation_px=(est_tx, est_ty)
        )

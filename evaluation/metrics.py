"""
Quantitative Registration Evaluation and Scientific Metrics for SIH26166.
Computes RMSE, MAE, SSIM, PSNR, Mutual Information, NCC, Inlier Ratios,
Spatial Coverage, and Ground-Truth Decomposition Errors.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Tuple
import numpy as np
import cv2

from evaluation.base import RegistrationEvaluatorBase, RegistrationEvaluationMetrics
from prototype.synthetic.ground_truth import GroundTruthTransform, GroundTruthComparisonMetrics


@dataclass
class FullEvaluationReport:
    # Image Similarity Metrics
    rmse: float
    mae: float
    ssim: float
    psnr_db: float
    mutual_information: float
    normalized_cross_correlation: float

    # Keypoint & Geometric Metrics
    initial_keypoints_ref: int
    initial_keypoints_src: int
    candidate_matches: int
    filtered_matches: int
    inliers_count: int
    inlier_ratio: float
    spatial_coverage_percentage: float
    occupied_grid_cells: int
    total_grid_cells: int
    reprojection_rmse_px: float
    geometric_model: str
    estimator: str

    # Subpixel Metrics
    subpixel_mean_displacement_px: float
    subpixel_convergence_rate: float

    # Ground Truth Comparison (if available)
    ground_truth_metrics: Optional[Dict[str, Any]] = None

    # Status
    registration_status: str = "SUCCESS"  # SUCCESS or REGISTRATION_FAILED
    failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RegistrationMetricsCalculator(RegistrationEvaluatorBase):
    """
    Computes rigorous radiometric, information-theoretic, and geometric metrics.
    """

    @staticmethod
    def calculate_ssim(img1: np.ndarray, img2: np.ndarray, k1: float = 0.01, k2: float = 0.03) -> float:
        """Structural Similarity Index (SSIM) between two single-channel images."""
        x = img1.astype(np.float64)
        y = img2.astype(np.float64)

        if x.max() > 1.0:
            x = x / 255.0
        if y.max() > 1.0:
            y = y / 255.0

        c1 = (k1 * 1.0) ** 2
        c2 = (k2 * 1.0) ** 2

        mu_x = cv2.GaussianBlur(x, (11, 11), 1.5)
        mu_y = cv2.GaussianBlur(y, (11, 11), 1.5)

        mu_x_sq = mu_x ** 2
        mu_y_sq = mu_y ** 2
        mu_xy = mu_x * mu_y

        sigma_x_sq = cv2.GaussianBlur(x ** 2, (11, 11), 1.5) - mu_x_sq
        sigma_y_sq = cv2.GaussianBlur(y ** 2, (11, 11), 1.5) - mu_y_sq
        sigma_xy = cv2.GaussianBlur(x * y, (11, 11), 1.5) - mu_xy

        numerator = (2.0 * mu_xy + c1) * (2.0 * sigma_xy + c2)
        denominator = (mu_x_sq + mu_y_sq + c1) * (sigma_x_sq + sigma_y_sq + c2)
        ssim_map = numerator / (denominator + 1e-12)

        return float(np.clip(np.mean(ssim_map), -1.0, 1.0))

    @staticmethod
    def calculate_psnr(img1: np.ndarray, img2: np.ndarray, max_val: float = 1.0) -> float:
        """Peak Signal-to-Noise Ratio (PSNR in dB)."""
        x = img1.astype(np.float64)
        y = img2.astype(np.float64)
        if x.max() > 1.0 or y.max() > 1.0:
            max_val = 255.0

        mse = np.mean((x - y) ** 2)
        if mse < 1e-12:
            return 100.0  # Identical images
        return float(10.0 * np.log10((max_val ** 2) / mse))

    @staticmethod
    def calculate_mutual_information(img1: np.ndarray, img2: np.ndarray, bins: int = 64) -> float:
        """Information-theoretic Mutual Information I(X; Y) = H(X) + H(Y) - H(X, Y)."""
        x = img1.ravel()
        y = img2.ravel()

        hist_2d, _, _ = np.histogram2d(x, y, bins=bins)
        # Joint probability
        p_xy = hist_2d / float(np.sum(hist_2d) + 1e-12)

        # Marginal probabilities
        p_x = np.sum(p_xy, axis=1)
        p_y = np.sum(p_xy, axis=0)

        # Entropies
        nz_xy = p_xy > 0
        nz_x = p_x > 0
        nz_y = p_y > 0

        h_xy = -np.sum(p_xy[nz_xy] * np.log2(p_xy[nz_xy]))
        h_x = -np.sum(p_x[nz_x] * np.log2(p_x[nz_x]))
        h_y = -np.sum(p_y[nz_y] * np.log2(p_y[nz_y]))

        mi = h_x + h_y - h_xy
        return float(max(0.0, mi))

    @staticmethod
    def calculate_ncc(img1: np.ndarray, img2: np.ndarray) -> float:
        """Normalized Cross-Correlation (Pearson correlation coefficient)."""
        x = img1.astype(np.float64).ravel()
        y = img2.astype(np.float64).ravel()

        std_x = np.std(x)
        std_y = np.std(y)

        if std_x < 1e-6 or std_y < 1e-6:
            return 0.0

        x_norm = (x - np.mean(x)) / std_x
        y_norm = (y - np.mean(y)) / std_y
        ncc = np.mean(x_norm * y_norm)
        return float(np.clip(ncc, -1.0, 1.0))

    def evaluate(
        self,
        registered_image: np.ndarray,
        reference_image: np.ndarray,
        ground_truth_homography: Optional[np.ndarray] = None
    ) -> RegistrationEvaluationMetrics:
        """
        Evaluate standard metrics implementing base RegistrationEvaluatorBase interface.
        """
        ref_f = reference_image.astype(np.float32)
        if ref_f.max() > 1.0:
            ref_f = ref_f / 255.0
        reg_f = registered_image.astype(np.float32)
        if reg_f.max() > 1.0:
            reg_f = reg_f / 255.0

        diff = ref_f - reg_f
        rmse = float(np.sqrt(np.mean(diff ** 2)))
        mae = float(np.mean(np.abs(diff)))
        ssim_val = self.calculate_ssim(ref_f, reg_f)
        psnr_val = self.calculate_psnr(ref_f, reg_f, max_val=1.0)
        mi_val = self.calculate_mutual_information(ref_f, reg_f)
        ncc_val = self.calculate_ncc(ref_f, reg_f)

        return RegistrationEvaluationMetrics(
            rmse_pixels=rmse,
            mae_pixels=mae,
            ssim=ssim_val,
            psnr_db=psnr_val,
            mutual_information=mi_val,
            normalized_cross_correlation=ncc_val,
            reprojection_error_m=None,
            notes="Evaluated via RegistrationMetricsCalculator"
        )

"""
Registration Evaluation and Scientific Metric Benchmark Interface.
[Placeholder for Phase 15: Evaluation & Accuracy Benchmarks]
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import numpy as np


@dataclass
class RegistrationEvaluationMetrics:
    rmse_pixels: float
    mae_pixels: float
    ssim: float
    psnr_db: float
    mutual_information: float
    normalized_cross_correlation: float
    reprojection_error_m: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RegistrationEvaluatorBase(ABC):
    """
    Abstract interface for evaluating quantitative registration accuracy.
    """

    @abstractmethod
    def evaluate(
        self,
        registered_image: np.ndarray,
        reference_image: np.ndarray,
        ground_truth_homography: Optional[np.ndarray] = None
    ) -> RegistrationEvaluationMetrics:
        """Compute RMSE, MAE, SSIM, PSNR, and Mutual Information between registered and reference rasters."""
        pass

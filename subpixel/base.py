"""
Sub-pixel Refinement Interface.
[Placeholder for Phase 13: Sub-pixel Correspondence Optimization]
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass
class SubpixelRefinementResult:
    refined_src_points: np.ndarray
    refined_ref_points: np.ndarray
    displacement_norm_mean: float = 0.0
    convergence_rate: float = 1.0


class SubpixelRefinerBase(ABC):
    """
    Abstract interface for sub-pixel accuracy optimization (Lucas-Kanade, Taylor series, correlation peak fitting).
    """

    @abstractmethod
    def refine(
        self,
        src_image: np.ndarray,
        ref_image: np.ndarray,
        src_points: np.ndarray,
        ref_points: np.ndarray,
        patch_size: int = 15
    ) -> SubpixelRefinementResult:
        """Refine keypoint coordinates to sub-pixel precision."""
        pass

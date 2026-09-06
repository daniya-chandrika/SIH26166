"""
Image Registration and Warping Interface.
[Placeholder for Phase 14: Final Resampling & Registration]
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

from geometry.base import TransformationResult


@dataclass
class RegistrationOutput:
    registered_image: np.ndarray
    difference_map: Optional[np.ndarray] = None
    output_path: Optional[str] = None
    transformation: Optional[TransformationResult] = None
    resampling_method: str = "BILINEAR"


class ImageRegistrarBase(ABC):
    """
    Abstract interface for warping and registering orbital rasters into reference geometry.
    """

    @abstractmethod
    def register(
        self,
        source_image: np.ndarray,
        reference_image: np.ndarray,
        transformation: TransformationResult,
        resampling_method: str = "BILINEAR"
    ) -> RegistrationOutput:
        """Apply geometric transformation and resample source image to align with reference grid."""
        pass

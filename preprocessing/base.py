"""
Radiometric and Geometric Preprocessing Interface.
[Placeholder for Phase 9: Preprocessing & Multiscale Representation]
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
import numpy as np

from metadata.models import LunarProductMetadata


class RadiometricPreprocessorBase(ABC):
    """
    Abstract interface for radiometric calibration, dynamic range normalization,
    and photometric correction (e.g. Lommel-Seeliger / Minnaert).
    """

    @abstractmethod
    def calibrate_and_normalize(
        self,
        raster_data: np.ndarray,
        metadata: LunarProductMetadata
    ) -> np.ndarray:
        """Calibrate raw digital numbers to Top-Of-Atmosphere / surface reflectance and normalize."""
        pass

    @abstractmethod
    def apply_photometric_correction(
        self,
        raster_data: np.ndarray,
        incidence_angle: float,
        emission_angle: float,
        phase_angle: float
    ) -> np.ndarray:
        """Apply lunar photometric illumination correction."""
        pass


class GeometricResamplerBase(ABC):
    """
    Abstract interface for ground sampling distance (GSD) matching and multi-scale pyramid generation.
    """

    @abstractmethod
    def resample_to_resolution(
        self,
        raster_data: np.ndarray,
        current_resolution: float,
        target_resolution: float
    ) -> np.ndarray:
        """Resample raster array to target GSD resolution in meters/pixel."""
        pass

    @abstractmethod
    def build_multiscale_pyramid(
        self,
        raster_data: np.ndarray,
        levels: int = 3
    ) -> List[np.ndarray]:
        """Generate multi-scale image pyramid for coarse-to-fine registration."""
        pass

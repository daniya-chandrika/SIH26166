"""
Feature Extraction and Keypoint Detection Interface.
[Placeholder for Phase 10: Deep and Classical Feature Detection]
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class KeypointsData:
    keypoints: np.ndarray          # Shape (N, 2) in (x, y) pixel coordinates
    descriptors: Optional[np.ndarray] = None  # Shape (N, D) feature embeddings
    scores: Optional[np.ndarray] = None       # Shape (N,) detection confidence
    image_shape: tuple = (0, 0)


class FeatureExtractorBase(ABC):
    """
    Abstract interface for feature extractors (SuperPoint, SIFT, ORB, LoFTR backbone).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the feature extractor method."""
        pass

    @abstractmethod
    def extract_features(
        self,
        image_array: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> KeypointsData:
        """Extract keypoints, scores, and visual descriptors from a normalized 2D image."""
        pass

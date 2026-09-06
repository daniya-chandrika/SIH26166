"""
Feature Matching and Correspondence Interface.
[Placeholder for Phase 11: Correspondence Detection & Confidence Filtering]
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import numpy as np

from features.base import KeypointsData


@dataclass
class MatchResult:
    source_points: np.ndarray       # Shape (M, 2)
    reference_points: np.ndarray    # Shape (M, 2)
    confidence: np.ndarray          # Shape (M,)
    raw_match_count: int = 0
    filtered_match_count: int = 0
    inliers_mask: Optional[np.ndarray] = None  # Shape (M,) boolean


class FeatureMatcherBase(ABC):
    """
    Abstract interface for feature matchers (LightGlue, LoFTR matcher, Mutual Nearest Neighbors).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the matcher algorithm."""
        pass

    @abstractmethod
    def match(
        self,
        features_src: KeypointsData,
        features_ref: KeypointsData,
        min_confidence: float = 0.2
    ) -> MatchResult:
        """Find correspondences between two sets of extracted keypoint representations."""
        pass

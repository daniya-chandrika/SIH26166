"""
LightGlue Neural Correspondence Matcher Adapter Interface for SIH26166.
"""
from typing import Optional
import numpy as np

from features.base import KeypointsData
from matching.base import FeatureMatcherBase, MatchResult


class LightGlueAdapter(FeatureMatcherBase):
    """
    Adapter for future LightGlue transformer matcher.
    """

    def __init__(self, weights_path: Optional[str] = None):
        self.weights_path = weights_path

    @property
    def name(self) -> str:
        return "LightGlue_Learned"

    def is_available(self) -> bool:
        try:
            import torch
            return self.weights_path is not None
        except ImportError:
            return False

    def match(
        self,
        features_src: KeypointsData,
        features_ref: KeypointsData,
        min_confidence: float = 0.2
    ) -> MatchResult:
        if not self.is_available():
            raise NotImplementedError(
                "LightGlue backend is not loaded. "
                "Use DescriptorMatcher (BFMatcher) for offline prototype execution."
            )
        return MatchResult(
            source_points=np.empty((0, 2), dtype=np.float32),
            reference_points=np.empty((0, 2), dtype=np.float32),
            confidence=np.empty((0,), dtype=np.float32)
        )

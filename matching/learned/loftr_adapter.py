"""
LoFTR (Detector-Free Local Feature Matching with Transformers) Adapter Interface for SIH26166.
"""
from typing import Optional
import numpy as np

from matching.base import MatchResult


class LoFTRAdapter:
    """
    Adapter for future detector-free LoFTR deep correspondence transformer.
    """

    def __init__(self, weights_path: Optional[str] = None):
        self.weights_path = weights_path

    @property
    def name(self) -> str:
        return "LoFTR_Learned"

    def is_available(self) -> bool:
        try:
            import torch
            return self.weights_path is not None
        except ImportError:
            return False

    def match_dense(
        self,
        image_src: np.ndarray,
        image_ref: np.ndarray,
        min_confidence: float = 0.2
    ) -> MatchResult:
        if not self.is_available():
            raise NotImplementedError(
                "LoFTR backend is not loaded. "
                "Use SIFT + DescriptorMatcher for offline prototype execution."
            )
        return MatchResult(
            source_points=np.empty((0, 2), dtype=np.float32),
            reference_points=np.empty((0, 2), dtype=np.float32),
            confidence=np.empty((0,), dtype=np.float32)
        )

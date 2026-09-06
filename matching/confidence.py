"""
Confidence Calculation and Quality Filtering for SIH26166.
Computes deterministic, physically-grounded confidence scores for descriptor matches.
"""
from typing import Tuple
import numpy as np


class ConfidenceFilter:
    """
    Evaluates correspondence confidence using Lowe's ratio margin and descriptor distances.
    Outputs normalized confidence in [0.0, 1.0].
    """

    @staticmethod
    def calculate_confidence(
        best_distance: float,
        second_best_distance: float,
        is_binary: bool = False
    ) -> float:
        """
        Calculate confidence score from nearest neighbor distances.
        c = (1.0 - d1 / d2) * exp(-d1 / scale)
        """
        if second_best_distance <= 1e-6:
            return 0.0

        ratio = best_distance / second_best_distance
        ratio_margin = max(0.0, 1.0 - ratio)

        # Scale factor depending on descriptor metric
        if is_binary:
            # Hamming distance (typically 0 - 256)
            scale = 64.0
        else:
            # L2 distance (typically 0 - 512 for SIFT)
            scale = 200.0

        dist_decay = np.exp(-best_distance / scale)
        confidence = float(np.clip(ratio_margin * (0.3 + 0.7 * dist_decay), 0.0, 1.0))
        return confidence

    @classmethod
    def filter_by_confidence(
        cls,
        src_points: np.ndarray,
        ref_points: np.ndarray,
        confidence_scores: np.ndarray,
        min_confidence: float = 0.15
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Filter point arrays retaining only correspondences above min_confidence."""
        if len(confidence_scores) == 0:
            return (
                np.empty((0, 2), dtype=np.float32),
                np.empty((0, 2), dtype=np.float32),
                np.empty((0,), dtype=np.float32)
            )

        valid_mask = confidence_scores >= min_confidence
        return (
            src_points[valid_mask],
            ref_points[valid_mask],
            confidence_scores[valid_mask]
        )

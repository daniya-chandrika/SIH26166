"""
SuperPoint Neural Feature Detector Adapter Interface for SIH26166.
"""
from typing import Optional, Dict, Any
import numpy as np

from features.base import FeatureExtractorBase, KeypointsData


class SuperPointAdapter(FeatureExtractorBase):
    """
    Adapter for future SuperPoint deep feature detector and descriptor model.
    Enables zero-code pipeline migration once pre-trained lunar weights are added.
    """

    def __init__(self, weights_path: Optional[str] = None, max_keypoints: int = 2048):
        self.weights_path = weights_path
        self.max_keypoints = max_keypoints
        self._model = None

    @property
    def name(self) -> str:
        return "SuperPoint_Learned"

    def is_available(self) -> bool:
        """Check if torch and model weights are installed and available."""
        try:
            import torch
            return self.weights_path is not None
        except ImportError:
            return False

    def extract_features(
        self,
        image_array: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> KeypointsData:
        if not self.is_available():
            raise NotImplementedError(
                "SuperPoint deep learning backend is not loaded. "
                "Use SIFTFeatureDetector or ORBFeatureDetector for offline prototype execution."
            )
        # Deep inference placeholder
        return KeypointsData(
            keypoints=np.empty((0, 2), dtype=np.float32),
            descriptors=np.empty((0, 256), dtype=np.float32),
            scores=np.empty((0,), dtype=np.float32),
            image_shape=image_array.shape[:2]
        )

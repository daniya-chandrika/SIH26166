"""
DISK (Learning local features with Reinforcement Learning) Adapter Interface for SIH26166.
"""
from typing import Optional
import numpy as np

from features.base import FeatureExtractorBase, KeypointsData
from core.exceptions import ModelUnavailableError


class DISKAdapter(FeatureExtractorBase):
    """
    Adapter for DISK deep local feature detector and descriptor model.
    """

    def __init__(self, weights_path: Optional[str] = None, max_keypoints: int = 2048):
        self.weights_path = weights_path
        self.max_keypoints = max_keypoints

    @property
    def name(self) -> str:
        return "DISK_Learned"

    def is_available(self) -> bool:
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
            raise ModelUnavailableError(
                model_name="DISK",
                missing_dependency="PyTorch or pre-trained DISK weights not found in environment."
            )
        return KeypointsData(
            keypoints=np.empty((0, 2), dtype=np.float32),
            descriptors=np.empty((0, 128), dtype=np.float32),
            scores=np.empty((0,), dtype=np.float32),
            image_shape=image_array.shape[:2]
        )

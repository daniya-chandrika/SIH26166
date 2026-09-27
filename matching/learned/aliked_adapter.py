"""
ALIKED (A Lighter Keypoint and Descriptor Extraction Network) Adapter Interface for SIH26166.
"""
from typing import Optional
import numpy as np

from features.base import FeatureExtractorBase, KeypointsData
from core.exceptions import ModelUnavailableError


class ALIKEDAdapter(FeatureExtractorBase):
    """
    Adapter for ALIKED deformable keypoint extraction model.
    """

    def __init__(self, model_name: str = "aliked-n16", weights_path: Optional[str] = None):
        self.model_name = model_name
        self.weights_path = weights_path

    @property
    def name(self) -> str:
        return f"ALIKED_{self.model_name}"

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
                model_name="ALIKED",
                missing_dependency="PyTorch or pre-trained ALIKED weights not found in environment."
            )
        return KeypointsData(
            keypoints=np.empty((0, 2), dtype=np.float32),
            descriptors=np.empty((0, 128), dtype=np.float32),
            scores=np.empty((0,), dtype=np.float32),
            image_shape=image_array.shape[:2]
        )

"""
Feature Extraction and Keypoint Detection Implementations for SIH26166.
Provides SIFT, ORB, and Learned Model adapters with explicit availability verification.
"""
from typing import Optional, Dict, Any
import numpy as np
import cv2

from features.base import FeatureExtractorBase, KeypointsData
from core.exceptions import ModelUnavailableError


class SIFTFeatureDetector(FeatureExtractorBase):
    """
    Scale-Invariant Feature Transform (SIFT) detector and descriptor extractor.
    Ideal for lunar terrain with scale, rotation, and illumination variations.
    """

    def __init__(
        self,
        nfeatures: int = 2000,
        n_octave_layers: int = 3,
        contrast_threshold: float = 0.03,
        edge_threshold: float = 10.0,
        sigma: float = 1.6
    ):
        self._nfeatures = nfeatures
        self._n_octave_layers = n_octave_layers
        self._contrast_threshold = contrast_threshold
        self._edge_threshold = edge_threshold
        self._sigma = sigma
        self._sift = cv2.SIFT_create(
            nfeatures=nfeatures,
            nOctaveLayers=n_octave_layers,
            contrastThreshold=contrast_threshold,
            edgeThreshold=edge_threshold,
            sigma=sigma
        )

    @property
    def name(self) -> str:
        return "SIFT"

    def extract_features(
        self,
        image_array: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> KeypointsData:
        # Ensure uint8 for OpenCV feature detectors
        if image_array.dtype != np.uint8:
            if image_array.max() <= 1.0:
                img_uint8 = np.clip(image_array * 255.0, 0, 255).astype(np.uint8)
            else:
                img_uint8 = np.clip(image_array, 0, 255).astype(np.uint8)
        else:
            img_uint8 = image_array

        h, w = img_uint8.shape[:2]
        keypoints, descriptors = self._sift.detectAndCompute(img_uint8, mask=mask)

        if not keypoints or descriptors is None or len(keypoints) == 0:
            return KeypointsData(
                keypoints=np.empty((0, 2), dtype=np.float32),
                descriptors=np.empty((0, 128), dtype=np.float32),
                scores=np.empty((0,), dtype=np.float32),
                image_shape=(h, w)
            )

        # Extract (x, y) coordinates and response scores
        kpts_xy = np.array([kp.pt for kp in keypoints], dtype=np.float32)
        scores = np.array([kp.response for kp in keypoints], dtype=np.float32)

        return KeypointsData(
            keypoints=kpts_xy,
            descriptors=descriptors.astype(np.float32),
            scores=scores,
            image_shape=(h, w)
        )


class ORBFeatureDetector(FeatureExtractorBase):
    """
    Oriented FAST and Rotated BRIEF (ORB) detector and binary descriptor.
    Lightweight, fast feature extractor for resource-constrained execution.
    """

    def __init__(self, nfeatures: int = 2000, fast_threshold: int = 20):
        self._nfeatures = nfeatures
        self._orb = cv2.ORB_create(
            nfeatures=nfeatures,
            fastThreshold=fast_threshold,
            scoreType=cv2.ORB_HARRIS_SCORE
        )

    @property
    def name(self) -> str:
        return "ORB"

    def extract_features(
        self,
        image_array: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> KeypointsData:
        if image_array.dtype != np.uint8:
            if image_array.max() <= 1.0:
                img_uint8 = np.clip(image_array * 255.0, 0, 255).astype(np.uint8)
            else:
                img_uint8 = np.clip(image_array, 0, 255).astype(np.uint8)
        else:
            img_uint8 = image_array

        h, w = img_uint8.shape[:2]
        keypoints, descriptors = self._orb.detectAndCompute(img_uint8, mask=mask)

        if not keypoints or descriptors is None or len(keypoints) == 0:
            return KeypointsData(
                keypoints=np.empty((0, 2), dtype=np.float32),
                descriptors=np.empty((0, 32), dtype=np.uint8),
                scores=np.empty((0,), dtype=np.float32),
                image_shape=(h, w)
            )

        kpts_xy = np.array([kp.pt for kp in keypoints], dtype=np.float32)
        scores = np.array([kp.response for kp in keypoints], dtype=np.float32)

        return KeypointsData(
            keypoints=kpts_xy,
            descriptors=descriptors,
            scores=scores,
            image_shape=(h, w)
        )


class AutoFeatureDetector(FeatureExtractorBase):
    """
    Automatic detector selecting requested detector with explicit error handling.
    """

    def __init__(self, preferred: str = "SIFT", nfeatures: int = 2000):
        self._preferred = preferred.upper()
        if self._preferred == "SIFT":
            self._detector = SIFTFeatureDetector(nfeatures=nfeatures)
        elif self._preferred == "ORB":
            self._detector = ORBFeatureDetector(nfeatures=nfeatures)
        elif self._preferred in ["SUPERPOINT", "SUPERPOINT_LEARNED"]:
            from matching.learned.superpoint_adapter import SuperPointAdapter
            sp = SuperPointAdapter()
            if not sp.is_available():
                raise ModelUnavailableError(
                    model_name="SuperPoint",
                    missing_dependency="PyTorch or pre-trained SuperPoint weights not installed."
                )
            self._detector = sp
        else:
            self._detector = SIFTFeatureDetector(nfeatures=nfeatures)

    @property
    def name(self) -> str:
        return self._detector.name

    def extract_features(
        self,
        image_array: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> KeypointsData:
        return self._detector.extract_features(image_array, mask=mask)


class FeatureDetectorFactory:
    """Factory to instantiate requested detector without silent fallbacks."""

    @staticmethod
    def create(detector_name: str = "SIFT", nfeatures: int = 2000) -> FeatureExtractorBase:
        name = detector_name.upper()
        if name == "SIFT":
            return SIFTFeatureDetector(nfeatures=nfeatures)
        elif name == "ORB":
            return ORBFeatureDetector(nfeatures=nfeatures)
        elif name in ["SUPERPOINT", "SUPERPOINT_LEARNED"]:
            from matching.learned.superpoint_adapter import SuperPointAdapter
            sp = SuperPointAdapter()
            if not sp.is_available():
                raise ModelUnavailableError(
                    model_name="SuperPoint",
                    missing_dependency="PyTorch or pre-trained SuperPoint weights (.pth) not found."
                )
            return sp
        else:
            raise ValueError(f"Unknown feature detector '{detector_name}'. Supported: SIFT, ORB, SuperPoint")

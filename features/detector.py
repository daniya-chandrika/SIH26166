"""
Feature Extraction and Keypoint Detection Implementations for SIH26166.
Provides robust SIFT and ORB feature extractors with automatic fallback.
"""
from typing import Optional
import numpy as np
import cv2

from features.base import FeatureExtractorBase, KeypointsData


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
    Lightweight, fast fallback when floating-point descriptors are not required.
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
    Automatic detector selecting SIFT with graceful fallback to ORB.
    """

    def __init__(self, preferred: str = "SIFT", nfeatures: int = 2000):
        self._preferred = preferred.upper()
        self._detector: FeatureExtractorBase

        if self._preferred == "SIFT":
            try:
                self._detector = SIFTFeatureDetector(nfeatures=nfeatures)
            except Exception:
                self._detector = ORBFeatureDetector(nfeatures=nfeatures)
        elif self._preferred == "ORB":
            self._detector = ORBFeatureDetector(nfeatures=nfeatures)
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

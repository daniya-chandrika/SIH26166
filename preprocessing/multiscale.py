"""
Multi-scale Representation and GSD Resampling for SIH26166.
Generates Gaussian pyramids and handles spatial resolution harmonization between sensors.
"""
from typing import List, Tuple, Optional
import numpy as np
import cv2


class MultiscaleRepresentation:
    """
    Builds multi-resolution image pyramids for coarse-to-fine registration.
    """

    @staticmethod
    def build_gaussian_pyramid(image: np.ndarray, levels: int = 3) -> List[np.ndarray]:
        """
        Construct Gaussian image pyramid.
        Level 0: original image (highest resolution)
        Level 1: 1/2 resolution
        Level 2: 1/4 resolution, etc.
        """
        pyramid = [image]
        current = image
        for i in range(1, levels):
            # Downsample by 2
            downsampled = cv2.pyrDown(current)
            pyramid.append(downsampled)
            current = downsampled
        return pyramid

    @staticmethod
    def resample_to_gsd(
        image: np.ndarray,
        source_gsd_m: float,
        target_gsd_m: float,
        interpolation: int = cv2.INTER_CUBIC
    ) -> Tuple[np.ndarray, float]:
        """
        Resample image array from source GSD to target GSD.
        Returns resampled array and effective scale factor.
        """
        if abs(source_gsd_m - target_gsd_m) < 1e-4:
            return image, 1.0

        # Scale factor = source_gsd / target_gsd
        # If source is 0.25m (OHRC) and target is 0.50m (LROC), scale is 0.5 (image shrinks in pixels)
        scale_factor = source_gsd_m / target_gsd_m
        h, w = image.shape[:2]
        new_w = max(1, int(round(w * scale_factor)))
        new_h = max(1, int(round(h * scale_factor)))

        resampled = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
        return resampled, scale_factor

    @staticmethod
    def resize_to_dimensions(
        image: np.ndarray,
        target_width: int,
        target_height: int,
        interpolation: int = cv2.INTER_LINEAR
    ) -> np.ndarray:
        """Resize image to specific pixel dimensions."""
        return cv2.resize(image, (target_width, target_height), interpolation=interpolation)

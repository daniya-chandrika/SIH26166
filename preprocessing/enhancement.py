"""
Local Contrast and Feature Enhancement for SIH26166.
Implements CLAHE, Unsharp Masking, and Edge-preserving filtering for lunar terrain.
"""
from typing import Optional
import numpy as np
import cv2


class ContrastEnhancer:
    """
    Enhances geomorphological contrast across shadowed lunar terrain and crater rims.
    """

    @staticmethod
    def apply_clahe(
        image_uint8: np.ndarray,
        clip_limit: float = 2.5,
        tile_grid_size: tuple = (8, 8)
    ) -> np.ndarray:
        """
        Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).
        Prevents noise over-amplification in uniform regolith plains while enhancing crater details.
        """
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(image_uint8)

    @staticmethod
    def apply_unsharp_mask(
        image: np.ndarray,
        sigma: float = 1.0,
        strength: float = 0.5
    ) -> np.ndarray:
        """
        Apply unsharp masking to enhance high-frequency crater rims and ejecta boundaries.
        """
        is_uint8 = image.dtype == np.uint8
        img_float = image.astype(np.float32)

        # Gaussian blur
        blurred = cv2.GaussianBlur(img_float, (0, 0), sigma)
        # High-frequency detail
        high_freq = img_float - blurred
        enhanced = img_float + strength * high_freq

        if is_uint8:
            return np.clip(enhanced, 0, 255).astype(np.uint8)
        else:
            return np.clip(enhanced, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def apply_bilateral_filter(
        image_uint8: np.ndarray,
        d: int = 5,
        sigma_color: float = 50.0,
        sigma_space: float = 50.0
    ) -> np.ndarray:
        """Edge-preserving smoothing to reduce sensor noise while preserving sharp crater boundaries."""
        return cv2.bilateralFilter(image_uint8, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)

"""
Radiometric and Dynamic Range Normalization for SIH26166.
Provides robust percentile-based scaling, nodata handling, and radiometric cleaning.
"""
from typing import Tuple, Optional
import numpy as np


class IntensityNormalizer:
    """
    Normalizes multi-sensor / synthetic lunar raster intensities to stable, calibrated dynamic ranges.
    """

    @staticmethod
    def ensure_grayscale_2d(image: np.ndarray) -> np.ndarray:
        """Convert multi-band or 3D arrays to 2D single-band float32 array."""
        if image.ndim == 2:
            return image.astype(np.float32)
        elif image.ndim == 3:
            # If 3-channel RGB
            if image.shape[2] == 3:
                # Standard luminance formula
                return (0.2989 * image[:, :, 0] + 0.5870 * image[:, :, 1] + 0.1140 * image[:, :, 2]).astype(np.float32)
            elif image.shape[2] == 1:
                return image[:, :, 0].astype(np.float32)
            else:
                # Hyperspectral / multi-band: use mean across bands or band 0
                return np.mean(image, axis=2).astype(np.float32)
        elif image.ndim == 1:
            raise ValueError(f"Expected 2D image array, received 1D array of shape {image.shape}")
        else:
            return image.reshape((image.shape[0], image.shape[1])).astype(np.float32)

    @staticmethod
    def handle_invalid_values(
        image: np.ndarray,
        nodata_value: Optional[float] = None,
        replacement_strategy: str = "median"
    ) -> np.ndarray:
        """Replace NaN, Inf, and specified nodata pixels with valid local statistics."""
        cleaned = np.copy(image).astype(np.float32)
        invalid_mask = np.isnan(cleaned) | np.isinf(cleaned)

        if nodata_value is not None:
            invalid_mask |= np.isclose(cleaned, nodata_value)

        if np.any(invalid_mask):
            valid_vals = cleaned[~invalid_mask]
            if len(valid_vals) == 0:
                return np.zeros_like(cleaned, dtype=np.float32)

            fill_val = np.median(valid_vals) if replacement_strategy == "median" else np.mean(valid_vals)
            cleaned[invalid_mask] = fill_val

        return cleaned

    @classmethod
    def robust_percentile_normalize(
        cls,
        image: np.ndarray,
        lower_percentile: float = 1.0,
        upper_percentile: float = 99.0,
        nodata_value: Optional[float] = None
    ) -> np.ndarray:
        """
        Normalize raster using lower/upper percentiles to suppress shadows and specular glints.
        Outputs float32 array in [0.0, 1.0].
        """
        img_2d = cls.ensure_grayscale_2d(image)
        cleaned = cls.handle_invalid_values(img_2d, nodata_value=nodata_value)

        p_low = np.percentile(cleaned, lower_percentile)
        p_high = np.percentile(cleaned, upper_percentile)

        if p_high - p_low < 1e-6:
            # Constant or zero-variance image
            return np.zeros_like(cleaned, dtype=np.float32)

        clipped = np.clip(cleaned, p_low, p_high)
        normalized = (clipped - p_low) / (p_high - p_low)
        return normalized.astype(np.float32)

    @classmethod
    def to_uint8(cls, normalized_float_img: np.ndarray) -> np.ndarray:
        """Convert [0.0, 1.0] float32 image to uint8 [0, 255]."""
        return np.clip(normalized_float_img * 255.0, 0, 255).astype(np.uint8)

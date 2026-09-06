"""
Registration Pipeline and Fusion Visualization for SIH26166.
Applies geometric transformation, resamples rasters, and generates alignment diagnostics.
"""
from typing import Optional, Tuple, Dict, Any
import numpy as np
import cv2

from geometry.base import TransformationResult
from registration.base import ImageRegistrarBase, RegistrationOutput
from registration.warp import ImageWarper


class RegistrationPipeline(ImageRegistrarBase):
    """
    Executes geometric warping and alignment verification.
    """

    def __init__(self, default_resampling: str = "BILINEAR"):
        self.default_resampling = default_resampling

    @staticmethod
    def compute_difference_map(
        ref_image: np.ndarray,
        registered_image: np.ndarray,
        overlap_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute absolute difference map between reference and registered image.
        """
        ref_norm = ref_image.astype(np.float32)
        reg_norm = registered_image.astype(np.float32)

        # Scale to [0, 1] if not already
        if ref_norm.max() > 1.0:
            ref_norm = ref_norm / 255.0
        if reg_norm.max() > 1.0:
            reg_norm = reg_norm / 255.0

        diff = np.abs(ref_norm - reg_norm)
        if overlap_mask is not None:
            diff[~overlap_mask] = 0.0
        return diff

    @staticmethod
    def create_checkerboard_overlay(
        ref_image: np.ndarray,
        registered_image: np.ndarray,
        tile_size: int = 32
    ) -> np.ndarray:
        """
        Generate alternating checkerboard pattern to visually inspect edge and feature continuity.
        """
        h, w = ref_image.shape[:2]
        checkerboard = np.copy(ref_image)

        y_indices, x_indices = np.indices((h, w))
        tile_x = (x_indices // tile_size) % 2
        tile_y = (y_indices // tile_size) % 2
        pattern = (tile_x ^ tile_y) == 1

        checkerboard[pattern] = registered_image[pattern]
        return checkerboard

    @staticmethod
    def create_false_color_blend(
        ref_image: np.ndarray,
        registered_image: np.ndarray
    ) -> np.ndarray:
        """
        Create false-color RGB overlay:
        - Green Channel: Reference image
        - Red + Blue (Magenta) Channels: Registered image
        Perfect alignment appears in neutral grayscale; spatial shifts appear as chromatic fringes.
        """
        ref_f = ref_image.astype(np.float32)
        if ref_f.max() > 1.0:
            ref_f = ref_f / 255.0
        reg_f = registered_image.astype(np.float32)
        if reg_f.max() > 1.0:
            reg_f = reg_f / 255.0

        h, w = ref_image.shape[:2]
        blend = np.zeros((h, w, 3), dtype=np.float32)
        blend[:, :, 0] = reg_f  # Blue: Registered
        blend[:, :, 1] = ref_f  # Green: Reference
        blend[:, :, 2] = reg_f  # Red: Registered

        return np.clip(blend, 0.0, 1.0)

    def register(
        self,
        source_image: np.ndarray,
        reference_image: np.ndarray,
        transformation: TransformationResult,
        resampling_method: Optional[str] = None
    ) -> RegistrationOutput:
        if transformation.matrix is None:
            raise ValueError("Cannot perform registration: transformation matrix is None.")

        method = resampling_method or self.default_resampling

        # Warp source image to reference grid
        warped_img, overlap_mask = ImageWarper.warp_source_to_reference(
            source_image=source_image,
            H_matrix=transformation.matrix,
            reference_shape=reference_image.shape[:2],
            resampling_method=method
        )

        # Difference map
        diff_map = self.compute_difference_map(
            ref_image=reference_image,
            registered_image=warped_img,
            overlap_mask=overlap_mask
        )

        return RegistrationOutput(
            registered_image=warped_img,
            difference_map=diff_map,
            output_path=None,
            transformation=transformation,
            resampling_method=method
        )

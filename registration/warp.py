"""
Coordinate Warping and Raster Resampling for SIH26166.
Applies estimated projective/affine transformation matrices to map source images to the reference grid.
"""
from typing import Tuple, Optional
import numpy as np
import cv2


class ImageWarper:
    """
    Warps source raster into reference coordinate space using estimated 3x3 transformation matrix.
    """

    INTERPOLATION_MAP = {
        "BILINEAR": cv2.INTER_LINEAR,
        "BICUBIC": cv2.INTER_CUBIC,
        "NEAREST": cv2.INTER_NEAREST,
        "LANCZOS": cv2.INTER_LANCZOS4,
    }

    @classmethod
    def warp_source_to_reference(
        cls,
        source_image: np.ndarray,
        H_matrix: np.ndarray,
        reference_shape: Tuple[int, int],
        resampling_method: str = "BILINEAR",
        border_mode: int = cv2.BORDER_CONSTANT,
        border_value: float = 0.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Warp source image using estimated H matrix (which maps p_src -> p_ref).
        Returns: (warped_image, valid_overlap_mask)
        """
        ref_h, ref_w = reference_shape[:2]
        interp = cls.INTERPOLATION_MAP.get(resampling_method.upper(), cv2.INTER_LINEAR)

        # Source image dimensions
        src_h, src_w = source_image.shape[:2]

        # In OpenCV warpPerspective:
        # dst(x, y) = src( (M11*x + M12*y + M13)/(M31*x + M32*y + M33), ... )
        # M maps destination coordinates (reference) to source coordinates (source).
        # Since H maps source -> reference (p_ref = H * p_src),
        # the mapping from reference to source is H_inv = inv(H).
        H_inv = np.linalg.inv(H_matrix)

        warped = cv2.warpPerspective(
            source_image.astype(np.float32),
            H_inv,
            (ref_w, ref_h),
            flags=interp,
            borderMode=border_mode,
            borderValue=border_value
        )

        # Create valid overlap mask (source bounding box mapped into reference)
        src_mask = np.ones((src_h, src_w), dtype=np.float32)
        warped_mask = cv2.warpPerspective(
            src_mask,
            H_inv,
            (ref_w, ref_h),
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0.0
        )
        overlap_mask = warped_mask > 0.5

        return warped, overlap_mask

"""
Transformation Engine for SIH26166.
Handles both geometric transformations (homography, affine, perspective, scale, rotation, translation)
and radiometric distortions (illumination angle shifts, gamma variations, noise, blur).
Maintains exact ground truth 3x3 transformation matrices.
"""
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
import numpy as np
import cv2


@dataclass
class GeometricParams:
    rotation_deg: float = 0.0
    scale: float = 1.0
    scale_y: Optional[float] = None
    translation_x: float = 0.0
    translation_y: float = 0.0
    shear_x: float = 0.0
    shear_y: float = 0.0
    perspective_x: float = 0.0
    perspective_y: float = 0.0


@dataclass
class RadiometricParams:
    illumination_gradient_strength: float = 0.0
    illumination_gradient_angle_deg: float = 0.0
    gamma: float = 1.0
    contrast_scale: float = 1.0
    brightness_offset: float = 0.0
    gaussian_noise_std: float = 0.0
    speckle_noise_std: float = 0.0
    blur_kernel_size: int = 0
    blur_sigma: float = 0.0


class TransformationEngine:
    """
    Applies paired geometric and radiometric transformations to reference imagery
    while preserving analytical ground-truth matrices.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()

    def build_ground_truth_matrix(
        self,
        params: GeometricParams,
        center_x: float,
        center_y: float
    ) -> np.ndarray:
        """
        Build 3x3 homography matrix H_gt mapping source image points to reference image points:
            p_ref ~ H_gt * p_src
        Centered at image center (center_x, center_y).
        """
        # 1. Translate center to origin
        T_center = np.array([
            [1.0, 0.0, -center_x],
            [0.0, 1.0, -center_y],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        # 2. Rotation
        rad = np.radians(params.rotation_deg)
        cos_t = np.cos(rad)
        sin_t = np.sin(rad)
        R = np.array([
            [cos_t, -sin_t, 0.0],
            [sin_t,  cos_t, 0.0],
            [0.0,    0.0,   1.0]
        ], dtype=np.float64)

        # 3. Scale
        sx = params.scale
        sy = params.scale_y if params.scale_y is not None else params.scale
        S = np.array([
            [sx,  0.0, 0.0],
            [0.0, sy,  0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        # 4. Shear
        Sh = np.array([
            [1.0, params.shear_x, 0.0],
            [params.shear_y, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        # 5. Perspective / Projective
        P = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [params.perspective_x, params.perspective_y, 1.0]
        ], dtype=np.float64)

        # 6. Translate back and apply final translation
        T_back = np.array([
            [1.0, 0.0, center_x + params.translation_x],
            [0.0, 1.0, center_y + params.translation_y],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        # Combined ground truth matrix: p_ref = T_back * P * Sh * S * R * T_center * p_src
        H_gt = T_back @ P @ Sh @ S @ R @ T_center

        # Normalize matrix so H_33 == 1
        if abs(H_gt[2, 2]) > 1e-12:
            H_gt = H_gt / H_gt[2, 2]

        return H_gt

    def apply_geometry(
        self,
        image: np.ndarray,
        H_gt: np.ndarray,
        output_shape: Optional[Tuple[int, int]] = None
    ) -> np.ndarray:
        """
        Warp reference image to create source image such that p_ref = H_gt * p_src.
        To sample source pixels from reference: p_ref = H_gt * p_src.
        OpenCV warpPerspective(src=image, M=inv(H_gt)) samples reference image into source canvas.
        """
        h, w = image.shape[:2]
        out_w, out_h = output_shape if output_shape is not None else (w, h)

        # Invert H_gt to map source pixel coords to reference image coords
        H_inv = np.linalg.inv(H_gt)

        warped = cv2.warpPerspective(
            image,
            H_inv,
            (out_w, out_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REFLECT_101
        )
        return warped

    def apply_radiometry(
        self,
        image: np.ndarray,
        params: RadiometricParams
    ) -> np.ndarray:
        """
        Apply realistic spaceborne radiometric perturbations:
        illumination gradients, sensor noise, PSF blur, gamma response.
        """
        h, w = image.shape[:2]
        img = image.astype(np.float32)

        # 1. Spatial Illumination Gradient (simulates different solar incidence angle)
        if params.illumination_gradient_strength > 0:
            ang_rad = np.radians(params.illumination_gradient_angle_deg)
            y, x = np.mgrid[:h, :w]
            # Normalized direction vector
            grad = (np.cos(ang_rad) * (x / w - 0.5) + np.sin(ang_rad) * (y / h - 0.5))
            illum_mask = 1.0 + params.illumination_gradient_strength * grad
            img = img * np.clip(illum_mask, 0.1, 2.0)

        # 2. Contrast scaling & brightness offset
        img = img * params.contrast_scale + params.brightness_offset

        # 3. Non-linear Gamma curve
        if abs(params.gamma - 1.0) > 1e-4:
            # Normalize to [0, 1] for gamma, then rescale
            min_val = img.min()
            max_val = max(img.max(), min_val + 1e-6)
            norm = (img - min_val) / (max_val - min_val)
            norm = np.power(np.clip(norm, 0.0, 1.0), params.gamma)
            img = norm * (max_val - min_val) + min_val

        # 4. Blur (PSF / defocus simulation)
        if params.blur_kernel_size > 0 or params.blur_sigma > 0:
            ksize = params.blur_kernel_size if params.blur_kernel_size % 2 == 1 else params.blur_kernel_size + 1
            if ksize <= 1 and params.blur_sigma > 0:
                ksize = int(2 * np.ceil(2 * params.blur_sigma) + 1)
            if ksize >= 3:
                img = cv2.GaussianBlur(img, (ksize, ksize), params.blur_sigma)

        # 5. Gaussian Sensor Noise
        if params.gaussian_noise_std > 0:
            noise = self.rng.normal(0.0, params.gaussian_noise_std, (h, w)).astype(np.float32)
            img = img + noise

        # 6. Multiplicative Speckle / Photon Noise
        if params.speckle_noise_std > 0:
            speckle = self.rng.normal(1.0, params.speckle_noise_std, (h, w)).astype(np.float32)
            img = img * speckle

        # Clip final image to valid range
        if image.dtype == np.uint8:
            return np.clip(img, 0.0, 255.0).astype(np.uint8)
        else:
            return np.clip(img, 0.0, 1.0).astype(np.float32)

    def transform(
        self,
        reference_image: np.ndarray,
        geo_params: GeometricParams,
        radio_params: RadiometricParams
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Execute full transformation pipeline.
        Returns: (source_image, H_gt)
        """
        h, w = reference_image.shape[:2]
        center_x, center_y = w / 2.0, h / 2.0

        # Build ground truth matrix
        H_gt = self.build_ground_truth_matrix(geo_params, center_x, center_y)

        # Warp geometry
        source_geo = self.apply_geometry(reference_image, H_gt)

        # Apply radiometric perturbations
        source_final = self.apply_radiometry(source_geo, radio_params)

        return source_final, H_gt

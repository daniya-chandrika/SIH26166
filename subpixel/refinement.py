"""
Sub-pixel Keypoint Refinement for SIH26166.
Refines correspondence coordinates to sub-pixel accuracy using local Normalized Cross-Correlation (NCC)
and 2D quadratic peak interpolation.
"""
from typing import Tuple, Optional
import numpy as np
import cv2

from subpixel.base import SubpixelRefinerBase, SubpixelRefinementResult


class SubpixelRefiner(SubpixelRefinerBase):
    """
    Refines corresponding point locations using local template cross-correlation
    and sub-pixel parabolic peak interpolation.
    """

    def __init__(
        self,
        patch_size: int = 15,
        search_radius: int = 3,
        min_ncc_peak: float = 0.5
    ):
        self.patch_size = patch_size if patch_size % 2 == 1 else patch_size + 1
        self.search_radius = search_radius
        self.min_ncc_peak = min_ncc_peak

    @staticmethod
    def _parabolic_peak_offset(c_prev: float, c_center: float, c_next: float) -> float:
        """Fit 1D parabola to 3 points and find continuous extremum offset in [-0.5, 0.5]."""
        denom = 2.0 * (2.0 * c_center - c_prev - c_next)
        if abs(denom) < 1e-6:
            return 0.0
        delta = (c_next - c_prev) / denom
        return float(np.clip(delta, -0.5, 0.5))

    def refine_single_point(
        self,
        src_img: np.ndarray,
        ref_img: np.ndarray,
        src_pt: np.ndarray,
        ref_pt: np.ndarray
    ) -> Tuple[np.ndarray, float, bool]:
        """
        Refine a single point pair.
        Returns: (refined_ref_pt, displacement_norm, success_bool)
        """
        half_p = self.patch_size // 2
        sx, sy = float(src_pt[0]), float(src_pt[1])
        rx, ry = float(ref_pt[0]), float(ref_pt[1])

        h_src, w_src = src_img.shape[:2]
        h_ref, w_ref = ref_img.shape[:2]

        # Check bounds for template extraction
        sx_int, sy_int = int(round(sx)), int(round(sy))
        if (
            sx_int - half_p < 0 or sx_int + half_p >= w_src or
            sy_int - half_p < 0 or sy_int + half_p >= h_src
        ):
            return ref_pt.copy(), 0.0, False

        template = src_img[sy_int - half_p:sy_int + half_p + 1, sx_int - half_p:sx_int + half_p + 1]

        # Check bounds for search window
        rx_int, ry_int = int(round(rx)), int(round(ry))
        win_rad = half_p + self.search_radius
        if (
            rx_int - win_rad < 0 or rx_int + win_rad >= w_ref or
            ry_int - win_rad < 0 or ry_int + win_rad >= h_ref
        ):
            return ref_pt.copy(), 0.0, False

        search_win = ref_img[ry_int - win_rad:ry_int + win_rad + 1, rx_int - win_rad:rx_int + win_rad + 1]

        # Compute Normalized Cross-Correlation
        try:
            ncc_map = cv2.matchTemplate(search_win, template, cv2.TM_CCOEFF_NORMED)
        except Exception:
            return ref_pt.copy(), 0.0, False

        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(ncc_map)
        if max_val < self.min_ncc_peak:
            return ref_pt.copy(), 0.0, False

        u_peak, v_peak = max_loc
        map_h, map_w = ncc_map.shape

        # Sub-pixel parabolic interpolation around peak
        du, dv = 0.0, 0.0
        if 0 < u_peak < map_w - 1:
            du = self._parabolic_peak_offset(
                ncc_map[v_peak, u_peak - 1],
                ncc_map[v_peak, u_peak],
                ncc_map[v_peak, u_peak + 1]
            )
        if 0 < v_peak < map_h - 1:
            dv = self._parabolic_peak_offset(
                ncc_map[v_peak - 1, u_peak],
                ncc_map[v_peak, u_peak],
                ncc_map[v_peak + 1, u_peak]
            )

        # Map peak back to reference coordinates
        # Top-left of search window in ref_img is (rx_int - win_rad, ry_int - win_rad)
        refined_rx = (rx_int - win_rad) + half_p + u_peak + du
        refined_ry = (ry_int - win_rad) + half_p + v_peak + dv

        disp = float(np.sqrt((refined_rx - rx) ** 2 + (refined_ry - ry) ** 2))

        # Reject wild jumps greater than search radius + 1
        if disp > (self.search_radius + 1.5):
            return ref_pt.copy(), 0.0, False

        return np.array([refined_rx, refined_ry], dtype=np.float32), disp, True

    def refine(
        self,
        src_image: np.ndarray,
        ref_image: np.ndarray,
        src_points: np.ndarray,
        ref_points: np.ndarray,
        patch_size: Optional[int] = None
    ) -> SubpixelRefinementResult:
        if patch_size is not None:
            self.patch_size = patch_size if patch_size % 2 == 1 else patch_size + 1

        n_pts = len(src_points)
        if n_pts == 0:
            return SubpixelRefinementResult(
                refined_src_points=np.empty((0, 2), dtype=np.float32),
                refined_ref_points=np.empty((0, 2), dtype=np.float32),
                displacement_norm_mean=0.0,
                convergence_rate=1.0
            )

        # Convert images to float32
        src_float = src_image.astype(np.float32) if src_image.dtype != np.float32 else src_image
        ref_float = ref_image.astype(np.float32) if ref_image.dtype != np.float32 else ref_image

        refined_refs = np.copy(ref_points)
        refined_srcs = np.copy(src_points)
        displacements = []
        converged_count = 0

        for i in range(n_pts):
            refined_pt, disp, ok = self.refine_single_point(
                src_float, ref_float, src_points[i], ref_points[i]
            )
            if ok:
                refined_refs[i] = refined_pt
                displacements.append(disp)
                converged_count += 1
            else:
                displacements.append(0.0)

        mean_disp = float(np.mean(displacements)) if displacements else 0.0
        convergence_rate = float(converged_count / n_pts) if n_pts > 0 else 1.0

        return SubpixelRefinementResult(
            refined_src_points=refined_srcs,
            refined_ref_points=refined_refs,
            displacement_norm_mean=mean_disp,
            convergence_rate=convergence_rate
        )

"""
Diagnostic Visualizations and Figure Generation for SIH26166.
Generates multi-panel diagnostic figures showing keypoint matches, inliers,
warped alignments, checkerboard continuity, and residual error heatmaps.
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import cv2

from registration.pipeline import RegistrationPipeline
from evaluation.metrics import FullEvaluationReport


class RegistrationVisualizer:
    """
    Renders diagnostic scientific figures for registration verification.
    """

    @staticmethod
    def draw_correspondences(
        ref_img: np.ndarray,
        src_img: np.ndarray,
        ref_pts: np.ndarray,
        src_pts: np.ndarray,
        inliers_mask: Optional[np.ndarray] = None,
        max_draw: int = 100
    ) -> np.ndarray:
        """
        Render side-by-side correspondence plot with connecting match lines.
        """
        h_ref, w_ref = ref_img.shape[:2]
        h_src, w_src = src_img.shape[:2]

        h_canvas = max(h_ref, h_src)
        w_canvas = w_ref + w_src

        canvas = np.zeros((h_canvas, w_canvas, 3), dtype=np.uint8)

        # Convert to 3-channel uint8
        ref_u8 = (ref_img * 255).astype(np.uint8) if ref_img.max() <= 1.0 else ref_img.astype(np.uint8)
        src_u8 = (src_img * 255).astype(np.uint8) if src_img.max() <= 1.0 else src_img.astype(np.uint8)

        if ref_u8.ndim == 2:
            ref_u8 = cv2.cvtColor(ref_u8, cv2.COLOR_GRAY2BGR)
        if src_u8.ndim == 2:
            src_u8 = cv2.cvtColor(src_u8, cv2.COLOR_GRAY2BGR)

        canvas[:h_ref, :w_ref] = ref_u8
        canvas[:h_src, w_ref:w_canvas] = src_u8

        n_pts = len(ref_pts)
        if n_pts == 0:
            return canvas

        indices = np.arange(n_pts)
        if n_pts > max_draw:
            indices = np.random.choice(n_pts, max_draw, replace=False)

        for idx in indices:
            rx, ry = int(round(ref_pts[idx][0])), int(round(ref_pts[idx][1]))
            sx, sy = int(round(src_pts[idx][0])), int(round(src_pts[idx][1]))

            # Offset source x by reference width
            sx_shifted = sx + w_ref

            is_inlier = inliers_mask[idx] if inliers_mask is not None else True
            color = (0, 255, 0) if is_inlier else (0, 0, 255)  # Green for inlier, Red for outlier

            cv2.circle(canvas, (rx, ry), 3, (255, 200, 0), -1)
            cv2.circle(canvas, (sx_shifted, sy), 3, (255, 200, 0), -1)
            cv2.line(canvas, (rx, ry), (sx_shifted, sy), color, 1, cv2.LINE_AA)

        return canvas

    @classmethod
    def generate_all_visualizations(
        cls,
        ref_img: np.ndarray,
        src_img: np.ndarray,
        reg_img: np.ndarray,
        diff_map: np.ndarray,
        ref_pts: np.ndarray,
        src_pts: np.ndarray,
        inliers_mask: Optional[np.ndarray],
        report: FullEvaluationReport,
        output_dir: Path
    ) -> List[Path]:
        """
        Generate and save all diagnostic figures.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths = []

        # 1. Input Pair
        fig, axes = plt.subplots(1, 2, figsize=(10, 5), dpi=150)
        axes[0].imshow(ref_img, cmap="gray")
        axes[0].set_title(f"Reference Image ({ref_img.shape[1]}x{ref_img.shape[0]})")
        axes[0].axis("off")
        axes[1].imshow(src_img, cmap="gray")
        axes[1].set_title(f"Source Image ({src_img.shape[1]}x{src_img.shape[0]})")
        axes[1].axis("off")
        plt.tight_layout()
        p1 = output_dir / "01_input_pair.png"
        fig.savefig(p1)
        plt.close(fig)
        saved_paths.append(p1)

        # 2. Inlier Matches Plot
        inlier_canvas = cls.draw_correspondences(
            ref_img, src_img, ref_pts, src_pts, inliers_mask=inliers_mask, max_draw=120
        )
        fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
        ax.imshow(cv2.cvtColor(inlier_canvas, cv2.COLOR_BGR2RGB))
        ax.set_title(f"Inlier Correspondences (Green=Inlier ({report.inliers_count}), Red=Outlier)")
        ax.axis("off")
        plt.tight_layout()
        p2 = output_dir / "02_inlier_matches.png"
        fig.savefig(p2)
        plt.close(fig)
        saved_paths.append(p2)

        # 3. Alignment & Difference Map
        fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=150)
        axes[0].imshow(ref_img, cmap="gray")
        axes[0].set_title("Reference Image")
        axes[0].axis("off")

        axes[1].imshow(reg_img, cmap="gray")
        axes[1].set_title("Warped Registered Image")
        axes[1].axis("off")

        im_diff = axes[2].imshow(diff_map, cmap="inferno", vmin=0.0, vmax=max(0.3, float(diff_map.max())))
        axes[2].set_title(f"Difference Map (RMSE: {report.rmse:.4f})")
        axes[2].axis("off")
        fig.colorbar(im_diff, ax=axes[2], fraction=0.046, pad=0.04)

        plt.tight_layout()
        p3 = output_dir / "03_registration_alignment.png"
        fig.savefig(p3)
        plt.close(fig)
        saved_paths.append(p3)

        # 4. Checkerboard & Blend Overlay
        checker = RegistrationPipeline.create_checkerboard_overlay(ref_img, reg_img, tile_size=32)
        blend = RegistrationPipeline.create_false_color_blend(ref_img, reg_img)

        fig, axes = plt.subplots(1, 2, figsize=(12, 6), dpi=150)
        axes[0].imshow(checker, cmap="gray")
        axes[0].set_title("Checkerboard Alignment (32px tiles)")
        axes[0].axis("off")

        axes[1].imshow(blend)
        axes[1].set_title("False Color Blend (Green: Ref, Magenta: Reg)")
        axes[1].axis("off")

        plt.tight_layout()
        p4 = output_dir / "04_checkerboard_and_blend.png"
        fig.savefig(p4)
        plt.close(fig)
        saved_paths.append(p4)

        # 5. Comprehensive Summary Dashboard (6 panels)
        fig, axes = plt.subplots(2, 3, figsize=(16, 10), dpi=150)
        axes[0, 0].imshow(ref_img, cmap="gray")
        axes[0, 0].set_title("1. Reference Image")
        axes[0, 0].axis("off")

        axes[0, 1].imshow(src_img, cmap="gray")
        axes[0, 1].set_title("2. Source Image (Transformed)")
        axes[0, 1].axis("off")

        axes[0, 2].imshow(cv2.cvtColor(inlier_canvas, cv2.COLOR_BGR2RGB))
        axes[0, 2].set_title(f"3. Inliers ({report.inliers_count}/{report.filtered_matches} - {report.inlier_ratio:.1%})")
        axes[0, 2].axis("off")

        axes[1, 0].imshow(reg_img, cmap="gray")
        axes[1, 0].set_title("4. Warped Registered Image")
        axes[1, 0].axis("off")

        axes[1, 1].imshow(checker, cmap="gray")
        axes[1, 1].set_title("5. Checkerboard Continuity")
        axes[1, 1].axis("off")

        im_d = axes[1, 2].imshow(diff_map, cmap="inferno", vmin=0.0, vmax=max(0.3, float(diff_map.max())))
        axes[1, 2].set_title(f"6. Residual Error (SSIM: {report.ssim:.3f}, PSNR: {report.psnr_db:.1f}dB)")
        axes[1, 2].axis("off")
        fig.colorbar(im_d, ax=axes[1, 2], fraction=0.046, pad=0.04)

        plt.suptitle(
            f"SIH26166 Scientific Lunar Registration Prototype — Status: {report.registration_status}",
            fontsize=14, fontweight="bold"
        )
        plt.tight_layout()
        p5 = output_dir / "registration_dashboard_summary.png"
        fig.savefig(p5)
        plt.close(fig)
        saved_paths.append(p5)

        return saved_paths

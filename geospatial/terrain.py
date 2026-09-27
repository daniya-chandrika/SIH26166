"""
Scientific Lunar Terrain Suitability Analysis and Geomorphology Evaluation Engine (SIH26166).
Evaluates whether overlapping lunar imagery contains sufficient structural geomorphology
(craters, crater rims, ridges, valleys, ejecta blankets, and texture gradients)
to support robust, high-precision image registration.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Tuple
import numpy as np
import cv2


@dataclass
class TerrainSuitabilityReport:
    """Quantitative terrain evaluation report."""
    suitability_score: float  # [0.0, 1.0]
    is_suitable_for_registration: bool
    edge_density: float
    texture_entropy: float
    crater_prominence_index: float
    ridge_valley_prominence: float
    usable_contrast_ratio: float
    feature_richness_verdict: str  # HIGH_TEXTURE, MODERATE_FEATURES, LOW_TEXTURE_MARE, UNUSABLE_FLAT
    geomorphology_flags: Dict[str, bool] = field(default_factory=dict)
    detailed_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TerrainSuitabilityEvaluator:
    """
    Analyzes terrain texture, contrast, crater morphology, and structural gradients
    to distinguish geographic overlap from actual registration suitability.
    """

    def __init__(
        self,
        min_suitability_threshold: float = 0.25,
        min_edge_density: float = 0.015,
        min_contrast_ratio: float = 0.08
    ):
        self.min_suitability_threshold = min_suitability_threshold
        self.min_edge_density = min_edge_density
        self.min_contrast_ratio = min_contrast_ratio

    def evaluate_terrain(
        self,
        image_array: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> TerrainSuitabilityReport:
        """
        Evaluate structural geomorphological suitability of a lunar raster for registration.
        """
        # Ensure 2D float32 normalized [0.0, 1.0]
        if image_array.ndim == 3:
            img_gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY) if image_array.shape[2] == 3 else image_array[:, :, 0]
        else:
            img_gray = image_array.copy()

        if img_gray.dtype == np.uint8:
            img_f = img_gray.astype(np.float32) / 255.0
        elif img_gray.dtype == np.uint16:
            img_f = img_gray.astype(np.float32) / 65535.0
        else:
            img_f = img_gray.astype(np.float32)
            if img_f.max() > 1.5:
                img_min = float(img_f.min())
                img_max = float(img_f.max())
                img_f = (img_f - img_min) / max(1e-6, (img_max - img_min))
            else:
                img_f = np.clip(img_f, 0.0, 1.0)

        if mask is not None:
            valid_pixels = img_f[mask > 0]
        else:
            valid_pixels = img_f.ravel()

        if len(valid_pixels) < 100:
            return TerrainSuitabilityReport(
                suitability_score=0.0,
                is_suitable_for_registration=False,
                edge_density=0.0,
                texture_entropy=0.0,
                crater_prominence_index=0.0,
                ridge_valley_prominence=0.0,
                usable_contrast_ratio=0.0,
                feature_richness_verdict="UNUSABLE_FLAT",
                geomorphology_flags={"empty_or_masked": True},
                detailed_notes="Insufficient valid pixels for terrain evaluation."
            )

        # 1. Contrast Ratio (Michelson & RMS contrast)
        p10 = float(np.percentile(valid_pixels, 10))
        p90 = float(np.percentile(valid_pixels, 90))
        contrast_ratio = (p90 - p10) / max(1e-6, p90 + p10)
        contrast_ratio = float(np.clip(contrast_ratio, 0.0, 1.0))

        # 2. Gradient & Edge Density (Sobel energy)
        img_u8 = (img_f * 255.0).clip(0, 255).astype(np.uint8)
        sobel_x = cv2.Sobel(img_u8, cv2.CV_32F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(img_u8, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2)

        edge_threshold = 25.0
        edge_pixels = np.sum(grad_mag > edge_threshold)
        edge_density = float(edge_pixels / max(1, img_u8.size))

        # 3. Texture Entropy (Shannon Entropy of local histogram)
        hist, _ = np.histogram(valid_pixels, bins=64, range=(0.0, 1.0))
        prob = hist / float(np.sum(hist) + 1e-12)
        nz_prob = prob[prob > 0]
        entropy_val = float(-np.sum(nz_prob * np.log2(nz_prob)))
        norm_entropy = float(np.clip(entropy_val / 6.0, 0.0, 1.0))  # log2(64) = 6

        # 4. Crater & Ridge Prominence (Laplacian multi-scale response)
        laplacian_3 = np.abs(cv2.Laplacian(img_u8, cv2.CV_32F, ksize=3))
        laplacian_7 = np.abs(cv2.Laplacian(img_u8, cv2.CV_32F, ksize=7))
        crater_prominence = float(np.clip((np.mean(laplacian_3) + np.mean(laplacian_7)) / 40.0, 0.0, 1.0))

        # 5. Ridge / Valley Prominence (Morphological Black Top-Hat & White Top-Hat)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        w_tophat = cv2.morphologyEx(img_u8, cv2.MORPH_TOPHAT, kernel)
        b_tophat = cv2.morphologyEx(img_u8, cv2.MORPH_BLACKHAT, kernel)
        ridge_prominence = float(np.clip((np.mean(w_tophat) + np.mean(b_tophat)) / 30.0, 0.0, 1.0))

        # Composite Terrain Suitability Score
        # Formula: 30% Edge Density + 25% Texture Entropy + 20% Crater Index + 15% Ridge Index + 10% Contrast
        score = (
            0.30 * min(1.0, edge_density / 0.05) +
            0.25 * norm_entropy +
            0.20 * crater_prominence +
            0.15 * ridge_prominence +
            0.10 * min(1.0, contrast_ratio / 0.20)
        )
        suitability_score = float(np.clip(score, 0.0, 1.0))

        # Feature flags
        flags = {
            "has_prominent_craters": crater_prominence > 0.25,
            "has_ridges_valleys": ridge_prominence > 0.20,
            "has_high_contrast": contrast_ratio > 0.12,
            "is_low_texture_mare": suitability_score < 0.30 and edge_density < 0.015,
            "has_adequate_texture": edge_density >= self.min_edge_density
        }

        # Verdict classification
        if suitability_score >= 0.65:
            verdict = "HIGH_TEXTURE"
            notes = "Rich geomorphology with distinct crater rims, high texture entropy, and prominent edges."
        elif suitability_score >= 0.40:
            verdict = "MODERATE_FEATURES"
            notes = "Moderate structural terrain features suitable for multi-scale registration."
        elif suitability_score >= 0.25:
            verdict = "LOW_TEXTURE_MARE"
            notes = "Low-contrast or basaltic mare terrain with sparse prominent tie points; sub-pixel refinement recommended."
        else:
            verdict = "UNUSABLE_FLAT"
            notes = "Critically flat or shadow-depleted scene with insufficient geometric contrast for reliable matching."

        is_suitable = suitability_score >= self.min_suitability_threshold

        return TerrainSuitabilityReport(
            suitability_score=round(suitability_score, 4),
            is_suitable_for_registration=is_suitable,
            edge_density=round(edge_density, 4),
            texture_entropy=round(entropy_val, 4),
            crater_prominence_index=round(crater_prominence, 4),
            ridge_valley_prominence=round(ridge_prominence, 4),
            usable_contrast_ratio=round(contrast_ratio, 4),
            feature_richness_verdict=verdict,
            geomorphology_flags=flags,
            detailed_notes=notes
        )

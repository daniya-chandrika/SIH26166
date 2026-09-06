"""
Preprocessing Pipeline for SIH26166.
Configurable controller executing radiometric cleaning, robust normalization,
CLAHE enhancement, and multi-scale pyramid generation.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

from prototype.data_interface import ImagePair
from preprocessing.normalization import IntensityNormalizer
from preprocessing.enhancement import ContrastEnhancer
from preprocessing.multiscale import MultiscaleRepresentation


@dataclass
class PreprocessingConfig:
    normalize: bool = True
    lower_percentile: float = 1.0
    upper_percentile: float = 99.0
    apply_clahe: bool = True
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: Tuple[int, int] = (8, 8)
    apply_unsharp: bool = True
    unsharp_sigma: float = 1.0
    unsharp_strength: float = 0.3
    multiscale: bool = True
    pyramid_levels: int = 3
    target_gsd_m: Optional[float] = None


@dataclass
class PreprocessedPair:
    reference_normalized: np.ndarray        # Float32 in [0, 1]
    reference_enhanced_uint8: np.ndarray    # Uint8 in [0, 255]
    reference_pyramid: List[np.ndarray]

    source_normalized: np.ndarray           # Float32 in [0, 1]
    source_enhanced_uint8: np.ndarray       # Uint8 in [0, 255]
    source_pyramid: List[np.ndarray]

    config: PreprocessingConfig
    metadata: Dict[str, Any] = field(default_factory=dict)


class PreprocessingPipeline:
    """
    Executes consistent radiometric and multiscale preprocessing across image pairs.
    """

    def __init__(self, config: Optional[PreprocessingConfig] = None):
        self.config = config or PreprocessingConfig()

    def process_single_image(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray, List[np.ndarray]]:
        """
        Process single raster through normalization, CLAHE enhancement, and pyramid construction.
        Returns: (normalized_float32, enhanced_uint8, pyramid)
        """
        # 1. Robust Percentile Normalization
        if self.config.normalize:
            norm_float = IntensityNormalizer.robust_percentile_normalize(
                image,
                lower_percentile=self.config.lower_percentile,
                upper_percentile=self.config.upper_percentile
            )
        else:
            norm_float = IntensityNormalizer.ensure_grayscale_2d(image)
            if norm_float.max() > 1.0:
                norm_float = norm_float / 255.0

        # Convert to uint8 for descriptor detection
        uint8_img = IntensityNormalizer.to_uint8(norm_float)

        # 2. Local Contrast Enhancement (CLAHE)
        if self.config.apply_clahe:
            enhanced_uint8 = ContrastEnhancer.apply_clahe(
                uint8_img,
                clip_limit=self.config.clahe_clip_limit,
                tile_grid_size=self.config.clahe_tile_grid
            )
        else:
            enhanced_uint8 = uint8_img

        # 3. Unsharp Masking
        if self.config.apply_unsharp:
            enhanced_uint8 = ContrastEnhancer.apply_unsharp_mask(
                enhanced_uint8,
                sigma=self.config.unsharp_sigma,
                strength=self.config.unsharp_strength
            )

        # 4. Multi-scale Pyramid
        if self.config.multiscale and self.config.pyramid_levels > 1:
            pyramid = MultiscaleRepresentation.build_gaussian_pyramid(
                enhanced_uint8,
                levels=self.config.pyramid_levels
            )
        else:
            pyramid = [enhanced_uint8]

        return norm_float, enhanced_uint8, pyramid

    def process(self, pair: ImagePair) -> PreprocessedPair:
        """
        Execute preprocessing for both reference and source imagery in an ImagePair.
        """
        ref_norm, ref_enh, ref_pyr = self.process_single_image(pair.reference)
        src_norm, src_enh, src_pyr = self.process_single_image(pair.source)

        meta = {
            "pair_name": pair.name,
            "scenario": pair.scenario_name,
            "ref_shape": ref_enh.shape,
            "src_shape": src_enh.shape,
            "pyramid_levels": len(ref_pyr),
            "preprocessing_config": {
                "normalize": self.config.normalize,
                "clahe": self.config.apply_clahe,
                "unsharp": self.config.apply_unsharp,
                "multiscale": self.config.multiscale
            }
        }

        return PreprocessedPair(
            reference_normalized=ref_norm,
            reference_enhanced_uint8=ref_enh,
            reference_pyramid=ref_pyr,
            source_normalized=src_norm,
            source_enhanced_uint8=src_enh,
            source_pyramid=src_pyr,
            config=self.config,
            metadata=meta
        )

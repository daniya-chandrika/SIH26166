"""
Generic Image Pair Data Interface for SIH26166.
Acts as the universal contract between data sources (Synthetic / Real Lunar Data)
and downstream registration algorithms.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import numpy as np


@dataclass
class ImagePair:
    """
    Standard interface for paired lunar imagery.
    Both synthetic generator and real lunar sensor loaders produce ImagePair instances.
    """
    reference: np.ndarray                   # 2D array (H, W) or multi-band (H, W, C)
    source: np.ndarray                      # 2D array (H, W) or multi-band (H, W, C)
    metadata: Optional[Dict[str, Any]] = None
    ground_truth_transform: Optional[np.ndarray] = None  # 3x3 matrix mapping source to reference coordinates
    ground_truth_details: Optional[Dict[str, Any]] = None
    scenario_name: str = "custom"
    seed: Optional[int] = None
    name: str = "lunar_image_pair"

    @property
    def reference_shape(self) -> tuple:
        return self.reference.shape

    @property
    def source_shape(self) -> tuple:
        return self.source.shape

    @property
    def has_ground_truth(self) -> bool:
        return self.ground_truth_transform is not None

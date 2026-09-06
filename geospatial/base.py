"""
Geospatial Validation and Footprint Intersection Interface.
[Placeholder for Phase 8: Geographic footprint & common-area validation]
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

from metadata.models import LunarProductMetadata


@dataclass
class FootprintOverlapResult:
    source_image_id: str
    reference_image_id: str
    overlap_percentage: float
    intersection_wkt: Optional[str] = None
    intersection_geojson: Optional[Dict[str, Any]] = None
    is_valid_pair: bool = False
    validation_message: str = ""


class GeospatialValidatorBase(ABC):
    """
    Abstract interface for lunar orbital footprint intersection and terrain validation.
    """

    @abstractmethod
    def compute_overlap(
        self,
        source_meta: LunarProductMetadata,
        reference_meta: LunarProductMetadata
    ) -> FootprintOverlapResult:
        """Calculate spatial intersection polygon and percentage overlap between two lunar images."""
        pass

    @abstractmethod
    def validate_same_terrain(
        self,
        source_meta: LunarProductMetadata,
        reference_meta: LunarProductMetadata,
        min_overlap_threshold: float = 20.0
    ) -> bool:
        """Validate whether two images share overlapping lunar surface terrain."""
        pass

    @abstractmethod
    def find_candidate_pairs(
        self,
        products: List[LunarProductMetadata],
        min_overlap_pct: float = 15.0
    ) -> List[FootprintOverlapResult]:
        """Discover all viable registration candidate pairs from a catalog of products."""
        pass

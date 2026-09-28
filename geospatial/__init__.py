"""
Geospatial and Geographic Footprint Processing Package for SIH26166.
"""
from geospatial.base import GeospatialValidatorBase, FootprintOverlapResult
from geospatial.overlap import GeospatialFootprintValidator
from geospatial.terrain import TerrainSuitabilityEvaluator, TerrainSuitabilityReport
from geospatial.catalog import (
    LunarCatalogDiscoveryService,
    PREDEFINED_LUNAR_REGIONS,
    validate_lunar_coordinates,
    construct_roi_bbox
)

__all__ = [
    "GeospatialValidatorBase",
    "FootprintOverlapResult",
    "GeospatialFootprintValidator",
    "TerrainSuitabilityEvaluator",
    "TerrainSuitabilityReport",
    "LunarCatalogDiscoveryService",
    "PREDEFINED_LUNAR_REGIONS",
    "validate_lunar_coordinates",
    "construct_roi_bbox"
]

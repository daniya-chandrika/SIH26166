"""
Matching Package for SIH26166.
"""
from matching.base import MatchResult, FeatureMatcherBase
from matching.matcher import DescriptorMatcher
from matching.confidence import ConfidenceFilter
from matching.spatial_filter import SpatialDistributionFilter, SpatialSelectionResult
from matching.learned import SuperPointAdapter, LightGlueAdapter, LoFTRAdapter

__all__ = [
    "MatchResult",
    "FeatureMatcherBase",
    "DescriptorMatcher",
    "ConfidenceFilter",
    "SpatialDistributionFilter",
    "SpatialSelectionResult",
    "SuperPointAdapter",
    "LightGlueAdapter",
    "LoFTRAdapter",
]

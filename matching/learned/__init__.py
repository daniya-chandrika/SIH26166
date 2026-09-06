"""
Learned Feature and Matching Adapters for SIH26166 (Phase 29).
Defines interfaces for future SuperPoint, LightGlue, and LoFTR neural network backends.
"""
from matching.learned.superpoint_adapter import SuperPointAdapter
from matching.learned.lightglue_adapter import LightGlueAdapter
from matching.learned.loftr_adapter import LoFTRAdapter

__all__ = ["SuperPointAdapter", "LightGlueAdapter", "LoFTRAdapter"]

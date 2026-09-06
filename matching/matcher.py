"""
Feature Matching and Correspondence Estimation for SIH26166.
Implements BFMatcher with Lowe's ratio test and confidence scoring.
"""
from typing import Optional, Tuple
import numpy as np
import cv2

from features.base import KeypointsData
from matching.base import FeatureMatcherBase, MatchResult
from matching.confidence import ConfidenceFilter


class DescriptorMatcher(FeatureMatcherBase):
    """
    Descriptor-based correspondence matcher with Lowe's ratio test.
    """

    def __init__(
        self,
        ratio_threshold: float = 0.78,
        cross_check: bool = False
    ):
        self._ratio_threshold = ratio_threshold
        self._cross_check = cross_check

    @property
    def name(self) -> str:
        return "BFMatcher"

    def match(
        self,
        features_src: KeypointsData,
        features_ref: KeypointsData,
        min_confidence: float = 0.10
    ) -> MatchResult:
        if (
            features_src.descriptors is None or len(features_src.descriptors) < 2 or
            features_ref.descriptors is None or len(features_ref.descriptors) < 2
        ):
            return MatchResult(
                source_points=np.empty((0, 2), dtype=np.float32),
                reference_points=np.empty((0, 2), dtype=np.float32),
                confidence=np.empty((0,), dtype=np.float32),
                raw_match_count=0,
                filtered_match_count=0
            )

        is_binary = features_src.descriptors.dtype == np.uint8
        norm_type = cv2.NORM_HAMMING if is_binary else cv2.NORM_L2

        matcher = cv2.BFMatcher(normType=norm_type, crossCheck=False)
        knn_matches = matcher.knnMatch(features_src.descriptors, features_ref.descriptors, k=2)

        raw_count = len(knn_matches)
        src_pts_list = []
        ref_pts_list = []
        conf_list = []

        for match_pair in knn_matches:
            if len(match_pair) == 2:
                m, n = match_pair
                # Lowe's ratio test
                if m.distance <= self._ratio_threshold * n.distance:
                    conf = ConfidenceFilter.calculate_confidence(
                        m.distance, n.distance, is_binary=is_binary
                    )
                    if conf >= min_confidence:
                        src_pts_list.append(features_src.keypoints[m.queryIdx])
                        ref_pts_list.append(features_ref.keypoints[m.trainIdx])
                        conf_list.append(conf)

        if not src_pts_list:
            return MatchResult(
                source_points=np.empty((0, 2), dtype=np.float32),
                reference_points=np.empty((0, 2), dtype=np.float32),
                confidence=np.empty((0,), dtype=np.float32),
                raw_match_count=raw_count,
                filtered_match_count=0
            )

        src_pts_arr = np.array(src_pts_list, dtype=np.float32)
        ref_pts_arr = np.array(ref_pts_list, dtype=np.float32)
        conf_arr = np.array(conf_list, dtype=np.float32)

        return MatchResult(
            source_points=src_pts_arr,
            reference_points=ref_pts_arr,
            confidence=conf_arr,
            raw_match_count=raw_count,
            filtered_match_count=len(src_pts_arr)
        )

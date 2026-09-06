"""
Unit tests for Feature Detection, Matching, Confidence, and Spatial Distribution (Phases 11-13).
"""
import unittest
import numpy as np

from prototype.synthetic.dataset import SyntheticDatasetGenerator
from preprocessing.pipeline import PreprocessingPipeline
from features.detector import SIFTFeatureDetector, ORBFeatureDetector, AutoFeatureDetector
from matching.matcher import DescriptorMatcher
from matching.confidence import ConfidenceFilter
from matching.spatial_filter import SpatialDistributionFilter
from matching.learned import SuperPointAdapter, LightGlueAdapter, LoFTRAdapter


class TestFeaturesAndMatching(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pair = SyntheticDatasetGenerator(default_seed=42).generate_pair(
            scenario_name="rotation_translation", width=128, height=128
        )
        preprocessed = PreprocessingPipeline().process(pair)
        cls.ref_img = preprocessed.reference_enhanced_uint8
        cls.src_img = preprocessed.source_enhanced_uint8

    def test_sift_detector(self):
        """Verify SIFT extracts keypoints and 128D descriptors."""
        detector = SIFTFeatureDetector(nfeatures=500)
        feats = detector.extract_features(self.ref_img)

        self.assertGreater(len(feats.keypoints), 10)
        self.assertEqual(feats.descriptors.shape[1], 128)
        self.assertEqual(feats.keypoints.shape[1], 2)
        self.assertEqual(feats.image_shape, (128, 128))

    def test_orb_detector(self):
        """Verify ORB extracts keypoints and binary descriptors."""
        detector = ORBFeatureDetector(nfeatures=500)
        feats = detector.extract_features(self.ref_img)

        self.assertGreater(len(feats.keypoints), 10)
        self.assertEqual(feats.descriptors.shape[1], 32)
        self.assertEqual(feats.descriptors.dtype, np.uint8)

    def test_auto_detector(self):
        """Verify AutoFeatureDetector defaults to SIFT."""
        detector = AutoFeatureDetector()
        feats = detector.extract_features(self.ref_img)
        self.assertIn(detector.name, ["SIFT", "ORB"])
        self.assertGreater(len(feats.keypoints), 0)

    def test_descriptor_matcher_with_ratio_test(self):
        """Verify BFMatcher with ratio test returns valid correspondences."""
        sift = SIFTFeatureDetector()
        feats_ref = sift.extract_features(self.ref_img)
        feats_src = sift.extract_features(self.src_img)

        matcher = DescriptorMatcher(ratio_threshold=0.85)
        match_res = matcher.match(feats_src, feats_ref)

        self.assertGreater(match_res.raw_match_count, 0)
        self.assertGreater(match_res.filtered_match_count, 0)
        self.assertEqual(len(match_res.source_points), match_res.filtered_match_count)
        self.assertEqual(len(match_res.reference_points), match_res.filtered_match_count)
        self.assertTrue((match_res.confidence >= 0.0).all())

    def test_confidence_filtering(self):
        """Verify confidence filter removes low-confidence matches."""
        src_pts = np.array([[10, 10], [20, 20], [30, 30]], dtype=np.float32)
        ref_pts = np.array([[12, 12], [22, 22], [32, 32]], dtype=np.float32)
        confs = np.array([0.9, 0.05, 0.6], dtype=np.float32)

        f_src, f_ref, f_conf = ConfidenceFilter.filter_by_confidence(
            src_pts, ref_pts, confs, min_confidence=0.5
        )
        self.assertEqual(len(f_conf), 2)
        self.assertListEqual(list(f_conf), [0.9, 0.6])

    def test_spatial_distribution_filter(self):
        """Verify uniform spatial selection partitions points across grid bins."""
        # Create clustered points
        n = 50
        src_pts = np.random.uniform(10, 20, (n, 2)).astype(np.float32)
        ref_pts = np.random.uniform(10, 20, (n, 2)).astype(np.float32)
        confs = np.random.uniform(0.5, 1.0, (n,)).astype(np.float32)

        spatial_filter = SpatialDistributionFilter(grid_rows=4, grid_cols=4, max_matches_per_cell=3)
        res = spatial_filter.spatially_uniform_selection(
            src_pts, ref_pts, confs, image_width=128, image_height=128
        )

        # Points in cell (0, 0) should be capped at max_matches_per_cell (3)
        self.assertLessEqual(len(res.reference_points), 3)
        self.assertEqual(res.occupied_cells, 1)
        self.assertAlmostEqual(res.spatial_coverage_percentage, (1 / 16) * 100.0)

    def test_learned_adapters_offline_stubs(self):
        """Verify deep learning model adapter interfaces return is_available() False when offline."""
        sp = SuperPointAdapter()
        lg = LightGlueAdapter()
        loftr = LoFTRAdapter()

        self.assertFalse(sp.is_available())
        self.assertFalse(lg.is_available())
        self.assertFalse(loftr.is_available())


if __name__ == "__main__":
    unittest.main()

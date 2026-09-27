"""
Unit and Policy Tests for Zero-Silent-Fallback and Failure Detection (Section 45).
"""
import unittest
import numpy as np

from features.detector import FeatureDetectorFactory
from matching.learned import SuperPointAdapter, LightGlueAdapter, LoFTRAdapter
from core.exceptions import ModelUnavailableError, RegistrationStatus


class TestFallbacksAndConfig(unittest.TestCase):

    def test_superpoint_unavailable_raises_model_unavailable_error(self):
        """Verify requesting unavailable SuperPoint raises ModelUnavailableError (NO SILENT SIFT FALLBACK)."""
        with self.assertRaises(ModelUnavailableError) as ctx:
            FeatureDetectorFactory.create("SUPERPOINT")
        
        err = ctx.exception
        self.assertEqual(err.status, RegistrationStatus.MODEL_UNAVAILABLE)
        self.assertEqual(err.model_name, "SuperPoint")
        self.assertIn("SuperPoint", err.message)

    def test_lightglue_unavailable_raises_model_unavailable_error(self):
        """Verify requesting unavailable LightGlue matcher raises ModelUnavailableError."""
        lg = LightGlueAdapter()
        self.assertFalse(lg.is_available())
        
        from features.base import KeypointsData
        dummy_kpts = KeypointsData(keypoints=np.empty((0, 2)), descriptors=np.empty((0, 256)), scores=np.empty((0,)), image_shape=(512, 512))
        
        with self.assertRaises(ModelUnavailableError) as ctx:
            lg.match(dummy_kpts, dummy_kpts)
        self.assertEqual(ctx.exception.status, RegistrationStatus.MODEL_UNAVAILABLE)

    def test_loftr_unavailable_raises_model_unavailable_error(self):
        """Verify requesting unavailable LoFTR matcher raises ModelUnavailableError."""
        loftr = LoFTRAdapter()
        self.assertFalse(loftr.is_available())
        
        with self.assertRaises(ModelUnavailableError) as ctx:
            loftr.match_dense(np.zeros((100, 100)), np.zeros((100, 100)))
        self.assertEqual(ctx.exception.status, RegistrationStatus.MODEL_UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for Preprocessing and Multiscale Pipeline (Phase 10).
"""
import unittest
import numpy as np

from prototype.synthetic.dataset import SyntheticDatasetGenerator
from preprocessing.normalization import IntensityNormalizer
from preprocessing.enhancement import ContrastEnhancer
from preprocessing.multiscale import MultiscaleRepresentation
from preprocessing.sensor_config import SENSOR_PROFILES, get_sensor_config
from preprocessing.pipeline import PreprocessingConfig, PreprocessingPipeline


class TestPreprocessing(unittest.TestCase):

    def test_normalization_with_nan_and_inf(self):
        """Verify NaN and Inf values are safely replaced without crashing."""
        arr = np.array([
            [10.0, np.nan, 30.0],
            [np.inf, 50.0, 60.0],
            [70.0, 80.0, 90.0]
        ], dtype=np.float32)

        norm = IntensityNormalizer.robust_percentile_normalize(arr)
        self.assertFalse(np.isnan(norm).any())
        self.assertFalse(np.isinf(norm).any())
        self.assertTrue(0.0 <= norm.min() <= norm.max() <= 1.0)

    def test_constant_image_normalization(self):
        """Verify zero-variance/constant image returns zeros safely."""
        constant_arr = np.full((32, 32), 42.0, dtype=np.float32)
        norm = IntensityNormalizer.robust_percentile_normalize(constant_arr)
        self.assertEqual(norm.shape, (32, 32))
        self.assertEqual(norm.max(), 0.0)

    def test_clahe_enhancement(self):
        """Verify CLAHE returns valid uint8 array with enhanced contrast."""
        img = (np.random.rand(64, 64) * 255).astype(np.uint8)
        enhanced = ContrastEnhancer.apply_clahe(img, clip_limit=2.0)
        self.assertEqual(enhanced.shape, (64, 64))
        self.assertEqual(enhanced.dtype, np.uint8)

    def test_multiscale_gaussian_pyramid(self):
        """Verify Gaussian pyramid correctly downsamples by factor of 2."""
        img = (np.random.rand(128, 128) * 255).astype(np.uint8)
        pyramid = MultiscaleRepresentation.build_gaussian_pyramid(img, levels=3)

        self.assertEqual(len(pyramid), 3)
        self.assertEqual(pyramid[0].shape, (128, 128))
        self.assertEqual(pyramid[1].shape, (64, 64))
        self.assertEqual(pyramid[2].shape, (32, 32))

    def test_sensor_profiles(self):
        """Verify authentic sensor specs are available."""
        ohrc = get_sensor_config("OHRC")
        self.assertEqual(ohrc.nominal_gsd_m, 0.25)
        tmc2 = get_sensor_config("TMC-2")
        self.assertEqual(tmc2.nominal_gsd_m, 5.0)
        iirs = get_sensor_config("IIRS")
        self.assertEqual(iirs.nominal_bands, 256)
        lroc = get_sensor_config("LROC")
        self.assertEqual(lroc.nominal_gsd_m, 0.50)

    def test_preprocessing_pipeline(self):
        """Verify full PreprocessingPipeline operates on ImagePair."""
        pair = SyntheticDatasetGenerator(default_seed=42).generate_pair(
            scenario_name="combined", width=64, height=64
        )
        pipeline = PreprocessingPipeline()
        res = pipeline.process(pair)

        self.assertEqual(res.reference_enhanced_uint8.shape, (64, 64))
        self.assertEqual(res.source_enhanced_uint8.shape, (64, 64))
        self.assertEqual(len(res.reference_pyramid), 3)


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for Synthetic Lunar Dataset Engine (Phase 9).
Tests procedural terrain generation, ground truth transformations, scenarios, and dataset building.
"""
import unittest
import numpy as np

from prototype.data_interface import ImagePair
from prototype.synthetic.generator import SyntheticTerrainGenerator
from prototype.synthetic.transformations import TransformationEngine, GeometricParams, RadiometricParams
from prototype.synthetic.scenarios import SyntheticScenarioManager, SCENARIOS
from prototype.synthetic.ground_truth import GroundTruthTransform
from prototype.synthetic.dataset import SyntheticDatasetGenerator


class TestSyntheticEngine(unittest.TestCase):

    def test_terrain_generator_determinism(self):
        """Verify identical seed produces exact identical terrain."""
        gen1 = SyntheticTerrainGenerator(seed=123)
        img1 = gen1.generate(width=128, height=128)

        gen2 = SyntheticTerrainGenerator(seed=123)
        img2 = gen2.generate(width=128, height=128)

        self.assertEqual(img1.shape, (128, 128))
        self.assertEqual(img1.dtype, np.float32)
        np.testing.assert_allclose(img1, img2, rtol=1e-5, atol=1e-5)
        self.assertTrue(0.0 <= img1.min() <= img1.max() <= 1.0)

    def test_terrain_generator_different_seeds(self):
        """Verify different seeds produce distinct terrain maps."""
        gen1 = SyntheticTerrainGenerator(seed=10)
        img1 = gen1.generate(width=128, height=128)

        gen2 = SyntheticTerrainGenerator(seed=20)
        img2 = gen2.generate(width=128, height=128)

        self.assertFalse(np.allclose(img1, img2))

    def test_ground_truth_matrix_identity(self):
        """Verify neutral parameters produce identity transformation."""
        engine = TransformationEngine()
        params = GeometricParams(rotation_deg=0.0, scale=1.0, translation_x=0.0, translation_y=0.0)
        H = engine.build_ground_truth_matrix(params, center_x=64.0, center_y=64.0)

        np.testing.assert_allclose(H, np.eye(3), atol=1e-6)

    def test_ground_truth_decomposition(self):
        """Verify matrix decomposition correctly extracts geometric components."""
        engine = TransformationEngine()
        params = GeometricParams(rotation_deg=30.0, scale=1.2, translation_x=10.0, translation_y=-5.0)
        H = engine.build_ground_truth_matrix(params, center_x=128.0, center_y=128.0)

        gt = GroundTruthTransform(H)
        decomp = gt.decompose_matrix(H)

        self.assertAlmostEqual(decomp["rotation_deg"], 30.0, delta=0.5)
        self.assertAlmostEqual(decomp["scale"], 1.2, delta=0.05)

    def test_all_eight_scenarios_exist(self):
        """Verify all 8 standard scenarios are defined and retrievable."""
        expected_scenarios = [
            "illumination", "scale", "rotation_translation", "viewpoint",
            "scale_illumination", "viewpoint_illumination", "strong_scale", "combined"
        ]
        for name in expected_scenarios:
            scen = SyntheticScenarioManager.get_scenario(name)
            self.assertEqual(scen.name, name)
            self.assertIsNotNone(scen.description)
            self.assertIsNotNone(scen.geo_params)
            self.assertIsNotNone(scen.radio_params)

    def test_synthetic_dataset_generator(self):
        """Verify dataset generator produces valid ImagePair with ground truth."""
        dataset_gen = SyntheticDatasetGenerator(default_seed=42)
        pair = dataset_gen.generate_pair(scenario_name="rotation_translation", width=128, height=128)

        self.assertIsInstance(pair, ImagePair)
        self.assertEqual(pair.reference.shape, (128, 128))
        self.assertEqual(pair.source.shape, (128, 128))
        self.assertTrue(pair.has_ground_truth)
        self.assertEqual(pair.ground_truth_transform.shape, (3, 3))


if __name__ == "__main__":
    unittest.main()

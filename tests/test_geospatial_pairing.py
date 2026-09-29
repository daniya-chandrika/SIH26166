"""
Unit and Integration Tests for Geospatial Footprint & Terrain Suitability Engine.
"""
import unittest
import numpy as np
from metadata.models import LunarProductMetadata
from geospatial.overlap import GeospatialFootprintValidator, Polygon
from geospatial.terrain import TerrainSuitabilityEvaluator


class TestGeospatialPairing(unittest.TestCase):

    def setUp(self):
        self.validator = GeospatialFootprintValidator(min_overlap_threshold=15.0)
        self.terrain_eval = TerrainSuitabilityEvaluator()

    def test_overlapping_bounding_boxes(self):
        """Verify overlap calculation for intersecting lunar footprints."""
        m_ref = LunarProductMetadata(
            image_id="LROC_REF_01",
            latitude=-89.90,
            longitude=0.0,
            spatial_resolution=0.5,
            bounding_box=(-90.0, -89.8, -5.0, 5.0)
        )
        m_src = LunarProductMetadata(
            image_id="OHRC_SRC_01",
            latitude=-89.90,
            longitude=1.0,
            spatial_resolution=0.25,
            bounding_box=(-89.95, -89.85, 0.0, 4.0)
        )

        res = self.validator.compute_overlap(m_src, m_ref)
        self.assertTrue(res.is_valid_pair)
        self.assertGreater(res.overlap_percentage, 15.0)
        self.assertIsNotNone(res.intersection_wkt)

    def test_non_overlapping_products_rejected(self):
        """Verify non-overlapping lunar products are rejected with is_valid_pair = False."""
        m_pole = LunarProductMetadata(
            image_id="LROC_SOUTH_POLE",
            latitude=-89.90,
            longitude=0.0,
            bounding_box=(-90.0, -89.8, -5.0, 5.0)
        )
        m_equator = LunarProductMetadata(
            image_id="OHRC_EQUATOR",
            latitude=0.67,
            longitude=23.47,
            bounding_box=(0.5, 0.8, 23.0, 24.0)
        )

        res = self.validator.compute_overlap(m_pole, m_equator)
        self.assertFalse(res.is_valid_pair)
        self.assertEqual(res.overlap_percentage, 0.0)

    def test_candidate_pairs_discovery(self):
        """Verify find_candidate_pairs discovers overlapping pairs across a catalog."""
        catalog = [
            LunarProductMetadata(image_id="P1", bounding_box=(-89.9, -89.8, 0.0, 2.0)),
            LunarProductMetadata(image_id="P2", bounding_box=(-89.9, -89.8, 1.0, 3.0)),
            LunarProductMetadata(image_id="P3", bounding_box=(10.0, 11.0, 20.0, 21.0))
        ]
        pairs = self.validator.find_candidate_pairs(catalog, min_overlap_pct=10.0)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].source_image_id, "P1")
        self.assertEqual(pairs[0].reference_image_id, "P2")

    def test_terrain_suitability_evaluation(self):
        """Verify terrain evaluator generates correct metrics for textured vs flat images."""
        # Highly textured crater image
        rng = np.random.RandomState(42)
        textured = rng.normal(0.5, 0.15, (256, 256)).astype(np.float32)
        # Add a simulated crater ring
        y, x = np.ogrid[:256, :256]
        r = np.sqrt((x - 128)**2 + (y - 128)**2)
        textured[np.abs(r - 50) < 5] = 0.95
        textured[np.abs(r - 45) < 3] = 0.10

        rep = self.terrain_eval.evaluate_terrain(textured)
        self.assertTrue(rep.is_suitable_for_registration)
        self.assertGreater(rep.suitability_score, 0.35)
        self.assertIn(rep.feature_richness_verdict, ["HIGH_TEXTURE", "MODERATE_FEATURES"])

        # Flat low-variance image
        flat = np.full((256, 256), 0.5, dtype=np.float32)
        flat_rep = self.terrain_eval.evaluate_terrain(flat)
        self.assertFalse(flat_rep.is_suitable_for_registration)
        self.assertLess(flat_rep.suitability_score, 0.35)


if __name__ == "__main__":
    unittest.main()

"""
Unit and Integration Tests for FastAPI REST API Interface.
"""
import unittest
from fastapi.testclient import TestClient

from api.server import app


class TestFastAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        """Verify GET /api/v1/health returns online status and system version."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertEqual(data["version"], "2.0.0")
        self.assertIn("OHRC", data["supported_sensors"])

    def test_regions_endpoint(self):
        """Verify GET /api/v1/regions lists standard lunar regions R01 - R10."""
        resp = self.client.get("/api/v1/regions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["total"], 10)
        codes = [r["region_code"] for r in data["regions"]]
        self.assertIn("R01", codes)
        self.assertIn("R04", codes)

    def test_products_endpoint(self):
        """Verify GET /api/v1/products returns orbital product catalog."""
        resp = self.client.get("/api/v1/products")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["total"], 0)

    def test_synthetic_registration_trigger(self):
        """Verify POST /api/v1/registration executes 12-stage prototype pipeline."""
        payload = {
            "mode": "synthetic",
            "scenario": "rotation_translation",
            "seed": 42,
            "image_size": 256,
            "detector": "SIFT",
            "model_type": "HOMOGRAPHY"
        }
        resp = self.client.post("/api/v1/registration", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("rmse", data["metrics"])
        self.assertLess(data["metrics"]["rmse"], 2.0)

    def test_list_experiments(self):
        """Verify GET /api/v1/experiments returns recorded experiments."""
        resp = self.client.get("/api/v1/experiments")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("experiments", data)
        self.assertIn("total", data)


if __name__ == "__main__":
    unittest.main()

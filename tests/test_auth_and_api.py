"""
Unit and Integration Tests for FastAPI REST API Interface.
Covers all /api/v1 endpoints with full end-to-end assertions.
"""
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from api.server import app

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA_DIR = WORKSPACE_ROOT / "tests" / "sample_data"


class TestFastAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_root_endpoint(self):
        """Verify GET / returns API documentation index and health route info."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("version", data)
        self.assertEqual(data["health_check"], "/api/v1/health")

    def test_02_health_endpoint(self):
        """Verify GET /api/v1/health returns online status and system version."""
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertEqual(data["version"], "2.0.0")
        self.assertIn("OHRC", data["supported_sensors"])

    def test_03_regions_endpoint(self):
        """Verify GET /api/v1/regions lists standard lunar regions R01 - R10."""
        resp = self.client.get("/api/v1/regions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["total"], 10)
        codes = [r["code"] for r in data["regions"]]
        self.assertIn("R01", codes)
        self.assertIn("R04", codes)

    def test_04_regions_search_endpoint(self):
        """Verify POST /api/v1/regions/search supports coordinate and bbox search."""
        # Search by coordinates
        payload_coords = {"latitude": -89.9, "longitude": 0.0, "radius_km": 15.0}
        resp = self.client.post("/api/v1/regions/search", json=payload_coords)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("candidate_pairs", data)

        # Search by bbox
        payload_bbox = {"min_latitude": -90.0, "max_latitude": -85.0, "min_longitude": -180.0, "max_longitude": 180.0}
        resp_bbox = self.client.post("/api/v1/regions/search", json=payload_bbox)
        self.assertEqual(resp_bbox.status_code, 200)
        data_bbox = resp_bbox.json()
        self.assertIn("candidate_pairs", data_bbox)

    def test_05_sensor_matrix_endpoint(self):
        """Verify GET /api/v1/sensor-matrix returns region cross-sensor matrix."""
        resp = self.client.get("/api/v1/sensor-matrix")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("sensor_matrix", data)
        self.assertGreaterEqual(len(data["sensor_matrix"]), 10)

    def test_06_products_endpoint(self):
        """Verify GET /api/v1/products returns orbital product catalog."""
        resp = self.client.get("/api/v1/products")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["total"], 0)

    def test_07_products_pairs_endpoint(self):
        """Verify GET /api/v1/products/pairs returns candidate pairs for region."""
        resp = self.client.get("/api/v1/products/pairs?region_id=R01")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("pairs", data)
        self.assertGreaterEqual(data["total"], 0)

    def test_08_remote_search_endpoint(self):
        """Verify POST /api/v1/remote/search queries remote archives."""
        payload = {
            "min_latitude": -90.0,
            "max_latitude": 90.0,
            "min_longitude": -180.0,
            "max_longitude": 180.0,
            "sensor": "OHRC"
        }
        resp = self.client.post("/api/v1/remote/search", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertGreater(data["count"], 0)

    def test_09_remote_cache_endpoint(self):
        """Verify POST /api/v1/remote/cache creates local cached window."""
        payload = {
            "product_id": "CH2_OHRC_FASTAPI_TEST",
            "sensor": "OHRC",
            "latitude": -89.9,
            "longitude": 0.0,
            "window_size": 256
        }
        resp = self.client.post("/api/v1/remote/cache", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("product_id", data)

    def test_10_metadata_endpoint(self):
        """Verify GET /api/v1/metadata returns manifest or placeholder."""
        resp = self.client.get("/api/v1/metadata")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue("manifest" in data or "message" in data)

    def test_11_quality_endpoint(self):
        """Verify GET /api/v1/quality returns quality report or placeholder."""
        resp = self.client.get("/api/v1/quality")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue("quality_report" in data or "message" in data)

    def test_12_synthetic_registration_trigger(self):
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

    def test_13_real_registration_trigger(self):
        """Verify POST /api/v1/registration executes 12-stage real multimodal pipeline."""
        payload = {
            "mode": "real",
            "region_id": "R01",
            "source_sensor": "OHRC",
            "reference_sensor": "LROC",
            "detector": "SIFT",
            "model_type": "HOMOGRAPHY",
            "image_size": 256,
            "seed": 42
        }
        resp = self.client.post("/api/v1/registration", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("rmse", data["metrics"])

    def test_14_list_experiments_and_details(self):
        """Verify GET /api/v1/experiments and GET /api/v1/registration/{exp_id}."""
        resp = self.client.get("/api/v1/experiments")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("experiments", data)
        self.assertIn("total", data)

        if data["total"] > 0:
            exp_id = data["experiments"][0]["id"]
            resp_det = self.client.get(f"/api/v1/registration/{exp_id}")
            self.assertEqual(resp_det.status_code, 200)
            det = resp_det.json()
            self.assertEqual(det["experiment_id"], exp_id)
            self.assertIn("metrics", det)

    def test_15_metrics_endpoint(self):
        """Verify GET /api/v1/metrics returns aggregated run statistics."""
        resp = self.client.get("/api/v1/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("runs", data)
        self.assertIn("total", data)

    def test_16_control_points_endpoints(self):
        """Verify POST and GET /api/v1/control-points."""
        # Find latest experiment
        resp_exp = self.client.get("/api/v1/experiments")
        data_exp = resp_exp.json()
        if data_exp["total"] > 0:
            exp_id = data_exp["experiments"][0]["id"]
            # Create control point
            cp_payload = {
                "source_x": 120.0,
                "source_y": 140.0,
                "reference_x": 121.5,
                "reference_y": 139.8,
                "point_type": "MANUAL_CHECK",
                "annotator": "FastAPI_Tester",
                "confidence": 0.99
            }
            resp_cp_post = self.client.post(f"/api/v1/control-points?experiment_id={exp_id}", json=cp_payload)
            self.assertEqual(resp_cp_post.status_code, 200)
            res = resp_cp_post.json()
            self.assertEqual(res["status"], "SUCCESS")

            # Query control points
            resp_cp_get = self.client.get(f"/api/v1/control-points?experiment_id={exp_id}")
            self.assertEqual(resp_cp_get.status_code, 200)
            get_data = resp_cp_get.json()
            self.assertGreaterEqual(get_data["count"], 1)

    def test_17_artifacts_endpoint(self):
        """Verify GET /api/v1/artifacts/{exp_id}."""
        resp_exp = self.client.get("/api/v1/experiments")
        data_exp = resp_exp.json()
        if data_exp["total"] > 0:
            exp_id = data_exp["experiments"][0]["id"]
            resp_art = self.client.get(f"/api/v1/artifacts/{exp_id}")
            self.assertEqual(resp_art.status_code, 200)
            art_data = resp_art.json()
            self.assertEqual(art_data["experiment_id"], exp_id)
            self.assertIn("artifacts", art_data)

    def test_18_benchmark_run_endpoint(self):
        """Verify POST /api/v1/benchmark/run executes the benchmark runner."""
        resp = self.client.post("/api/v1/benchmark/run")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("success_rate_percentage", data)
        self.assertIn("case_results", data)
        self.assertEqual(data["passed_cases"], 7)

    def test_19_upload_endpoint(self):
        """Verify POST /api/v1/ingestion/upload accepts file archive upload."""
        sample_zip = SAMPLE_DATA_DIR / "ch2_ohrc_orbital_product.zip"
        if sample_zip.exists():
            with open(sample_zip, "rb") as f:
                files = {"file": ("test_fastapi_upload.zip", f, "application/zip")}
                resp = self.client.post("/api/v1/ingestion/upload?region_code=R01&sensor=OHRC", files=files)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("status", data)
            self.assertIn(data["status"], ["SUCCESS", "VALIDATED", "DUPLICATE_ACCEPTED", "ALREADY_CATALOGED"])


if __name__ == "__main__":
    unittest.main()

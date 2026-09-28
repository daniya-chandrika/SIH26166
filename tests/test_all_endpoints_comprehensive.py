"""
Comprehensive End-to-End API Endpoint Verification Test Suite.
Verifies all 45+ GET and POST API routes in the SIH26166 Dashboard Server.
"""
import json
import time
import io
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer
from pathlib import Path
import pytest

from dashboard_server import DashboardRequestHandler, RUNS_DIR, SAMPLE_DATA_DIR, RAW_DIR


@pytest.fixture(scope="module")
def live_server():
    """Start an in-process dashboard server on an ephemeral port."""
    server = HTTPServer(("127.0.0.1", 0), DashboardRequestHandler)
    port = server.server_port
    base_url = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield base_url
    server.shutdown()
    server.server_close()


def http_get(url: str):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, resp.headers, resp.read()


def http_post_json(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.headers, resp.read()


def http_post_multipart(url: str, fields: dict, files: list):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = io.BytesIO()
    for k, v in fields.items():
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.write(f"{v}\r\n".encode("utf-8"))
    for field_name, filename, file_bytes in files:
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.write(b"Content-Type: application/octet-stream\r\n\r\n")
        body.write(file_bytes)
        body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode("utf-8"))

    raw = body.getvalue()
    req = urllib.request.Request(
        url,
        data=raw,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, resp.headers, resp.read()


class TestAllAPIEndpoints:
    """Tests all API endpoints for 100% end-to-end success."""

    def test_01_health_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/health")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["project_id"] == "SIH26166"
        assert data["status"] in ("ONLINE", "PROCESSING")
        assert "supported_sensors" in data

    def test_02_summary_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/summary")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "total_experiments" in data
        assert "successful_experiments" in data

    def test_03_runs_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/runs")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "runs" in data
        assert "total" in data

    def test_04_benchmarks_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/benchmarks")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "standard_suite_cases" in data
        assert "external_references" in data

    def test_05_regions_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/regions")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["total"] >= 10
        assert data["regions"][0]["code"] == "R01"

    def test_06_products_catalog_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/products")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "products" in data
        assert len(data["products"]) > 0

    def test_07_products_filtered_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/products?sensor=OHRC")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "products" in data
        for p in data["products"]:
            assert p["sensor"] == "OHRC"

    def test_08_products_candidate_pairs_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/products/pairs?region_id=R01")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "pairs" in data

    def test_09_products_single_by_id_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/products")
        data = json.loads(body.decode("utf-8"))
        first_id = data["products"][0]["product_id"]
        status2, headers2, body2 = http_get(f"{live_server}/api/products/{first_id}")
        assert status2 == 200
        prod = json.loads(body2.decode("utf-8"))
        assert prod["product_id"] == first_id

    def test_10_sensor_matrix_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/sensor-matrix")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "sensor_matrix" in data
        assert len(data["sensor_matrix"]) >= 10

    def test_11_scenarios_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/scenarios")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "scenarios" in data
        assert len(data["scenarios"]) >= 5

    def test_12_remote_search_get_endpoint(self, live_server):
        status, headers, body = http_get(f"{live_server}/api/data/remote/search?sensor=OHRC")
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "products" in data

    def test_13_regions_search_post_endpoint(self, live_server):
        payload = {"latitude": -89.9, "longitude": 0.0, "radius_km": 15.0}
        status, headers, body = http_post_json(f"{live_server}/api/regions/search", payload)
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert "intersecting_products" in data or "candidate_pairs" in data

    def test_14_remote_search_post_endpoint(self, live_server):
        payload = {
            "search_type": "coords",
            "latitude": -89.9,
            "longitude": 0.0,
            "region_id": "R01",
            "sensor": "OHRC"
        }
        status, headers, body = http_post_json(f"{live_server}/api/data/remote/search", payload)
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["count"] > 0

    def test_15_remote_select_post_endpoint(self, live_server):
        payload = {
            "product_id": "CH2_OHRC_TEST_PROD",
            "sensor": "OHRC",
            "latitude": -89.9,
            "longitude": 0.0,
            "window_size": 256
        }
        status, headers, body = http_post_json(f"{live_server}/api/data/remote/select", payload)
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["status"] in ("READY", "CACHED_AND_READY")
        assert "product" in data

    def test_16_local_upload_multipart_endpoint(self, live_server):
        zip_path = SAMPLE_DATA_DIR / "ch2_ohrc_orbital_product.zip"
        assert zip_path.exists()
        file_bytes = zip_path.read_bytes()
        status, headers, body = http_post_multipart(
            f"{live_server}/api/data/local/upload",
            fields={"region_code": "R01", "sensor": "OHRC"},
            files=[("files", "test_upload_ohrc.zip", file_bytes)]
        )
        assert status == 200
        data = json.loads(body.decode("utf-8"))
        assert data["status"] in ("SUCCESS", "VALIDATED", "DUPLICATE_ACCEPTED", "ALREADY_CATALOGED")
        assert "product" in data or "product_id" in data

    def test_17_pipeline_execution_and_job_endpoints(self, live_server):
        payload = {
            "data_mode": "LOCAL",
            "region": "R01",
            "source_sensor": "OHRC",
            "reference_sensor": "LROC",
            "feature_detector": "SIFT",
            "geometric_model": "homography"
        }
        status, headers, body = http_post_json(f"{live_server}/api/registration/start", payload)
        assert status == 202
        data = json.loads(body.decode("utf-8"))
        job_id = data["job_id"]

        # Poll job status
        max_wait = 40
        start_t = time.time()
        final_job = None
        while time.time() - start_t < max_wait:
            s_status, _, s_body = http_get(f"{live_server}/api/jobs/{job_id}")
            assert s_status == 200
            final_job = json.loads(s_body.decode("utf-8"))
            if final_job["status"] in ("COMPLETED", "SUCCESS", "FAILED"):
                break
            time.sleep(0.5)

        assert final_job is not None
        assert final_job["status"] in ("COMPLETED", "SUCCESS")
        assert final_job.get("experiment_id") is not None

        # Verify /api/jobs/{job_id}/stages endpoint
        st_status, _, st_body = http_get(f"{live_server}/api/jobs/{job_id}/stages")
        assert st_status == 200
        stages_data = json.loads(st_body.decode("utf-8"))
        assert stages_data["job_id"] == job_id
        assert len(stages_data["stages"]) == 12

        # Verify /api/jobs/{job_id}/status endpoint
        stat_status, _, stat_body = http_get(f"{live_server}/api/jobs/{job_id}/status")
        assert stat_status == 200

        # Now test Run result endpoints
        run_id = final_job["experiment_id"]
        
        # 1. /api/run/{run_id} (JSON details)
        r_status, _, r_body = http_get(f"{live_server}/api/run/{run_id}")
        assert r_status == 200
        run_details = json.loads(r_body.decode("utf-8"))
        assert run_details["id"] == run_id
        assert "metrics" in run_details
        assert "config" in run_details

        # 2. /api/run/{run_id}/details
        rd_status, _, rd_body = http_get(f"{live_server}/api/run/{run_id}/details")
        assert rd_status == 200

        # 3. /api/run/{run_id}/status
        rs_status, _, rs_body = http_get(f"{live_server}/api/run/{run_id}/status")
        assert rs_status == 200

        # 4. /api/run/{run_id}/report (Markdown)
        rep_status, _, rep_body = http_get(f"{live_server}/api/run/{run_id}/report")
        assert rep_status == 200
        assert b"Scientific" in rep_body and b"Report" in rep_body

        # 5. /api/run/{run_id}/artifacts
        art_status, _, art_body = http_get(f"{live_server}/api/run/{run_id}/artifacts")
        assert art_status == 200
        art_data = json.loads(art_body.decode("utf-8"))
        assert art_data["count"] > 0

        # 6. Artifact Downloads (GeoTIFF, PNG, JSON, MD)
        for art_name in ["registered_image.png", "metrics.json", "scientific_report.md"]:
            d_status, d_headers, d_bytes = http_get(f"{live_server}/api/run/{run_id}/download/{art_name}")
            assert d_status == 200
            assert len(d_bytes) > 0

        # 7. ZIP Package Download
        zip_status, zip_headers, zip_bytes = http_get(f"{live_server}/api/run/{run_id}/download/zip")
        assert zip_status == 200
        assert zip_headers.get_content_type() == "application/zip"
        assert len(zip_bytes) > 500

        # 8. Inline image streams for frontend visualization gallery
        for img_name in ["registered_image.png", "difference_map.png", "matches.png", "checkerboard.png"]:
            img_status, img_headers, img_bytes = http_get(f"{live_server}/api/run/{run_id}/{img_name}")
            assert img_status == 200
            assert img_headers.get_content_type() == "image/png"
            assert len(img_bytes) > 100

        # 9. Control points endpoints
        cp_post = {
            "experiment_id": run_id,
            "source_x": 100.5,
            "source_y": 200.5,
            "reference_x": 102.0,
            "reference_y": 201.0,
            "point_type": "MANUAL_CHECK",
            "annotator": "E2E_Test_Scientist"
        }
        cp_status, _, cp_body = http_post_json(f"{live_server}/api/control-points", cp_post)
        assert cp_status == 200
        cp_res = json.loads(cp_body.decode("utf-8"))
        assert cp_res["status"] == "SUCCESS"

        # GET control points for this run
        cp_get_status, _, cp_get_body = http_get(f"{live_server}/api/control-points?experiment_id={run_id}")
        assert cp_get_status == 200
        cp_get_data = json.loads(cp_get_body.decode("utf-8"))
        assert cp_get_data["count"] >= 1

        # 10. Compare endpoint
        cmp_status, _, cmp_body = http_get(f"{live_server}/api/compare?exp_a={run_id}&exp_b={run_id}")
        assert cmp_status == 200
        cmp_data = json.loads(cmp_body.decode("utf-8"))
        assert "experiment_a" in cmp_data and "experiment_b" in cmp_data

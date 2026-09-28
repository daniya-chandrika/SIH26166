"""
End-to-End Verification Test Script for SIH26166 Dashboard Server
Tests Mode A (Local Upload), Mode B (Remote Search), 12-Stage Pipeline State Machine,
and All Download Artifacts Endpoints over live HTTP.
"""

import sys
import os
import io
import time
import zipfile
import json
import threading
import urllib.request
import urllib.parse
from pathlib import Path
from http.server import HTTPServer
import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard_server import DashboardRequestHandler, JOB_MANAGER

TEST_PORT = 8089
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"
_server_instance = None

@pytest.fixture(scope="module", autouse=True)
def live_server():
    global _server_instance
    server = HTTPServer(("127.0.0.1", TEST_PORT), DashboardRequestHandler)
    _server_instance = server
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.3)
    yield
    server.shutdown()
    server.server_close()

def http_get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "SIH26166-TestClient"})
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read(), resp.headers

def http_post_json(path, data):
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "SIH26166-TestClient"})
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def http_post_multipart(path, fields, files):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = io.BytesIO()
    
    for k, v in fields.items():
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.write(f"{v}\r\n".encode("utf-8"))
        
    for name, fname, content in files:
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(f'Content-Disposition: form-data; name="{name}"; filename="{fname}"\r\n'.encode("utf-8"))
        body.write(b"Content-Type: application/octet-stream\r\n\r\n")
        body.write(content)
        body.write(b"\r\n")
        
    body.write(f"--{boundary}--\r\n".encode("utf-8"))
    
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body.getvalue(),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "SIH26166-TestClient"
        }
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class TestEndToEndModesAndDownloads:
    """Complete End-to-End Test Suite for Mode A, Mode B, and Artifact Downloads."""
    
    _created_run_id = None

    def test_01_system_health(self):
        status, body, headers = http_get("/api/health")
        assert status == 200, f"Health check failed: {status}"
        data = json.loads(body.decode("utf-8"))
        assert data["status"] in ["ONLINE", "HEALTHY", "PROCESSING"]
        assert "supported_modes" in data
        assert "MODE_A_LOCAL" in data["supported_modes"]
        assert "MODE_B_REMOTE" in data["supported_modes"]

    def test_02_mode_a_local_upload_and_pipeline(self):
        dummy_lbl = b"PDS_VERSION_ID = PDS3\nRECORD_TYPE = FIXED_LENGTH\nMISSION_NAME = 'CHANDRAYAAN-2'\nINSTRUMENT_HOST_NAME = 'CH2'\nINSTRUMENT_ID = 'OHRC'\nOBJECT = IMAGE\n  LINES = 512\n  LINE_SAMPLES = 512\n  SAMPLE_BITS = 16\nEND_OBJECT = IMAGE\nEND\n"
        
        status, upload_data = http_post_multipart(
            "/api/data/local/upload",
            fields={"region_code": "R01", "source_sensor": "OHRC"},
            files=[("files", "test_ohrc_orbital.lbl", dummy_lbl)]
        )
        assert status == 200, f"Upload failed: {status}"
        prod_id = upload_data.get("product_id") or upload_data.get("product", {}).get("product_id") or "test_ohrc_orbital"
        sensor = upload_data.get("sensor") or upload_data.get("product", {}).get("sensor") or "OHRC"

        status, job_info = http_post_json("/api/registration/start", {
            "data_mode": "LOCAL",
            "source_product": prod_id,
            "region": "R01",
            "source_sensor": "OHRC",
            "reference_sensor": "LROC",
            "feature_detector": "SIFT",
            "geometric_model": "homography"
        })
        assert status in [200, 202], f"Job start failed: {job_info}"
        job_id = job_info["job_id"]

        # Poll until job finishes
        max_wait = 60
        start_time = time.time()
        final_job = None
        
        while time.time() - start_time < max_wait:
            st, body, _ = http_get(f"/api/jobs/{job_id}")
            assert st == 200
            job_state = json.loads(body.decode("utf-8"))
            job_st = job_state.get("status")
            
            if job_st in ["COMPLETED", "SUCCESS", "FAILED"]:
                final_job = job_state
                break
            time.sleep(0.4)

        assert final_job is not None, "Job timed out"
        assert final_job["status"] in ["COMPLETED", "SUCCESS"], f"Job failed: {final_job.get('error')}"

        # Verify all 12 stages executed
        stages = final_job.get("stages", [])
        assert len(stages) == 12, f"Expected 12 stages, got {len(stages)}"
        for st_data in (stages if isinstance(stages, list) else stages.values()):
            st_num = st_data["stage_number"]
            assert st_data["status"] == "COMPLETED", f"Stage {st_num} status is {st_data['status']}"
            dur = st_data.get("duration_s", st_data.get("duration", 0))
            assert dur >= 0

        run_id = final_job.get("run_id") or final_job.get("experiment_id")
        assert run_id is not None, "Run ID was not generated"
        TestEndToEndModesAndDownloads._created_run_id = run_id

    def test_03_mode_b_remote_search_and_select(self):
        status, search_data = http_post_json("/api/data/remote/search", {
            "search_type": "coords",
            "latitude": -89.9,
            "longitude": 0.0,
            "region_name": "Shackleton Crater",
            "region_id": "R01",
            "provider": "ALL",
            "sensor": "OHRC",
            "max_gsd": 5.0
        })
        assert status == 200, f"Remote search failed: {search_data}"
        products = search_data.get("products", [])
        assert len(products) > 0, "No remote products found"
        first_prod = products[0]

        # Select product
        status, select_data = http_post_json("/api/data/remote/select", {
            "product_id": first_prod["product_id"],
            "sensor": first_prod["sensor"],
            "latitude": -89.9,
            "longitude": 0.0
        })
        assert status == 200, f"Remote select failed: {select_data}"
        assert select_data["status"] in ["CACHED_AND_READY", "READY", "SUCCESS"]

    def test_04_all_artifact_downloads(self):
        run_id = TestEndToEndModesAndDownloads._created_run_id
        assert run_id is not None, "No run ID available for download testing"

        artifacts = [
            "registered_image.tif",
            "registered_image.png",
            "reference_image.tif",
            "valid_mask.png",
            "difference_map.png",
            "checkerboard.png",
            "matches.png",
            "scientific_report.md",
            "scientific_report.json",
            "metrics.json",
        ]

        for fname in artifacts:
            url = f"/api/run/{run_id}/download/{fname}"
            st, content, headers = http_get(url)
            assert st == 200, f"Download failed for {fname}: status {st}"
            assert len(content) > 0, f"Downloaded empty content for {fname}"

        # Test ZIP Bundle download
        st, zip_content, headers = http_get(f"/api/run/{run_id}/download/zip")
        assert st == 200, f"ZIP download failed: {st}"
        assert len(zip_content) > 0, "Downloaded empty ZIP"

        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            namelist = zf.namelist()
            assert len(namelist) >= 5, "ZIP bundle missing expected artifacts"


if __name__ == "__main__":
    pytest.main(["-v", __file__])

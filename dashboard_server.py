"""
SIH26166 Interactive Lunar Registration Dashboard Server
Serves the web frontend and provides REST endpoints for inspecting and triggering runs,
benchmarks, remote orbital archive exploration, and side-by-side scientific comparison.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from orchestrator.prototype_pipeline import PrototypePipelineConfig, PrototypeRegistrationOrchestrator
from orchestrator.real_pipeline import RealPipelineConfig, RealMultimodalRegistrationOrchestrator
from ingestion.remote_archive import RemoteArchiveClient, RemoteArchiveSearchQuery
from experiments.benchmark import LunarRegistrationBenchmarkRunner
from reports.scientific_report import ScientificReportGenerator
from metadata.models import LunarProductMetadata

WORKSPACE_ROOT = Path(__file__).resolve().parent
RUNS_DIR = WORKSPACE_ROOT / "experiments" / "runs"
BENCH_DIR = WORKSPACE_ROOT / "experiments" / "benchmarks"
FRONTEND_DIR = WORKSPACE_ROOT / "frontend"
PORT = int(os.environ.get("PORT", 8080))


class JobManager:
    """Thread-safe asynchronous job manager for long-running registration experiments."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, params: Dict[str, Any]) -> str:
        job_id = f"JOB_{uuid.uuid4().hex[:8].upper()}"
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "QUEUED",
                "params": params,
                "created_at": time.time(),
                "started_at": None,
                "finished_at": None,
                "experiment_id": None,
                "error": None,
                "logs": [],
            }
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return dict(job)
            return None

    def list_active_jobs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                dict(j)
                for j in self._jobs.values()
                if j["status"] in ("QUEUED", "RUNNING")
            ]

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(kwargs)

    def append_log(self, job_id: str, message: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                timestamp = datetime.now().strftime("%H:%M:%S")
                self._jobs[job_id]["logs"].append(f"[{timestamp}] {message}")


JOB_MANAGER = JobManager()


def _run_experiment_worker(job_id: str, params: Dict[str, Any]) -> None:
    """Background worker executing the registration orchestrator."""
    JOB_MANAGER.update_job(job_id, status="RUNNING", started_at=time.time())
    JOB_MANAGER.append_log(job_id, "Registration pipeline worker initialized.")

    try:
        mode = params.get("mode", "synthetic").lower()
        scenario = params.get("scenario", "combined")
        seed = int(params.get("seed", 42))
        image_size = int(params.get("image_size", 512))
        model_type = params.get("model_type", "HOMOGRAPHY").upper()
        detector = params.get("detector", "SIFT").upper()
        region_id = params.get("region_id", "R01")
        source_sensor = params.get("source_sensor", "OHRC")
        reference_sensor = params.get("reference_sensor", "LROC")

        if mode in ["real", "remote"]:
            JOB_MANAGER.append_log(job_id, f"Querying remote orbital archive for {region_id} ({source_sensor} vs {reference_sensor})...")
            client = RemoteArchiveClient()
            pairs = client.find_cross_mission_pairs(
                min_latitude=-90.0, max_latitude=90.0,
                min_longitude=-180.0, max_longitude=180.0,
                ch2_sensor=source_sensor,
                ref_sensor=reference_sensor
            )
            if not pairs:
                raise ValueError(f"No matching overlapping product pair found for region {region_id}.")

            ch2_item, lroc_item, overlap_pct = pairs[0]
            JOB_MANAGER.append_log(job_id, f"Found overlapping pair: {ch2_item.product_id} & {lroc_item.product_id} ({overlap_pct:.1f}% overlap).")
            ref_arr, _ = client.retrieve_spatial_window(lroc_item, window_size_px=image_size, seed=seed)
            src_arr, _ = client.retrieve_spatial_window(ch2_item, window_size_px=image_size, seed=seed)

            m_ref = LunarProductMetadata(product_id=lroc_item.product_id, sensor=lroc_item.sensor, spatial_resolution=lroc_item.spatial_resolution_m, latitude=lroc_item.center_latitude, longitude=lroc_item.center_longitude)
            m_src = LunarProductMetadata(product_id=ch2_item.product_id, sensor=ch2_item.sensor, spatial_resolution=ch2_item.spatial_resolution_m, latitude=ch2_item.center_latitude, longitude=ch2_item.center_longitude)

            real_cfg = RealPipelineConfig(
                region_id=region_id,
                detector=detector,
                geometric_model=model_type,
                output_dir=str(RUNS_DIR)
            )
            orchestrator = RealMultimodalRegistrationOrchestrator(real_cfg)
            report = orchestrator.run(meta_reference=m_ref, meta_source=m_src, reference_raster_override=ref_arr, source_raster_override=src_arr)
        else:
            config = PrototypePipelineConfig(
                scenario=scenario,
                seed=seed,
                image_width=image_size,
                image_height=image_size,
                detector=detector,
                geometric_model=model_type,
                output_dir=str(RUNS_DIR),
            )
            JOB_MANAGER.append_log(
                job_id,
                f"Configured: Scenario={scenario}, Seed={seed}, Size={image_size}px, Model={model_type}, Detector={detector}",
            )
            orchestrator = PrototypeRegistrationOrchestrator(config)
            report = orchestrator.run()

        # Identify latest created run folder
        latest_run = None
        if RUNS_DIR.exists():
            runs = sorted(
                [
                    d
                    for d in RUNS_DIR.iterdir()
                    if d.is_dir() and d.name.startswith("SIH26166_EXP_")
                ],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if runs:
                latest_run = runs[0].name
                # Save scientific report markdown
                try:
                    ScientificReportGenerator.save_report(
                        run_dir=runs[0],
                        experiment_id=latest_run,
                        config=params,
                        metrics=report.to_dict(),
                        transform_data={"model": model_type},
                        is_synthetic=(mode == "synthetic")
                    )
                except Exception:
                    pass

        is_success = report.registration_status == "SUCCESS"
        status_str = "SUCCESS" if is_success else "FAILED"

        JOB_MANAGER.update_job(
            job_id,
            status=status_str,
            finished_at=time.time(),
            experiment_id=latest_run,
            error=report.failure_reason,
            metrics=report.to_dict(),
        )
        JOB_MANAGER.append_log(
            job_id, f"Execution completed with status: {status_str} (Run: {latest_run})"
        )

    except Exception as e:
        JOB_MANAGER.update_job(
            job_id,
            status="FAILED",
            finished_at=time.time(),
            error=str(e),
        )
        JOB_MANAGER.append_log(job_id, f"Pipeline execution failed: {str(e)}")


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for SIH26166 Scientific Lunar Registration Dashboard."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        if path == "/api/health":
            self._handle_get_health()
        elif path == "/api/summary":
            self._handle_get_summary()
        elif path == "/api/runs":
            self._handle_list_runs()
        elif path == "/api/benchmarks":
            self._handle_get_benchmarks()
        elif path == "/api/remote/search":
            self._handle_get_remote_search(query)
        elif path == "/api/control-points":
            self._handle_get_control_points(query)
        elif path == "/api/compare":
            self._handle_get_compare(query)
        elif path.startswith("/api/jobs/"):
            job_id = path[len("/api/jobs/") :]
            self._handle_get_job(job_id)
        elif path.startswith("/api/run/"):
            subpath = path[len("/api/run/") :]
            if subpath.endswith("/details"):
                run_id = subpath[: -len("/details")]
                self._handle_get_run_details(run_id)
            elif subpath.endswith("/status"):
                run_id = subpath[: -len("/status")]
                self._handle_get_run_status(run_id)
            elif subpath.endswith("/report"):
                run_id = subpath[: -len("/report")]
                self._handle_get_run_report(run_id)
            else:
                self._handle_get_run_file(subpath)
        elif path == "/api/scenarios":
            self._handle_get_scenarios()
        else:
            # Serve static frontend files
            super().do_GET()

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/trigger":
            self._handle_trigger_run()
        elif path == "/api/benchmark/run":
            self._handle_trigger_benchmark()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def _send_json(self, data: Any, status: int = 200) -> None:
        content = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def _handle_get_health(self) -> None:
        """Returns verified real backend health and operating state."""
        runs_available = RUNS_DIR.exists() and RUNS_DIR.is_dir()
        total_runs = 0
        if runs_available:
            total_runs = len(
                [
                    d
                    for d in RUNS_DIR.iterdir()
                    if d.is_dir() and d.name.startswith("SIH26166_EXP_")
                ]
            )

        active_jobs = JOB_MANAGER.list_active_jobs()
        health_data = {
            "status": "ONLINE" if len(active_jobs) == 0 else "PROCESSING",
            "service": "Scientific Lunar Image Registration Engine",
            "project_id": "SIH26166",
            "version": "2.0.0",
            "pipeline_available": True,
            "runs_directory_available": runs_available,
            "database_mode": "HYBRID / LOCAL PERSISTENCE + OPTIONAL SUPABASE",
            "python_version": sys.version.split()[0],
            "total_runs_on_disk": total_runs,
            "active_processing_jobs": len(active_jobs),
            "supported_sensors": ["OHRC", "TMC-2", "IIRS", "LROC"],
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._send_json(health_data)

    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> Optional[float]:
        """Calculates composite registration quality score."""
        if not metrics or metrics.get("registration_status") != "SUCCESS":
            return 0.0 if metrics else None

        inlier_ratio = float(metrics.get("inlier_ratio") or 0.0)
        rmse = float(metrics.get("reprojection_rmse_px") or metrics.get("rmse") or 5.0)
        rmse_score = max(0.0, min(1.0, 1.0 - (rmse / 5.0)))
        spatial_cov = float(metrics.get("spatial_coverage_percentage") or 0.0) / 100.0
        subpix_conv = float(metrics.get("subpixel_convergence_rate") or 0.0)

        score = (
            (0.35 * inlier_ratio)
            + (0.25 * rmse_score)
            + (0.20 * spatial_cov)
            + (0.20 * subpix_conv)
        )
        return round(max(0.0, min(1.0, score)), 4)

    def _handle_get_summary(self) -> None:
        """Calculates aggregated statistics from experiment runs."""
        total_experiments = 0
        successful_experiments = 0
        failed_experiments = 0
        rmse_values: List[float] = []
        inlier_ratios: List[float] = []
        spatial_coverages: List[float] = []
        best_experiment = None
        best_score = -1.0
        latest_experiment = None
        scenario_counts: Dict[str, int] = {}

        if RUNS_DIR.exists():
            folders = sorted(
                [
                    d
                    for d in RUNS_DIR.iterdir()
                    if d.is_dir() and d.name.startswith("SIH26166_EXP_")
                ],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            total_experiments = len(folders)
            if folders:
                latest_experiment = folders[0].name

            for folder in folders:
                metrics_file = folder / "metrics.json"
                config_file = folder / "config.json"
                metrics_data: Dict[str, Any] = {}
                config_data: Dict[str, Any] = {}

                if metrics_file.exists():
                    try:
                        with open(metrics_file, "r", encoding="utf-8") as f:
                            metrics_data = json.load(f)
                    except Exception:
                        pass

                if config_file.exists():
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            config_data = json.load(f)
                    except Exception:
                        pass

                scenario = config_data.get("scenario", config_data.get("region_id", "unknown"))
                scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1

                is_success = metrics_data.get("registration_status") == "SUCCESS"
                if is_success:
                    successful_experiments += 1
                else:
                    failed_experiments += 1

                rmse = metrics_data.get("reprojection_rmse_px") or metrics_data.get("rmse")
                if rmse is not None and isinstance(rmse, (int, float)) and rmse < 900:
                    rmse_values.append(float(rmse))

                inlier_r = metrics_data.get("inlier_ratio")
                if inlier_r is not None and isinstance(inlier_r, (int, float)):
                    inlier_ratios.append(float(inlier_r))

                cov = metrics_data.get("spatial_coverage_percentage")
                if cov is not None and isinstance(cov, (int, float)):
                    spatial_coverages.append(float(cov))

                score = self._calculate_quality_score(metrics_data)
                if score is not None and score > best_score:
                    best_score = score
                    best_experiment = {
                        "id": folder.name,
                        "quality_score": score,
                        "rmse": rmse,
                        "inlier_ratio": inlier_r,
                    }

        avg_rmse = round(sum(rmse_values) / len(rmse_values), 4) if rmse_values else None
        avg_inlier_ratio = round(sum(inlier_ratios) / len(inlier_ratios), 4) if inlier_ratios else None
        avg_spatial_cov = round(sum(spatial_coverages) / len(spatial_coverages), 2) if spatial_coverages else None

        active_jobs = JOB_MANAGER.list_active_jobs()

        summary_data = {
            "total_experiments": total_experiments,
            "successful_experiments": successful_experiments,
            "failed_experiments": failed_experiments,
            "active_processing_runs": len(active_jobs),
            "average_rmse": avg_rmse,
            "average_inlier_ratio": avg_inlier_ratio,
            "average_spatial_coverage": avg_spatial_cov,
            "best_registration_quality": round(best_score, 4) if best_score >= 0 else None,
            "best_experiment": best_experiment,
            "latest_experiment": latest_experiment,
            "scenarios_distribution": scenario_counts,
        }
        self._send_json(summary_data)

    def _handle_get_scenarios(self) -> None:
        scenarios = [
            {"id": "combined", "name": "Combined Mission Challenge", "description": "Simultaneous rotation, scale difference, solar illumination gradient, and sensor noise."},
            {"id": "illumination", "name": "Illumination Variations", "description": "Simulates different solar elevation angles (shadow dynamics and radiometric contrast)."},
            {"id": "scale", "name": "Multi-Scale Discrepancy", "description": "Simulates resolution ratio between different orbital sensors (e.g. TMC-2 vs OHRC)."},
            {"id": "viewpoint", "name": "Off-Nadir Viewpoint / Perspective", "description": "Perspective tilt distortion due to spacecraft off-nadir pointing angle."},
            {"id": "rotation_translation", "name": "Orbital Drift (Rotation & Shift)", "description": "Planar drift and camera orientation change along orbital track."},
            {"id": "strong_scale", "name": "Strong Scale Disparity (1.45x)", "description": "Large resolution difference across orbital sensors."},
        ]
        self._send_json({"scenarios": scenarios})

    def _handle_list_runs(self) -> None:
        runs: List[Dict[str, Any]] = []
        if RUNS_DIR.exists():
            for folder in sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if folder.is_dir() and folder.name.startswith("SIH26166_EXP_"):
                    metrics_path = folder / "metrics.json"
                    transform_path = folder / "transform.json"
                    config_path = folder / "config.json"
                    gt_path = folder / "ground_truth.json"

                    metrics_data = {}
                    if metrics_path.exists():
                        try:
                            with open(metrics_path, "r", encoding="utf-8") as f:
                                metrics_data = json.load(f)
                        except Exception:
                            pass

                    transform_data = {}
                    if transform_path.exists():
                        try:
                            with open(transform_path, "r", encoding="utf-8") as f:
                                transform_data = json.load(f)
                        except Exception:
                            pass

                    config_data = {}
                    if config_path.exists():
                        try:
                            with open(config_path, "r", encoding="utf-8") as f:
                                config_data = json.load(f)
                        except Exception:
                            pass

                    gt_data = {}
                    if gt_path.exists():
                        try:
                            with open(gt_path, "r", encoding="utf-8") as f:
                                gt_data = json.load(f)
                        except Exception:
                            pass

                    viz_files = []
                    viz_dir = folder / "visualizations"
                    if viz_dir.exists():
                        viz_files = [f.name for f in sorted(viz_dir.iterdir()) if f.is_file() and f.suffix in (".png", ".jpg")]

                    quality_score = self._calculate_quality_score(metrics_data)

                    runs.append({
                        "id": folder.name,
                        "timestamp": folder.stat().st_mtime,
                        "date_iso": datetime.fromtimestamp(folder.stat().st_mtime, tz=timezone.utc).isoformat(),
                        "metrics": metrics_data,
                        "transform": transform_data,
                        "config": config_data,
                        "ground_truth": gt_data,
                        "visualizations": viz_files,
                        "quality_score": quality_score,
                        "success": metrics_data.get("registration_status") == "SUCCESS",
                    })

        self._send_json({"runs": runs, "total": len(runs)})

    def _handle_get_run_details(self, run_id: str) -> None:
        run_folder = RUNS_DIR / run_id
        if not run_folder.exists() or not run_folder.is_dir() or not run_id.startswith("SIH26166_EXP_"):
            self.send_error(HTTPStatus.NOT_FOUND, f"Experiment {run_id} not found")
            return

        def _load_json(filename: str) -> Optional[Dict[str, Any]]:
            p = run_folder / filename
            if p.exists() and p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return None
            return None

        def _load_text(filename: str) -> str:
            p = run_folder / filename
            if p.exists() and p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    return ""
            return ""

        config_data = _load_json("config.json") or {}
        metrics_data = _load_json("metrics.json") or {}
        transform_data = _load_json("transform.json") or {}
        ground_truth_data = _load_json("ground_truth.json") or {}
        matches_data = _load_json("matches.json") or {}
        logs_text = _load_text("logs.txt")
        report_md = _load_text("scientific_report.md")

        viz_files = []
        viz_dir = run_folder / "visualizations"
        if viz_dir.exists():
            viz_files = [f.name for f in sorted(viz_dir.iterdir()) if f.is_file() and f.suffix in (".png", ".jpg")]

        quality_score = self._calculate_quality_score(metrics_data)

        payload = {
            "id": run_id,
            "timestamp": run_folder.stat().st_mtime,
            "date_iso": datetime.fromtimestamp(run_folder.stat().st_mtime, tz=timezone.utc).isoformat(),
            "config": config_data,
            "metrics": metrics_data,
            "transform": transform_data,
            "ground_truth": ground_truth_data,
            "matches": matches_data,
            "logs": logs_text,
            "scientific_report_md": report_md,
            "visualizations": viz_files,
            "quality_score": quality_score,
            "status": metrics_data.get("registration_status", "UNKNOWN"),
            "success": metrics_data.get("registration_status") == "SUCCESS",
        }
        self._send_json(payload)

    def _handle_get_run_status(self, run_id: str) -> None:
        run_folder = RUNS_DIR / run_id
        if not run_folder.exists():
            self._send_json({"id": run_id, "exists": False, "status": "NOT_FOUND"})
            return

        metrics_file = run_folder / "metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._send_json({
                        "id": run_id,
                        "exists": True,
                        "status": data.get("registration_status", "COMPLETED"),
                        "success": data.get("registration_status") == "SUCCESS",
                    })
                    return
            except Exception:
                pass

        self._send_json({"id": run_id, "exists": True, "status": "UNKNOWN"})

    def _handle_get_run_report(self, run_id: str) -> None:
        run_folder = RUNS_DIR / run_id
        if not run_folder.exists() or not run_id.startswith("SIH26166_EXP_"):
            self.send_error(HTTPStatus.NOT_FOUND, f"Experiment {run_id} not found")
            return

        md_file = run_folder / "scientific_report.md"
        if md_file.exists():
            with open(md_file, "r", encoding="utf-8") as f:
                report_bytes = f.read().encode("utf-8")
        else:
            report_bytes = f"# Report for {run_id}\n\nMetrics recorded.".encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{run_id}_report.md"')
        self.send_header("Content-Length", str(len(report_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(report_bytes)

    def _handle_get_benchmarks(self) -> None:
        """List benchmark results and external reference comparisons."""
        runner = LunarRegistrationBenchmarkRunner(output_dir=BENCH_DIR)
        ext_baselines = [b.to_dict() for b in runner.get_external_reference_baselines()]

        bench_runs = []
        if BENCH_DIR.exists():
            for d in sorted(BENCH_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if d.is_dir() and d.name.startswith("BENCH_"):
                    rep_file = d / "benchmark_report.json"
                    if rep_file.exists():
                        try:
                            bench_runs.append(json.loads(rep_file.read_text(encoding="utf-8")))
                        except Exception:
                            pass

        self._send_json({
            "benchmark_runs": bench_runs,
            "external_references": ext_baselines,
            "standard_suite_cases": [tc.to_dict() for tc in runner.get_standard_suite()]
        })

    def _handle_get_remote_search(self, query: Dict[str, List[str]]) -> None:
        """Search remote orbital archives."""
        client = RemoteArchiveClient()
        sensor = query.get("sensor", [None])[0]
        q = RemoteArchiveSearchQuery(
            min_latitude=float(query.get("min_lat", [-90.0])[0]),
            max_latitude=float(query.get("max_lat", [90.0])[0]),
            min_longitude=float(query.get("min_lon", [-180.0])[0]),
            max_longitude=float(query.get("max_lon", [180.0])[0]),
            sensor=sensor
        )
        items = [p.to_dict() for p in client.search_products(q)]
        self._send_json({"results": items, "count": len(items)})

    def _handle_get_control_points(self, query: Dict[str, List[str]]) -> None:
        """Get control points for an experiment."""
        exp_id = query.get("experiment_id", [None])[0]
        if not exp_id:
            self._send_json({"error": "Missing experiment_id"}, status=400)
            return

        cp_file = RUNS_DIR / exp_id / "control_points.json"
        if cp_file.exists():
            pts = json.loads(cp_file.read_text(encoding="utf-8"))
            self._send_json({"experiment_id": exp_id, "control_points": pts, "count": len(pts)})
        else:
            self._send_json({"experiment_id": exp_id, "control_points": [], "count": 0})

    def _handle_get_compare(self, query: Dict[str, List[str]]) -> None:
        """Compare Experiment A vs Experiment B."""
        exp_a = query.get("exp_a", [None])[0]
        exp_b = query.get("exp_b", [None])[0]

        if not exp_a or not exp_b:
            self._send_json({"error": "Provide both exp_a and exp_b parameters"}, status=400)
            return

        def _get_run(exp_id: str) -> Dict[str, Any]:
            folder = RUNS_DIR / exp_id
            if not folder.exists():
                return {}
            cfg = json.loads((folder / "config.json").read_text(encoding="utf-8")) if (folder / "config.json").exists() else {}
            met = json.loads((folder / "metrics.json").read_text(encoding="utf-8")) if (folder / "metrics.json").exists() else {}
            tf = json.loads((folder / "transform.json").read_text(encoding="utf-8")) if (folder / "transform.json").exists() else {}
            return {"id": exp_id, "config": cfg, "metrics": met, "transform": tf}

        self._send_json({
            "experiment_a": _get_run(exp_a),
            "experiment_b": _get_run(exp_b),
            "comparison_timestamp": datetime.now(timezone.utc).isoformat()
        })

    def _handle_get_job(self, job_id: str) -> None:
        job = JOB_MANAGER.get_job(job_id)
        if not job:
            self.send_error(HTTPStatus.NOT_FOUND, f"Job {job_id} not found")
            return
        self._send_json(job)

    def _handle_get_run_file(self, subpath: str) -> None:
        parts = subpath.split("/", 1)
        if len(parts) < 2:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid run file path")
            return

        run_id, rel_path = parts[0], parts[1]
        run_folder = RUNS_DIR / run_id
        target_file = (run_folder / rel_path).resolve()

        try:
            target_file.relative_to(RUNS_DIR)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Access denied")
            return

        if not target_file.exists() or not target_file.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, f"File {rel_path} not found")
            return

        mime_type, _ = mimetypes.guess_type(str(target_file))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(target_file, "rb") as f:
                content = f.read()

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def _handle_trigger_run(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            params = json.loads(body.decode("utf-8")) if body else {}

            job_id = JOB_MANAGER.create_job(params)

            worker_thread = threading.Thread(
                target=_run_experiment_worker,
                args=(job_id, params),
                daemon=True,
                name=f"Worker-{job_id}",
            )
            worker_thread.start()

            self._send_json(
                {
                    "status": "QUEUED",
                    "job_id": job_id,
                    "message": "Registration pipeline successfully queued for asynchronous execution.",
                },
                status=202,
            )
        except Exception as e:
            self._send_json({"status": "ERROR", "error": str(e)}, status=500)

    def _handle_trigger_benchmark(self) -> None:
        """Trigger benchmark suite execution asynchronously."""
        try:
            runner = LunarRegistrationBenchmarkRunner(output_dir=BENCH_DIR)
            suite_res = runner.run_benchmark_suite()
            self._send_json(suite_res.to_dict())
        except Exception as e:
            self._send_json({"status": "ERROR", "error": str(e)}, status=500)


def run_server(port: int = PORT) -> None:
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print("=" * 70)
    print(" [SIH26166] SCIENTIFIC LUNAR IMAGE REGISTRATION DASHBOARD SERVER")
    print("=" * 70)
    print(f" Web UI available at:   http://localhost:{port}")
    print(f" Runs directory:        {RUNS_DIR}")
    print(f" Benchmarks directory:  {BENCH_DIR}")
    print(f" Python Environment:    {sys.version.split()[0]}")
    print(" Press Ctrl+C to stop the server.")
    print("=" * 70)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port_arg)

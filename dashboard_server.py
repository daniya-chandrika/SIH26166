"""
SIH26166 Interactive Lunar Registration Dashboard Server
Serves the web frontend and provides REST endpoints for inspecting and triggering runs.
Preserves existing scientific architecture while adding async execution and rich telemetry.
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

WORKSPACE_ROOT = Path(__file__).resolve().parent
RUNS_DIR = WORKSPACE_ROOT / "experiments" / "runs"
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
    """Background worker executing the existing 12-stage PrototypeRegistrationOrchestrator."""
    JOB_MANAGER.update_job(job_id, status="RUNNING", started_at=time.time())
    JOB_MANAGER.append_log(job_id, "Registration pipeline worker initialized.")

    try:
        scenario = params.get("scenario", "combined")
        seed = int(params.get("seed", 42))
        image_size = int(params.get("image_size", 512))
        model_type = params.get("model_type", "HOMOGRAPHY").upper()
        detector = params.get("detector", "SIFT").upper()
        subpixel = bool(params.get("refine_subpixel", True))

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

        if path == "/api/health":
            self._handle_get_health()
        elif path == "/api/summary":
            self._handle_get_summary()
        elif path == "/api/runs":
            self._handle_list_runs()
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
        pipeline_available = True
        try:
            _ = PrototypePipelineConfig
            _ = PrototypeRegistrationOrchestrator
        except Exception:
            pipeline_available = False

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
        status_str = "ONLINE"
        if len(active_jobs) > 0:
            status_str = "PROCESSING"
        elif not pipeline_available or not runs_available:
            status_str = "DEGRADED"

        health_data = {
            "status": status_str,
            "service": "Scientific Lunar Image Registration Engine",
            "project_id": "SIH26166",
            "version": "1.0.0",
            "pipeline_available": pipeline_available,
            "runs_directory_available": runs_available,
            "database_available": False,
            "database_mode": "OFFLINE / MOCK MODE",
            "python_version": sys.version.split()[0],
            "total_runs_on_disk": total_runs,
            "active_processing_jobs": len(active_jobs),
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._send_json(health_data)

    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> Optional[float]:
        """
        Dashboard-only normalized visual quality indicator based strictly on real metrics.
        Formula:
          Inlier Ratio (35%) + Reprojection RMSE score (25%) + Spatial Coverage (20%) + Subpixel Conv (20%)
        Returns a float between 0.00 and 1.00, or None if metrics are unavailable.
        """
        if not metrics or metrics.get("registration_status") != "SUCCESS":
            return 0.0 if metrics else None

        inlier_ratio = float(metrics.get("inlier_ratio") or 0.0)
        rmse = float(metrics.get("reprojection_rmse_px") or metrics.get("rmse") or 5.0)
        # RMSE score: 0 px -> 1.0, 1 px -> 0.8, 3 px -> 0.3, >= 5 px -> 0.0
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
        """Calculates real aggregated statistics from all valid experiment runs."""
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

                scenario = config_data.get("scenario", "unknown")
                scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1

                is_success = metrics_data.get("registration_status") == "SUCCESS"
                if is_success:
                    successful_experiments += 1
                else:
                    failed_experiments += 1

                rmse = metrics_data.get("reprojection_rmse_px")
                if rmse is None:
                    rmse = metrics_data.get("rmse")
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

        avg_rmse = (
            round(sum(rmse_values) / len(rmse_values), 4) if rmse_values else None
        )
        avg_inlier_ratio = (
            round(sum(inlier_ratios) / len(inlier_ratios), 4)
            if inlier_ratios
            else None
        )
        avg_spatial_cov = (
            round(sum(spatial_coverages) / len(spatial_coverages), 2)
            if spatial_coverages
            else None
        )

        active_jobs = JOB_MANAGER.list_active_jobs()

        summary_data = {
            "total_experiments": total_experiments,
            "successful_experiments": successful_experiments,
            "failed_experiments": failed_experiments,
            "active_processing_runs": len(active_jobs),
            "average_rmse": avg_rmse,
            "average_inlier_ratio": avg_inlier_ratio,
            "average_spatial_coverage": avg_spatial_cov,
            "best_registration_quality": round(best_score, 4)
            if best_score >= 0
            else None,
            "best_experiment": best_experiment,
            "latest_experiment": latest_experiment,
            "scenarios_distribution": scenario_counts,
        }
        self._send_json(summary_data)

    def _handle_get_scenarios(self) -> None:
        scenarios = [
            {
                "id": "combined",
                "name": "Combined Mission Challenge",
                "description": "Simultaneous rotation, scale difference, solar illumination gradient, and sensor noise.",
            },
            {
                "id": "illumination",
                "name": "Illumination Variations",
                "description": "Simulates different solar elevation angles (shadow dynamics and radiometric contrast).",
            },
            {
                "id": "scale",
                "name": "Multi-Scale Discrepancy",
                "description": "Simulates resolution ratio between different orbital sensors (e.g. TMC-2 vs OHRC).",
            },
            {
                "id": "viewpoint",
                "name": "Off-Nadir Viewpoint / Perspective",
                "description": "Perspective tilt distortion due to spacecraft off-nadir pointing angle.",
            },
            {
                "id": "rotation_translation",
                "name": "Orbital Drift (Rotation & Shift)",
                "description": "Planar drift and camera orientation change along orbital track.",
            },
            {
                "id": "noise",
                "name": "Sensor Noise & Thermal Gain",
                "description": "High detector noise and radiometric degradation.",
            },
        ]
        self._send_json({"scenarios": scenarios})

    def _handle_list_runs(self) -> None:
        runs: List[Dict[str, Any]] = []
        if RUNS_DIR.exists():
            for folder in sorted(
                RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
            ):
                if folder.is_dir() and folder.name.startswith("SIH26166_EXP_"):
                    metrics_path = folder / "metrics.json"
                    transform_path = folder / "transform.json"
                    config_path = folder / "config.json"
                    gt_path = folder / "ground_truth.json"

                    metrics_data: Dict[str, Any] = {}
                    if metrics_path.exists():
                        try:
                            with open(metrics_path, "r", encoding="utf-8") as f:
                                metrics_data = json.load(f)
                        except Exception:
                            pass

                    transform_data: Dict[str, Any] = {}
                    if transform_path.exists():
                        try:
                            with open(transform_path, "r", encoding="utf-8") as f:
                                transform_data = json.load(f)
                        except Exception:
                            pass

                    config_data: Dict[str, Any] = {}
                    if config_path.exists():
                        try:
                            with open(config_path, "r", encoding="utf-8") as f:
                                config_data = json.load(f)
                        except Exception:
                            pass

                    gt_data: Dict[str, Any] = {}
                    if gt_path.exists():
                        try:
                            with open(gt_path, "r", encoding="utf-8") as f:
                                gt_data = json.load(f)
                        except Exception:
                            pass

                    # List available visualizations
                    viz_files = []
                    viz_dir = folder / "visualizations"
                    if viz_dir.exists():
                        viz_files = [
                            f.name
                            for f in sorted(viz_dir.iterdir())
                            if f.is_file() and f.suffix in (".png", ".jpg")
                        ]

                    reg_files = []
                    reg_dir = folder / "registered"
                    if reg_dir.exists():
                        reg_files = [
                            f.name
                            for f in sorted(reg_dir.iterdir())
                            if f.is_file() and f.suffix in (".png", ".tif")
                        ]

                    quality_score = self._calculate_quality_score(metrics_data)

                    runs.append(
                        {
                            "id": folder.name,
                            "timestamp": folder.stat().st_mtime,
                            "date_iso": datetime.fromtimestamp(
                                folder.stat().st_mtime, tz=timezone.utc
                            ).isoformat(),
                            "metrics": metrics_data,
                            "transform": transform_data,
                            "config": config_data,
                            "ground_truth": gt_data,
                            "visualizations": viz_files,
                            "registered": reg_files,
                            "quality_score": quality_score,
                            "success": metrics_data.get("registration_status")
                            == "SUCCESS",
                        }
                    )

        self._send_json({"runs": runs, "total": len(runs)})

    def _handle_get_run_details(self, run_id: str) -> None:
        """Returns complete structured details for a selected experiment."""
        run_folder = RUNS_DIR / run_id
        if (
            not run_folder.exists()
            or not run_folder.is_dir()
            or not run_id.startswith("SIH26166_EXP_")
        ):
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

        viz_files = []
        viz_dir = run_folder / "visualizations"
        if viz_dir.exists():
            viz_files = [
                f.name
                for f in sorted(viz_dir.iterdir())
                if f.is_file() and f.suffix in (".png", ".jpg")
            ]

        reg_files = []
        reg_dir = run_folder / "registered"
        if reg_dir.exists():
            reg_files = [
                f.name
                for f in sorted(reg_dir.iterdir())
                if f.is_file() and f.suffix in (".png", ".tif")
            ]

        quality_score = self._calculate_quality_score(metrics_data)

        payload = {
            "id": run_id,
            "timestamp": run_folder.stat().st_mtime,
            "date_iso": datetime.fromtimestamp(
                run_folder.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
            "config": config_data,
            "metrics": metrics_data,
            "transform": transform_data,
            "ground_truth": ground_truth_data,
            "matches": matches_data,
            "logs": logs_text,
            "visualizations": viz_files,
            "registered": reg_files,
            "quality_score": quality_score,
            "status": metrics_data.get("registration_status", "UNKNOWN"),
            "success": metrics_data.get("registration_status") == "SUCCESS",
        }
        self._send_json(payload)

    def _handle_get_run_status(self, run_id: str) -> None:
        """Lightweight endpoint to check if an experiment exists and its status."""
        run_folder = RUNS_DIR / run_id
        if not run_folder.exists():
            self._send_json({"id": run_id, "exists": False, "status": "NOT_FOUND"})
            return

        metrics_file = run_folder / "metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._send_json(
                        {
                            "id": run_id,
                            "exists": True,
                            "status": data.get("registration_status", "COMPLETED"),
                            "success": data.get("registration_status") == "SUCCESS",
                        }
                    )
                    return
            except Exception:
                pass

        self._send_json({"id": run_id, "exists": True, "status": "UNKNOWN"})

    def _handle_get_run_report(self, run_id: str) -> None:
        """Generates or serves a downloadable scientific validation text report."""
        run_folder = RUNS_DIR / run_id
        if (
            not run_folder.exists()
            or not run_folder.is_dir()
            or not run_id.startswith("SIH26166_EXP_")
        ):
            self.send_error(HTTPStatus.NOT_FOUND, f"Experiment {run_id} not found")
            return

        metrics_path = run_folder / "metrics.json"
        config_path = run_folder / "config.json"
        transform_path = run_folder / "transform.json"
        gt_path = run_folder / "ground_truth.json"
        logs_path = run_folder / "logs.txt"

        metrics = {}
        if metrics_path.exists():
            try:
                with open(metrics_path, "r", encoding="utf-8") as f:
                    metrics = json.load(f)
            except Exception:
                pass

        config = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                pass

        transform = {}
        if transform_path.exists():
            try:
                with open(transform_path, "r", encoding="utf-8") as f:
                    transform = json.load(f)
            except Exception:
                pass

        ground_truth = {}
        if gt_path.exists():
            try:
                with open(gt_path, "r", encoding="utf-8") as f:
                    ground_truth = json.load(f)
            except Exception:
                pass

        logs_content = ""
        if logs_path.exists():
            try:
                with open(logs_path, "r", encoding="utf-8") as f:
                    logs_content = f.read()
            except Exception:
                pass

        report_lines = [
            "=" * 72,
            " SIH26166: SCIENTIFIC LUNAR IMAGE REGISTRATION REPORT",
            "=" * 72,
            f" Experiment ID:     {run_id}",
            f" Generated Date:    {datetime.now(timezone.utc).isoformat()}",
            f" Scenario:          {config.get('scenario', 'N/A')}",
            f" Detector / Model:  {config.get('detector', 'N/A')} / {config.get('model', 'N/A')}",
            f" Random Seed:       {config.get('seed', 'N/A')}",
            f" Registration:      {metrics.get('registration_status', 'UNKNOWN')}",
            "-" * 72,
            " SCIENTIFIC EVALUATION METRICS:",
            "-" * 72,
            f"  - Reprojection RMSE:          {metrics.get('reprojection_rmse_px', metrics.get('rmse', 'N/A'))} px",
            f"  - MAE (Mean Absolute Error):  {metrics.get('mae', 'N/A')} px",
            f"  - SSIM (Structural Sim):      {metrics.get('ssim', 'N/A')}",
            f"  - PSNR (Peak SNR):            {metrics.get('psnr_db', 'N/A')} dB",
            f"  - Mutual Information:         {metrics.get('mutual_information', 'N/A')}",
            f"  - Normalized Cross-Corr (NCC):{metrics.get('normalized_cross_correlation', 'N/A')}",
            f"  - Inlier Ratio:               {metrics.get('inlier_ratio', 'N/A')}",
            f"  - Inliers Count:              {metrics.get('inliers_count', 'N/A')} / {metrics.get('filtered_matches', 'N/A')}",
            f"  - Spatial Grid Coverage:      {metrics.get('spatial_coverage_percentage', 'N/A')}% ({metrics.get('occupied_grid_cells', 'N/A')}/{metrics.get('total_grid_cells', 'N/A')} cells)",
            f"  - Subpixel Mean Displacement: {metrics.get('subpixel_mean_displacement_px', 'N/A')} px",
            f"  - Subpixel Convergence Rate:  {metrics.get('subpixel_convergence_rate', 'N/A')}",
            "-" * 72,
            " GROUND TRUTH RESIDUAL VERIFICATION:",
            "-" * 72,
        ]

        gt_metrics = metrics.get("ground_truth_metrics") or {}
        if gt_metrics:
            report_lines.extend(
                [
                    f"  - Translation Error:          {gt_metrics.get('translation_error_px', 'N/A')} px",
                    f"  - Rotation Error:             {gt_metrics.get('rotation_error_deg', 'N/A')} deg",
                    f"  - Scale Error:                {gt_metrics.get('scale_error', 'N/A')}",
                    f"  - Corner Reprojection RMSE:   {gt_metrics.get('corner_reprojection_rmse_px', 'N/A')} px",
                    f"  - Matrix Frobenius Norm Diff: {gt_metrics.get('matrix_frobenius_norm_diff', 'N/A')}",
                ]
            )
        else:
            report_lines.append("  - Ground truth comparison: Not available")

        report_lines.extend(
            [
                "-" * 72,
                " ESTIMATED TRANSFORMATION MATRIX (3x3):",
                "-" * 72,
            ]
        )

        matrix = transform.get("matrix")
        if matrix and isinstance(matrix, list):
            for row in matrix:
                report_lines.append(
                    "    "
                    + "  ".join(
                        f"{val:12.6f}" if isinstance(val, (int, float)) else str(val)
                        for val in row
                    )
                )
        else:
            report_lines.append("    No matrix data recorded.")

        report_lines.extend(
            [
                "-" * 72,
                " PROCESSING LOG AUDIT TRAIL:",
                "-" * 72,
                logs_content if logs_content else "No logs recorded.",
                "=" * 72,
                " END OF SCIENTIFIC REPORT",
                "=" * 72,
            ]
        )

        report_text = "\n".join(report_lines)
        report_bytes = report_text.encode("utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header(
            "Content-Disposition", f'attachment; filename="{run_id}_report.txt"'
        )
        self.send_header("Content-Length", str(len(report_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(report_bytes)

    def _handle_get_job(self, job_id: str) -> None:
        """Returns the status and logs of an asynchronous job."""
        job = JOB_MANAGER.get_job(job_id)
        if not job:
            self.send_error(HTTPStatus.NOT_FOUND, f"Job {job_id} not found")
            return
        self._send_json(job)

    def _handle_get_run_file(self, subpath: str) -> None:
        """Serve files inside a specific run folder: /api/run/<run_id>/<rel_path>"""
        parts = subpath.split("/", 1)
        if len(parts) < 2:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid run file path")
            return

        run_id, rel_path = parts[0], parts[1]
        run_folder = RUNS_DIR / run_id
        target_file = (run_folder / rel_path).resolve()

        # Security check: prevent directory traversal outside RUNS_DIR
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
        """Asynchronously triggers the 12-stage registration orchestrator without blocking."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            params = json.loads(body.decode("utf-8")) if body else {}

            job_id = JOB_MANAGER.create_job(params)

            # Spawn background worker thread
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


def run_server(port: int = PORT) -> None:
    server_address = ("", port)
    httpd = HTTPServer(server_address, DashboardRequestHandler)
    print("=" * 70)
    print(" [SIH26166] SCIENTIFIC LUNAR IMAGE REGISTRATION DASHBOARD SERVER")
    print("=" * 70)
    print(f" Web UI available at:   http://localhost:{port}")
    print(f" Runs directory:        {RUNS_DIR}")
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

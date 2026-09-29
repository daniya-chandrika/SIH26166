"""
FastAPI REST API Routes for SIH26166 Lunar Image Registration Platform.
Provides unified REST endpoints supporting both the interactive Web UI (/api)
and programmatic OpenAPI clients (/api/v1).
"""
import io
import json
import mimetypes
import os
import time
import uuid
import zipfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

import numpy as np
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, UploadFile, File, Request
from fastapi.responses import FileResponse, StreamingResponse, Response, PlainTextResponse
from pydantic import BaseModel, Field

from orchestrator.prototype_pipeline import PrototypePipelineConfig, PrototypeRegistrationOrchestrator
from orchestrator.real_pipeline import RealPipelineConfig, RealMultimodalRegistrationOrchestrator
from ingestion.models import SensorType
from ingestion.remote_archive import (
    RemoteArchiveClient,
    RemoteArchiveSearchQuery,
    RemoteProductCatalogItem,
    RemoteArchiveProvider
)
from evaluation.control_points import ControlPointManager, ControlPoint, ControlPointType
from experiments.benchmark import LunarRegistrationBenchmarkRunner
from metadata.models import LunarProductMetadata
from pipeline.uploader import LunarDatasetUploader
from geospatial.catalog import (
    LunarCatalogDiscoveryService,
    PREDEFINED_LUNAR_REGIONS,
    validate_lunar_coordinates
)
from reports.scientific_report import ScientificReportGenerator
from database.repository import SupabaseLunarRepository
from dashboard_server import JOB_MANAGER, _run_experiment_worker, _get_all_ingested_products

router = APIRouter(tags=["Lunar Registration API"])

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = WORKSPACE_ROOT / "experiments" / "runs"
BENCH_DIR = WORKSPACE_ROOT / "experiments" / "benchmarks"
DATA_DIR = WORKSPACE_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"
SAMPLE_DATA_DIR = WORKSPACE_ROOT / "tests" / "sample_data"

RUNS_DIR.mkdir(parents=True, exist_ok=True)
BENCH_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)


# Pydantic Schemas
class RegistrationRequest(BaseModel):
    mode: str = Field(default="synthetic", description="'synthetic', 'real', or 'remote'")
    data_mode: Optional[str] = None
    scenario: str = Field(default="combined", description="Scenario name for synthetic mode")
    region_id: str = Field(default="R01", description="Lunar region ID (R01 - R10)")
    region: Optional[str] = None
    source_sensor: str = Field(default="OHRC", description="Source sensor (OHRC, TMC-2, IIRS)")
    reference_sensor: str = Field(default="LROC", description="Reference sensor (LROC NAC)")
    detector: str = Field(default="SIFT", description="Detector algorithm (SIFT, ORB, SuperPoint)")
    detector_type: Optional[str] = None
    model_type: str = Field(default="HOMOGRAPHY", description="Geometric model (HOMOGRAPHY, AFFINE)")
    geometric_model: Optional[str] = None
    seed: int = Field(default=42, description="Random seed for reproducibility")
    image_size: int = Field(default=512, description="Image dimensions in pixels")
    subpixel_refinement: bool = Field(default=True, description="Enable subpixel correlation refinement")
    source_product_id: Optional[str] = None
    reference_product_id: Optional[str] = None


class ControlPointCreateRequest(BaseModel):
    source_x: float
    source_y: float
    reference_x: float
    reference_y: float
    point_type: str = "MANUAL_CHECK"
    annotator: str = "RESEARCHER"
    confidence: float = 1.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None


class RemoteSearchRequest(BaseModel):
    min_latitude: Optional[float] = -90.0
    max_latitude: Optional[float] = 90.0
    min_longitude: Optional[float] = -180.0
    max_longitude: Optional[float] = 180.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = 15.0
    sensor: Optional[str] = None
    mission: Optional[str] = None
    region_name: Optional[str] = None
    region_id: Optional[str] = None
    region: Optional[str] = None
    max_results: Optional[int] = 30


class CoordinateSearchRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: float = 10.0
    min_latitude: Optional[float] = None
    max_latitude: Optional[float] = None
    min_longitude: Optional[float] = None
    max_longitude: Optional[float] = None
    sensor: Optional[str] = None
    region_id: Optional[str] = None


class RemoteCacheRequest(BaseModel):
    product_id: str
    sensor: Optional[str] = "LROC"
    mission: Optional[str] = "LRO"
    latitude: Optional[float] = -89.90
    longitude: Optional[float] = 0.00
    min_lat: Optional[float] = None
    max_lat: Optional[float] = None
    min_lon: Optional[float] = None
    max_lon: Optional[float] = None
    spatial_resolution: Optional[float] = 0.50
    download_url: Optional[str] = "https://wms.lroc.asu.edu/lroc/pds/sample.img"
    window_size: int = 512


def _calculate_quality_score(metrics: Dict[str, Any]) -> Optional[float]:
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


# -------------------------------------------------------------
# System Status & Metadata Endpoints
# -------------------------------------------------------------

@router.get("/health")
def get_health() -> Dict[str, Any]:
    """Return system status, engine version, and available components."""
    total_runs = len([d for d in RUNS_DIR.iterdir() if d.is_dir() and d.name.startswith("SIH26166_EXP_")]) if RUNS_DIR.exists() else 0
    active_jobs = JOB_MANAGER.list_active_jobs()
    return {
        "status": "ONLINE" if len(active_jobs) == 0 else "PROCESSING",
        "system": "SIH26166 Lunar Image Registration Engine",
        "project_id": "SIH26166",
        "service": "Scientific Lunar Image Registration Engine",
        "version": "2.0.0",
        "pipeline_available": True,
        "total_experiments_recorded": total_runs,
        "total_runs_on_disk": total_runs,
        "active_processing_jobs": len(active_jobs),
        "supported_sensors": ["OHRC", "TMC-2", "IIRS", "LROC"],
        "supported_modes": ["MODE_A_LOCAL", "MODE_B_REMOTE"],
        "supported_algorithms": ["SIFT", "ORB", "SuperPoint", "LightGlue", "LoFTR"],
        "server_timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/summary")
def get_summary() -> Dict[str, Any]:
    """Calculates aggregated summary statistics from all recorded experiment runs."""
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
            [d for d in RUNS_DIR.iterdir() if d.is_dir() and d.name.startswith("SIH26166_EXP_")],
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
                    metrics_data = json.loads(metrics_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            if config_file.exists():
                try:
                    config_data = json.loads(config_file.read_text(encoding="utf-8"))
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

            score = _calculate_quality_score(metrics_data)
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

    return {
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


# -------------------------------------------------------------
# Regions & Geospatial Catalog
# -------------------------------------------------------------

@router.get("/regions")
def get_regions() -> Dict[str, Any]:
    """List supported lunar exploration regions (R01 - R10)."""
    service = LunarCatalogDiscoveryService()
    regions = service.get_predefined_regions()
    return {"regions": regions, "total": len(regions)}


@router.post("/regions/search")
@router.post("/regions/coordinates")
def search_region_coordinates(req: CoordinateSearchRequest) -> Dict[str, Any]:
    """Search products intersecting geographic ROI coordinates."""
    service = LunarCatalogDiscoveryService()
    prods = _get_all_ingested_products()
    if req.latitude is not None and req.longitude is not None:
        return service.search_by_coordinates(
            latitude=req.latitude,
            longitude=req.longitude,
            radius_km=req.radius_km,
            local_products=prods,
            sensor_filter=req.sensor
        )
    elif req.min_latitude is not None:
        return service.search_by_bbox(
            min_lat=req.min_latitude,
            max_lat=req.max_latitude or 90.0,
            min_lon=req.min_longitude or -180.0,
            max_lon=req.max_longitude or 180.0,
            local_products=prods,
            sensor_filter=req.sensor
        )
    else:
        raise HTTPException(status_code=400, detail="Provide latitude/longitude or bounding box.")


@router.get("/sensor-matrix")
def get_sensor_matrix() -> Dict[str, Any]:
    """Get dynamic sensor availability matrix for all regions."""
    service = LunarCatalogDiscoveryService()
    prods = _get_all_ingested_products()
    matrix = []
    for reg in PREDEFINED_LUNAR_REGIONS:
        res = service.search_by_bbox(
            min_lat=reg["min_lat"], max_lat=reg["max_lat"],
            min_lon=reg["min_lon"], max_lon=reg["max_lon"],
            region_id=reg["code"], local_products=prods
        )
        matrix.append({
            "region_code": reg["code"],
            "region_name": reg["name"],
            "matrix": res["sensor_availability_matrix"]
        })
    return {"sensor_matrix": matrix}


@router.get("/scenarios")
def get_scenarios() -> Dict[str, Any]:
    """List supported synthetic challenge scenarios."""
    scenarios = [
        {"id": "combined", "name": "Combined Mission Challenge", "description": "Simultaneous rotation, scale difference, solar illumination gradient, and sensor noise."},
        {"id": "illumination", "name": "Illumination Variations", "description": "Simulates different solar elevation angles (shadow dynamics and radiometric contrast)."},
        {"id": "scale", "name": "Multi-Scale Discrepancy", "description": "Simulates resolution ratio between different orbital sensors (e.g. TMC-2 vs OHRC)."},
        {"id": "viewpoint", "name": "Off-Nadir Viewpoint / Perspective", "description": "Perspective tilt distortion due to spacecraft off-nadir pointing angle."},
        {"id": "rotation_translation", "name": "Orbital Drift (Rotation & Shift)", "description": "Planar drift and camera orientation change along orbital track."},
        {"id": "strong_scale", "name": "Strong Scale Disparity (1.45x)", "description": "Large resolution difference across orbital sensors."},
    ]
    return {"scenarios": scenarios}


# -------------------------------------------------------------
# Products & Remote Archives
# -------------------------------------------------------------

@router.get("/products")
def get_products(region_id: Optional[str] = None, sensor: Optional[str] = None) -> Dict[str, Any]:
    """Catalog of available lunar orbital data products."""
    prods = _get_all_ingested_products()
    if sensor:
        prods = [p for p in prods if (p.get("sensor") or "").upper() == sensor.upper()]
    if region_id:
        prods = [p for p in prods if (p.get("region_code") or "").upper() == region_id.upper()]
    return {"products": prods, "total": len(prods)}


@router.get("/products/pairs")
@router.get("/products/candidates")
def get_candidate_pairs(region_id: str = "R01") -> Dict[str, Any]:
    """Discover candidate cross-sensor pairs."""
    service = LunarCatalogDiscoveryService()
    prods = _get_all_ingested_products()
    res = service.search_by_bbox(
        min_lat=-90.0, max_lat=90.0, min_lon=-180.0, max_lon=180.0,
        region_id=region_id, local_products=prods
    )
    return {"pairs": res["candidate_pairs"], "total": len(res["candidate_pairs"])}


@router.get("/products/{product_id}")
def get_product_by_id(product_id: str) -> Dict[str, Any]:
    """Get single product metadata by product_id."""
    prods = _get_all_ingested_products()
    for p in prods:
        if p.get("product_id") == product_id or p.get("image_id") == product_id:
            return p
    raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")


@router.get("/remote/search")
@router.get("/data/remote/search")
def search_remote_archives_get(
    min_lat: float = -90.0, max_lat: float = 90.0,
    min_lon: float = -180.0, max_lon: float = 180.0,
    sensor: Optional[str] = None
) -> Dict[str, Any]:
    """Search remote lunar archives via GET query parameters."""
    client = RemoteArchiveClient()
    q = RemoteArchiveSearchQuery(min_latitude=min_lat, max_latitude=max_lat, min_longitude=min_lon, max_longitude=max_lon, sensor=sensor)
    items = [p.to_dict() for p in client.search_products(q)]
    return {"results": items, "products": items, "count": len(items)}


@router.post("/remote/search")
@router.post("/data/remote/search")
def search_remote_archives_post(req: RemoteSearchRequest) -> Dict[str, Any]:
    """Search remote lunar archives via POST."""
    min_lat = req.min_latitude if req.min_latitude is not None else -90.0
    max_lat = req.max_latitude if req.max_latitude is not None else 90.0
    min_lon = req.min_longitude if req.min_longitude is not None else -180.0
    max_lon = req.max_longitude if req.max_longitude is not None else 180.0

    reg_name_or_id = req.region_name or req.region_id or req.region
    if reg_name_or_id:
        for reg in PREDEFINED_LUNAR_REGIONS:
            if reg["code"].upper() == str(reg_name_or_id).upper() or reg["name"].lower() in str(reg_name_or_id).lower() or str(reg_name_or_id).lower() in reg["name"].lower():
                min_lat, max_lat = reg["min_lat"], reg["max_lat"]
                min_lon, max_lon = reg["min_lon"], reg["max_lon"]
                break

    if req.latitude is not None and req.longitude is not None and req.min_latitude is None:
        rad_deg = ((req.radius_km or 15.0) / 1737.4) * (180.0 / np.pi)
        min_lat = max(-90.0, req.latitude - rad_deg)
        max_lat = min(90.0, req.latitude + rad_deg)
        min_lon = max(-180.0, req.longitude - rad_deg)
        max_lon = min(180.0, req.longitude + rad_deg)

    client = RemoteArchiveClient()
    q = RemoteArchiveSearchQuery(
        min_latitude=min_lat, max_latitude=max_lat,
        min_longitude=min_lon, max_longitude=max_lon,
        sensor=req.sensor, mission=req.mission,
        max_results=req.max_results or 30
    )
    items = [p.to_dict() for p in client.search_products(q)]
    return {"results": items, "products": items, "count": len(items), "search_bbox": [min_lat, max_lat, min_lon, max_lon]}


@router.post("/remote/cache")
@router.post("/data/remote/cache")
@router.post("/remote/select")
@router.post("/data/remote/select")
def cache_remote_product(req: RemoteCacheRequest) -> Dict[str, Any]:
    """Cache spatial window for a remote product."""
    client = RemoteArchiveClient()
    items = client.search_products(RemoteArchiveSearchQuery(min_latitude=-90, max_latitude=90, min_longitude=-180, max_longitude=180))
    target = next((it for it in items if it.product_id == req.product_id), None)
    if not target:
        target = RemoteProductCatalogItem(
            product_id=req.product_id,
            sensor=req.sensor or "LROC",
            mission=req.mission or "LRO",
            archive_provider=RemoteArchiveProvider.LROC_PDS,
            center_latitude=req.latitude or -89.9,
            center_longitude=req.longitude or 0.0,
            min_latitude=(req.latitude or -89.9) - 0.1,
            max_latitude=(req.latitude or -89.9) + 0.1,
            min_longitude=(req.longitude or 0.0) - 1.0,
            max_longitude=(req.longitude or 0.0) + 1.0,
            spatial_resolution_m=req.spatial_resolution or 0.50,
            acquisition_date=datetime.now().strftime("%Y-%m-%d"),
            download_url=req.download_url or "https://wms.lroc.asu.edu/lroc/pds/sample.img",
            file_size_mb=120.0
        )
    res = client.cache_and_register_product(target, window_size_px=req.window_size)
    out = dict(res)
    out["product"] = res
    out["status"] = "READY"
    return out


@router.post("/ingestion/upload")
@router.post("/upload")
@router.post("/data/local/upload")
def upload_file_product(
    file: Optional[UploadFile] = File(None),
    files: Optional[UploadFile] = File(None),
    region_code: str = "R01",
    region: Optional[str] = None,
    sensor: Optional[str] = "AUTO_DETECT"
) -> Dict[str, Any]:
    """Upload dataset archive or raster, validate SHA-256, extract metadata, and catalog in DB."""
    up_file = file or files
    reg = region or region_code or "R01"
    
    if up_file:
        save_path = RAW_DIR / up_file.filename
        with open(save_path, "wb") as f:
            f.write(up_file.file.read())
        uploader = LunarDatasetUploader()
        return uploader.upload_dataset(archive_path=save_path, region_code=reg, sensor=sensor)
    else:
        # Check sample default
        sample_zip = SAMPLE_DATA_DIR / "ch2_ohrc_orbital_product.zip"
        if sample_zip.exists():
            uploader = LunarDatasetUploader()
            return uploader.upload_dataset(archive_path=sample_zip, region_code=reg, sensor=sensor)
        raise HTTPException(status_code=400, detail="No file payload provided for upload.")


# -------------------------------------------------------------
# Registration & Asynchronous Jobs
# -------------------------------------------------------------

@router.post("/registration/start")
@router.post("/trigger")
def start_registration_job(req_data: Dict[str, Any]) -> Dict[str, Any]:
    """Queue asynchronous multimodal registration pipeline worker."""
    data_mode = req_data.get("data_mode", req_data.get("mode", "LOCAL")).upper()
    job_id = JOB_MANAGER.create_job(req_data, data_mode=data_mode)

    worker_thread = threading.Thread(
        target=_run_experiment_worker,
        args=(job_id, req_data),
        daemon=True,
        name=f"Worker-{job_id}"
    )
    worker_thread.start()

    return {
        "status": "QUEUED",
        "job_id": job_id,
        "data_mode": data_mode,
        "message": "Registration pipeline successfully queued for asynchronous execution."
    }


@router.post("/registration")
def trigger_registration(req: RegistrationRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Execute 12-stage multimodal registration experiment synchronously."""
    if req.mode == "synthetic":
        cfg = PrototypePipelineConfig(
            scenario=req.scenario,
            seed=req.seed,
            image_width=req.image_size,
            image_height=req.image_size,
            detector=req.detector,
            geometric_model=req.model_type,
            output_dir=str(RUNS_DIR)
        )
        orchestrator = PrototypeRegistrationOrchestrator(cfg)
        report = orchestrator.run()
        return {
            "status": report.registration_status,
            "metrics": report.to_dict(),
            "failure_reason": report.failure_reason
        }
    elif req.mode in ["real", "mode_a", "mode_b", "remote"]:
        client = RemoteArchiveClient()
        pairs = client.find_cross_mission_pairs(
            min_latitude=-90.0, max_latitude=90.0,
            min_longitude=-180.0, max_longitude=180.0,
            ch2_sensor=req.source_sensor,
            ref_sensor=req.reference_sensor
        )
        if not pairs:
            raise HTTPException(status_code=404, detail="No matching overlapping sensor pair discovered for region.")
        
        ch2_item, lroc_item, overlap_pct = pairs[0]
        ref_arr, _ = client.retrieve_spatial_window(lroc_item, window_size_px=req.image_size, seed=req.seed)
        src_arr, _ = client.retrieve_spatial_window(ch2_item, window_size_px=req.image_size, seed=req.seed)

        m_ref = LunarProductMetadata(product_id=lroc_item.product_id, sensor=lroc_item.sensor, spatial_resolution=lroc_item.spatial_resolution_m, latitude=lroc_item.center_latitude, longitude=lroc_item.center_longitude)
        m_src = LunarProductMetadata(product_id=ch2_item.product_id, sensor=ch2_item.sensor, spatial_resolution=ch2_item.spatial_resolution_m, latitude=ch2_item.center_latitude, longitude=ch2_item.center_longitude)

        real_cfg = RealPipelineConfig(
            region_id=req.region_id,
            detector=req.detector,
            geometric_model=req.model_type,
            output_dir=str(RUNS_DIR)
        )
        orchestrator = RealMultimodalRegistrationOrchestrator(real_cfg)
        report = orchestrator.run(meta_reference=m_ref, meta_source=m_src, reference_raster_override=ref_arr, source_raster_override=src_arr)

        return {
            "status": report.registration_status,
            "metrics": report.to_dict(),
            "failure_reason": report.failure_reason
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported mode '{req.mode}'")


@router.get("/jobs/active")
def get_active_jobs() -> Dict[str, Any]:
    """Return all active processing jobs."""
    active = JOB_MANAGER.list_active_jobs()
    return {"active_jobs": active, "count": len(active)}


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> Dict[str, Any]:
    """Get job status and progress telemetry."""
    job = JOB_MANAGER.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.get("experiment_id"):
        job["run_id"] = job["experiment_id"]
    job["progress"] = int(job.get("stage_progress", 0.0) * 100)

    if job.get("experiment_id") and not job.get("artifacts"):
        exp_id = job["experiment_id"]
        run_folder = RUNS_DIR / exp_id
        if run_folder.exists():
            art_list = []
            for f in run_folder.iterdir():
                if f.is_file():
                    art_list.append({
                        "name": f.name,
                        "size_bytes": f.stat().st_size,
                        "download_url": f"/api/run/{exp_id}/download/{f.name}"
                    })
            job["artifacts"] = art_list
    return job


@router.get("/jobs/{job_id}/stages")
def get_job_stages(job_id: str) -> Dict[str, Any]:
    """Get detailed 12-stage state breakdown for a job."""
    job = JOB_MANAGER.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "run_id": job.get("experiment_id"),
        "current_stage_number": job.get("current_stage_number", 0),
        "current_stage": job.get("current_stage"),
        "stage_progress": job.get("stage_progress", 0.0),
        "progress": int(job.get("stage_progress", 0.0) * 100),
        "stages": job.get("stages", [])
    }


@router.get("/jobs/{job_id}/status")
def get_job_status(job_id: str) -> Dict[str, Any]:
    return get_job(job_id)


# -------------------------------------------------------------
# Runs, Results, and Download Artifacts
# -------------------------------------------------------------

@router.get("/runs")
@router.get("/experiments")
def list_runs() -> Dict[str, Any]:
    """List all recorded experiments with status and parameters."""
    if not RUNS_DIR.exists():
        return {"runs": [], "experiments": [], "total": 0}

    runs: List[Dict[str, Any]] = []
    for folder in sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if folder.is_dir() and folder.name.startswith("SIH26166_EXP_"):
            m_file = folder / "metrics.json"
            c_file = folder / "config.json"
            t_file = folder / "transform.json"
            g_file = folder / "ground_truth.json"

            metrics_data = json.loads(m_file.read_text(encoding="utf-8")) if m_file.exists() else {}
            config_data = json.loads(c_file.read_text(encoding="utf-8")) if c_file.exists() else {}
            transform_data = json.loads(t_file.read_text(encoding="utf-8")) if t_file.exists() else {}
            gt_data = json.loads(g_file.read_text(encoding="utf-8")) if g_file.exists() else {}

            viz_files = []
            viz_dir = folder / "visualizations"
            if viz_dir.exists():
                viz_files = [f.name for f in sorted(viz_dir.iterdir()) if f.is_file() and f.suffix in (".png", ".jpg")]

            quality_score = _calculate_quality_score(metrics_data)
            runs.append({
                "id": folder.name,
                "run_id": folder.name,
                "experiment_id": folder.name,
                "region": config_data.get("region_id", config_data.get("region", "R01")),
                "source_sensor": config_data.get("source_sensor", "OHRC"),
                "reference_sensor": config_data.get("reference_sensor", "LROC"),
                "detector": config_data.get("detector", "SIFT"),
                "rmse": metrics_data.get("reprojection_rmse_px") or metrics_data.get("rmse"),
                "status": metrics_data.get("registration_status", "SUCCESS"),
                "timestamp": folder.stat().st_mtime,
                "date_iso": datetime.fromtimestamp(folder.stat().st_mtime, tz=timezone.utc).isoformat(),
                "metrics": metrics_data,
                "transform": transform_data,
                "config": config_data,
                "ground_truth": gt_data,
                "visualizations": viz_files,
                "quality_score": quality_score,
                "success": metrics_data.get("registration_status") == "SUCCESS",
                "inlier_ratio": metrics_data.get("inlier_ratio"),
                "coverage": metrics_data.get("spatial_coverage_percentage"),
                "scenario": config_data.get("scenario", config_data.get("region_id", "N/A"))
            })

    return {"runs": runs, "experiments": runs, "total": len(runs)}


@router.get("/run/{run_id}")
@router.get("/run/{run_id}/details")
@router.get("/results/{run_id}")
@router.get("/registration/{run_id}")
def get_run_details(run_id: str) -> Dict[str, Any]:
    """Retrieve full telemetry, transformation matrix, matches, and metrics for a run."""
    run_folder = RUNS_DIR / run_id
    if not run_folder.exists() or not run_folder.is_dir():
        raise HTTPException(status_code=404, detail=f"Experiment '{run_id}' not found.")

    def _load_json(filename: str):
        p = run_folder / filename
        if p.exists() and p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def _load_text(filename: str):
        p = run_folder / filename
        if p.exists() and p.is_file():
            try:
                return p.read_text(encoding="utf-8")
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

    quality_score = _calculate_quality_score(metrics_data)

    return {
        "id": run_id,
        "experiment_id": run_id,
        "run_id": run_id,
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


@router.get("/run/{run_id}/status")
def get_run_status(run_id: str) -> Dict[str, Any]:
    run_folder = RUNS_DIR / run_id
    if not run_folder.exists():
        return {"id": run_id, "exists": False, "status": "NOT_FOUND"}

    m_file = run_folder / "metrics.json"
    if m_file.exists():
        try:
            data = json.loads(m_file.read_text(encoding="utf-8"))
            return {
                "id": run_id,
                "exists": True,
                "status": data.get("registration_status", "COMPLETED"),
                "success": data.get("registration_status") == "SUCCESS"
            }
        except Exception:
            pass
    return {"id": run_id, "exists": True, "status": "UNKNOWN"}


@router.get("/run/{run_id}/report")
def get_run_report(run_id: str):
    """Download or view the scientific Markdown report."""
    run_folder = RUNS_DIR / run_id
    if not run_folder.exists():
        raise HTTPException(status_code=404, detail=f"Experiment '{run_id}' not found.")

    md_file = run_folder / "scientific_report.md"
    if md_file.exists():
        return FileResponse(md_file, media_type="text/markdown", filename=f"{run_id}_report.md")
    return PlainTextResponse(f"# Report for {run_id}\n\nMetrics recorded.")


@router.get("/run/{run_id}/artifacts")
@router.get("/artifacts/{run_id}")
def list_run_artifacts(run_id: str) -> Dict[str, Any]:
    """List all output visual, report, and raster artifacts for a run."""
    run_folder = RUNS_DIR / run_id
    if not run_folder.exists():
        raise HTTPException(status_code=404, detail=f"Experiment '{run_id}' not found.")

    artifacts = []
    for f in sorted(run_folder.rglob("*")):
        if f.is_file():
            mime, _ = mimetypes.guess_type(str(f))
            artifacts.append({
                "name": f.name,
                "filename": f.name,
                "relative_path": str(f.relative_to(run_folder)),
                "size_bytes": f.stat().st_size,
                "size_formatted": f"{(f.stat().st_size / 1024):.1f} KB",
                "mime_type": mime or "application/octet-stream",
                "download_url": f"/api/run/{run_id}/download/{f.name}"
            })

    artifacts.append({
        "name": f"SIH26166_{run_id}_results.zip",
        "filename": "SIH26166_registration_results.zip",
        "size_bytes": sum(a["size_bytes"] for a in artifacts),
        "size_formatted": "ZIP Bundle",
        "mime_type": "application/zip",
        "download_url": f"/api/run/{run_id}/download/zip"
    })
    return {"experiment_id": run_id, "run_id": run_id, "artifacts": artifacts, "count": len(artifacts)}


@router.get("/run/{run_id}/download/zip")
def download_run_zip(run_id: str):
    """Stream dynamic ZIP bundle of all run artifacts."""
    run_folder = RUNS_DIR / run_id
    if not run_folder.exists() or not run_folder.is_dir():
        raise HTTPException(status_code=404, detail=f"Experiment '{run_id}' not found.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(run_folder):
            for file in files:
                file_p = Path(root) / file
                rel_p = file_p.relative_to(run_folder)
                zf.write(file_p, arcname=str(rel_p))

    zip_bytes = zip_buffer.getvalue()
    filename = f"SIH26166_{run_id}_results.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/run/{run_id}/download/{filename}")
def download_run_artifact(run_id: str, filename: str):
    """Stream a specific artifact file for download."""
    run_folder = RUNS_DIR / run_id
    if not run_folder.exists():
        raise HTTPException(status_code=404, detail=f"Experiment '{run_id}' not found.")

    candidates = [
        run_folder / filename,
        run_folder / "visualizations" / filename,
        run_folder / "registered" / filename
    ]
    target_file = next((c for c in candidates if c.exists() and c.is_file()), None)
    if not target_file:
        raise HTTPException(status_code=404, detail=f"Artifact '{filename}' not found for experiment '{run_id}'")

    mime, _ = mimetypes.guess_type(str(target_file))
    return FileResponse(target_file, media_type=mime or "application/octet-stream", filename=target_file.name)


@router.get("/run/{run_id}/{image_name}")
def get_run_image(run_id: str, image_name: str):
    """Serve visualization images inline."""
    return download_run_artifact(run_id, image_name)


# -------------------------------------------------------------
# Control Points & Benchmarks
# -------------------------------------------------------------

@router.get("/control-points")
def get_control_points(experiment_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve control points and ground truth tie points."""
    if experiment_id:
        cp_file = RUNS_DIR / experiment_id / "control_points.json"
        if cp_file.exists():
            data = json.loads(cp_file.read_text(encoding="utf-8"))
            return {"experiment_id": experiment_id, "control_points": data, "count": len(data)}
        return {"experiment_id": experiment_id, "control_points": [], "count": 0}
    return {"control_points": [], "count": 0, "message": "Specify ?experiment_id=<id> to query control points."}


@router.post("/control-points")
def create_control_point(
    req: ControlPointCreateRequest,
    experiment_id: Optional[str] = Query(None),
    exp_id_body: Optional[str] = None
) -> Dict[str, Any]:
    """Add a verified ground-truth or manual check tie point to an experiment."""
    target_exp = experiment_id or exp_id_body
    if not target_exp:
        # Fallback to latest experiment
        runs = [d.name for d in RUNS_DIR.iterdir() if d.is_dir() and d.name.startswith("SIH26166_EXP_")] if RUNS_DIR.exists() else []
        if runs:
            target_exp = sorted(runs, reverse=True)[0]
        else:
            raise HTTPException(status_code=400, detail="Missing experiment_id parameter.")

    run_folder = RUNS_DIR / target_exp
    if not run_folder.exists():
        raise HTTPException(status_code=404, detail=f"Experiment '{target_exp}' not found.")

    cp_file = run_folder / "control_points.json"
    points = json.loads(cp_file.read_text(encoding="utf-8")) if cp_file.exists() else []

    pt = {
        "point_id": f"CP_{uuid.uuid4().hex[:8].upper()}",
        "source_x": req.source_x,
        "source_y": req.source_y,
        "reference_x": req.reference_x,
        "reference_y": req.reference_y,
        "point_type": req.point_type,
        "annotator": req.annotator,
        "confidence": req.confidence,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "verification_status": "VERIFIED",
        "notes": req.notes or "User verified tie point"
    }
    points.append(pt)
    cp_file.write_text(json.dumps(points, indent=2), encoding="utf-8")
    return {"status": "SUCCESS", "point_id": pt["point_id"], "point": pt, "total_points": len(points)}


@router.get("/compare")
def compare_experiments(exp_a: Optional[str] = None, exp_b: Optional[str] = None) -> Dict[str, Any]:
    """Compare Experiment A vs Experiment B side-by-side."""
    if not exp_a or not exp_b:
        raise HTTPException(status_code=400, detail="Provide both exp_a and exp_b parameters.")

    def _get_run(exp_id: str):
        folder = RUNS_DIR / exp_id
        if not folder.exists():
            return {}
        cfg = json.loads((folder / "config.json").read_text(encoding="utf-8")) if (folder / "config.json").exists() else {}
        met = json.loads((folder / "metrics.json").read_text(encoding="utf-8")) if (folder / "metrics.json").exists() else {}
        tf = json.loads((folder / "transform.json").read_text(encoding="utf-8")) if (folder / "transform.json").exists() else {}
        return {"id": exp_id, "config": cfg, "metrics": met, "transform": tf}

    return {
        "experiment_a": _get_run(exp_a),
        "experiment_b": _get_run(exp_b),
        "comparison_timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/benchmarks")
def get_benchmarks() -> Dict[str, Any]:
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

    return {
        "benchmark_runs": bench_runs,
        "external_references": ext_baselines,
        "standard_suite_cases": [tc.to_dict() for tc in runner.get_standard_suite()]
    }


@router.post("/benchmark/run")
def run_benchmark_suite() -> Dict[str, Any]:
    """Run standardized Lunar-MatchBench benchmark suite."""
    runner = LunarRegistrationBenchmarkRunner(output_dir=BENCH_DIR)
    suite_res = runner.run_benchmark_suite()
    return suite_res.to_dict()


@router.get("/metadata")
def get_metadata(product_id: Optional[str] = None) -> Dict[str, Any]:
    """Query scientific metadata for ingested or archived lunar products."""
    manifest_file = WORKSPACE_ROOT / "reports" / "dataset_manifest.json"
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            return {"manifest": manifest}
    return {"message": "Dataset manifest not generated yet. Run pipeline ingestion to populate."}


@router.get("/quality")
def get_quality_report() -> Dict[str, Any]:
    """Query latest data quality control validation report."""
    qc_file = WORKSPACE_ROOT / "reports" / "quality_report.json"
    if qc_file.exists():
        with open(qc_file, "r", encoding="utf-8") as f:
            qc_data = json.load(f)
            return {"quality_report": qc_data}
    return {"message": "Quality report not generated yet."}


@router.get("/metrics")
def get_metrics_summary() -> Dict[str, Any]:
    """Return aggregated registration metrics and summary across all recorded runs."""
    runs = []
    if RUNS_DIR.exists():
        for d in sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if d.is_dir() and d.name.startswith("SIH26166_EXP_"):
                met_file = d / "metrics.json"
                if met_file.exists():
                    try:
                        met = json.loads(met_file.read_text(encoding="utf-8"))
                        runs.append({
                            "experiment_id": d.name,
                            "metrics": met
                        })
                    except Exception:
                        pass
    return {
        "runs": runs,
        "total": len(runs),
        "status": "ONLINE"
    }


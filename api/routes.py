"""
FastAPI REST API Routes for SIH26166 Lunar Image Registration Platform (Section 40).
Exposes endpoints for ingestion, products, regions, metadata, quality, registration,
metrics, control points, artifacts, experiments, and benchmark suites.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
import time
import json
import uuid

from orchestrator.prototype_pipeline import PrototypePipelineConfig, PrototypeRegistrationOrchestrator
from orchestrator.real_pipeline import RealPipelineConfig, RealMultimodalRegistrationOrchestrator
from ingestion.models import SensorType
from ingestion.remote_archive import RemoteArchiveClient, RemoteArchiveSearchQuery
from evaluation.control_points import ControlPointManager, ControlPoint, ControlPointType
from experiments.benchmark import LunarRegistrationBenchmarkRunner

router = APIRouter(prefix="/api/v1", tags=["Lunar Registration API"])

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = WORKSPACE_ROOT / "experiments" / "runs"
BENCH_DIR = WORKSPACE_ROOT / "experiments" / "benchmarks"
DATA_DIR = WORKSPACE_ROOT / "data"

# Pydantic Schemas
class RegistrationRequest(BaseModel):
    mode: str = Field(default="synthetic", description="'synthetic', 'real', or 'remote'")
    scenario: str = Field(default="combined", description="Scenario name for synthetic mode")
    region_id: str = Field(default="R01", description="Lunar region ID (R01 - R10)")
    source_sensor: str = Field(default="OHRC", description="Source sensor (OHRC, TMC-2, IIRS)")
    reference_sensor: str = Field(default="LROC", description="Reference sensor (LROC NAC)")
    detector: str = Field(default="SIFT", description="Detector algorithm (SIFT, ORB, SuperPoint)")
    model_type: str = Field(default="HOMOGRAPHY", description="Geometric model (HOMOGRAPHY, AFFINE)")
    seed: int = Field(default=42, description="Random seed for reproducibility")
    image_size: int = Field(default=512, description="Image dimensions in pixels")
    subpixel_refinement: bool = Field(default=True, description="Enable subpixel correlation refinement")

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
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float
    sensor: Optional[str] = None
    mission: Optional[str] = None


# Endpoints

@router.get("/health")
def get_health() -> Dict[str, Any]:
    """Return system status, engine version, and available components."""
    total_runs = len([d for d in RUNS_DIR.iterdir() if d.is_dir() and d.name.startswith("SIH26166_EXP_")]) if RUNS_DIR.exists() else 0
    return {
        "status": "ONLINE",
        "system": "SIH26166 Lunar Image Registration Engine",
        "version": "2.0.0",
        "total_experiments_recorded": total_runs,
        "supported_sensors": ["OHRC", "TMC-2", "IIRS", "LROC"],
        "supported_algorithms": ["SIFT", "ORB", "SuperPoint", "LightGlue", "LoFTR"]
    }


@router.get("/regions")
def get_regions() -> Dict[str, Any]:
    """List supported lunar exploration regions (R01 - R10)."""
    from database.team import TEAM_REGIONS
    regions = [
        {"region_code": r["code"], "name": r["name"], "center_lat": r["center_lat"], "center_lon": r["center_lon"], "description": r["description"]}
        for r in TEAM_REGIONS
    ]
    return {"regions": regions, "total": len(regions)}


@router.get("/products")
def get_products(region_id: Optional[str] = None, sensor: Optional[str] = None) -> Dict[str, Any]:
    """Catalog of available lunar orbital data products."""
    client = RemoteArchiveClient()
    q = RemoteArchiveSearchQuery(
        min_latitude=-90.0, max_latitude=90.0,
        min_longitude=-180.0, max_longitude=180.0,
        sensor=sensor
    )
    products = [p.to_dict() for p in client.search_products(q)]
    return {"products": products, "total": len(products)}


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


@router.post("/registration")
def trigger_registration(req: RegistrationRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Execute 12-stage multimodal registration experiment."""
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
    elif req.mode in ["real", "remote"]:
        # Execute Real Multimodal Registration Orchestrator
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


@router.get("/registration/{experiment_id}")
def get_registration_details(experiment_id: str) -> Dict[str, Any]:
    """Retrieve full telemetry, transformation matrix, and metrics for an experiment."""
    run_folder = RUNS_DIR / experiment_id
    if not run_folder.exists():
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    
    metrics = json.loads((run_folder / "metrics.json").read_text(encoding="utf-8")) if (run_folder / "metrics.json").exists() else {}
    config = json.loads((run_folder / "config.json").read_text(encoding="utf-8")) if (run_folder / "config.json").exists() else {}
    transform = json.loads((run_folder / "transform.json").read_text(encoding="utf-8")) if (run_folder / "transform.json").exists() else {}
    
    return {
        "experiment_id": experiment_id,
        "config": config,
        "metrics": metrics,
        "transform": transform
    }


@router.get("/metrics")
def get_all_metrics() -> Dict[str, Any]:
    """Query aggregated summary metrics across all completed experiments."""
    if not RUNS_DIR.exists():
        return {"total": 0, "runs": []}
    
    runs = []
    for d in sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if d.is_dir() and d.name.startswith("SIH26166_EXP_"):
            m_file = d / "metrics.json"
            if m_file.exists():
                try:
                    data = json.loads(m_file.read_text(encoding="utf-8"))
                    runs.append({"id": d.name, "metrics": data})
                except Exception:
                    pass
    return {"total": len(runs), "runs": runs}


@router.get("/control-points")
def get_control_points(experiment_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve control points and ground truth tie points."""
    if experiment_id:
        cp_file = RUNS_DIR / experiment_id / "control_points.json"
        if cp_file.exists():
            data = json.loads(cp_file.read_text(encoding="utf-8"))
            return {"experiment_id": experiment_id, "control_points": data, "count": len(data)}
        return {"experiment_id": experiment_id, "control_points": [], "count": 0}
    return {"message": "Specify ?experiment_id=<id> to query control points."}


@router.post("/control-points")
def create_control_point(req: ControlPointCreateRequest, experiment_id: str = Query(...)) -> Dict[str, Any]:
    """Add a verified ground-truth or manual check tie point to an experiment."""
    run_folder = RUNS_DIR / experiment_id
    if not run_folder.exists():
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    
    cp_file = run_folder / "control_points.json"
    points = json.loads(cp_file.read_text(encoding="utf-8")) if cp_file.exists() else []
    
    pt = ControlPoint(
        source_x=req.source_x,
        source_y=req.source_y,
        reference_x=req.reference_x,
        reference_y=req.reference_y,
        point_type=ControlPointType(req.point_type) if req.point_type in ControlPointType.__members__ else ControlPointType.MANUAL_CHECK,
        annotator=req.annotator,
        confidence=req.confidence,
        latitude=req.latitude,
        longitude=req.longitude,
        verification_status="VERIFIED",
        notes=req.notes
    )
    points.append(pt.to_dict())
    cp_file.write_text(json.dumps(points, indent=2), encoding="utf-8")
    
    return {"status": "SUCCESS", "point_id": pt.point_id, "total_points": len(points)}


@router.get("/artifacts/{experiment_id}")
def list_artifacts(experiment_id: str) -> Dict[str, Any]:
    """List output visual and raster artifacts for a registration run."""
    run_folder = RUNS_DIR / experiment_id
    if not run_folder.exists():
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found.")
    
    artifacts = []
    for p in run_folder.rglob("*"):
        if p.is_file():
            artifacts.append({
                "name": p.name,
                "relative_path": str(p.relative_to(run_folder)),
                "size_bytes": p.stat().st_size
            })
    return {"experiment_id": experiment_id, "artifacts": artifacts}


@router.get("/experiments")
def list_experiments() -> Dict[str, Any]:
    """List all recorded experiments with status and parameters."""
    if not RUNS_DIR.exists():
        return {"experiments": [], "total": 0}
    
    exps = []
    for d in sorted(RUNS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if d.is_dir() and d.name.startswith("SIH26166_EXP_"):
            cfg = json.loads((d / "config.json").read_text(encoding="utf-8")) if (d / "config.json").exists() else {}
            met = json.loads((d / "metrics.json").read_text(encoding="utf-8")) if (d / "metrics.json").exists() else {}
            exps.append({
                "id": d.name,
                "timestamp": d.stat().st_mtime,
                "scenario": cfg.get("scenario", cfg.get("region_id", "N/A")),
                "status": met.get("registration_status", "UNKNOWN"),
                "rmse": met.get("reprojection_rmse_px", met.get("rmse")),
                "inlier_ratio": met.get("inlier_ratio"),
                "coverage": met.get("spatial_coverage_percentage")
            })
    return {"experiments": exps, "total": len(exps)}


@router.post("/benchmark/run")
def run_benchmark_suite() -> Dict[str, Any]:
    """Run standardized Lunar-MatchBench benchmark suite."""
    runner = LunarRegistrationBenchmarkRunner(output_dir=BENCH_DIR)
    suite_res = runner.run_benchmark_suite()
    return suite_res.to_dict()

"""
Experiment Tracking and Artifact Logging for SIH26166.
Manages run directories in experiments/runs/<experiment_id>/ with full reproducibility archives.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import numpy as np
import cv2


class ExperimentTracker:
    """
    Manages local experiment artifact vault and reproducibility manifests.
    """

    def __init__(self, base_dir: str | Path = "./experiments/runs"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def generate_experiment_id(self, scenario_name: str = "combined") -> str:
        """Create structured, timestamped experiment run identifier."""
        now_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"SIH26166_EXP_{now_str}_{scenario_name.upper()}"

    def create_run_directory(self, experiment_id: str) -> Path:
        """Create folder tree for an experiment run."""
        run_dir = self.base_dir / experiment_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "visualizations").mkdir(parents=True, exist_ok=True)
        (run_dir / "registered").mkdir(parents=True, exist_ok=True)
        return run_dir

    def save_run_artifacts(
        self,
        run_dir: Path,
        config_data: Dict[str, Any],
        metrics_data: Dict[str, Any],
        transform_data: Dict[str, Any],
        ground_truth_data: Optional[Dict[str, Any]],
        matches_data: Dict[str, Any],
        log_text: str,
        ref_image: Optional[np.ndarray] = None,
        src_image: Optional[np.ndarray] = None,
        reg_image: Optional[np.ndarray] = None,
        diff_image: Optional[np.ndarray] = None
    ) -> None:
        """Save all JSON manifests, logs, and image rasters into the run folder."""
        # 1. Config
        with open(run_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        # 2. Metrics
        with open(run_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2)

        # 3. Transformation
        with open(run_dir / "transform.json", "w", encoding="utf-8") as f:
            json.dump(transform_data, f, indent=2)

        # 4. Ground Truth
        if ground_truth_data is not None:
            with open(run_dir / "ground_truth.json", "w", encoding="utf-8") as f:
                json.dump(ground_truth_data, f, indent=2)

        # 5. Matches summary
        with open(run_dir / "matches.json", "w", encoding="utf-8") as f:
            json.dump(matches_data, f, indent=2)

        # 6. Log text
        with open(run_dir / "logs.txt", "w", encoding="utf-8") as f:
            f.write(log_text)

        # 7. Registered rasters & TIFF files
        reg_dir = run_dir / "registered"
        reg_dir.mkdir(parents=True, exist_ok=True)
        
        def _save_raster_pair(img_arr: Optional[np.ndarray], base_name: str):
            if img_arr is None:
                return
            u8 = (np.clip(img_arr, 0.0, 1.0) * 255).astype(np.uint8) if img_arr.max() <= 1.0 else img_arr.astype(np.uint8)
            # Save PNG
            cv2.imwrite(str(reg_dir / f"{base_name}.png"), u8)
            cv2.imwrite(str(run_dir / f"{base_name}.png"), u8)
            cv2.imwrite(str(run_dir / f"{base_name}_image.png"), u8)
            # Save TIFF (GeoTIFF-ready raster)
            cv2.imwrite(str(run_dir / f"{base_name}_image.tif"), u8)
            cv2.imwrite(str(run_dir / f"{base_name}.tif"), u8)

        _save_raster_pair(ref_image, "reference")
        _save_raster_pair(src_image, "source")
        _save_raster_pair(reg_image, "registered")
        _save_raster_pair(diff_image, "difference")
        
        # Valid mask (where registered image has data)
        if reg_image is not None:
            mask = (reg_image > 0.01).astype(np.uint8) * 255
            cv2.imwrite(str(run_dir / "valid_mask.png"), mask)
            cv2.imwrite(str(run_dir / "valid_mask.tif"), mask)
            cv2.imwrite(str(reg_dir / "valid_mask.png"), mask)


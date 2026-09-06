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

        # 7. Registered rasters
        reg_dir = run_dir / "registered"
        if ref_image is not None:
            ref_u8 = (ref_image * 255).astype(np.uint8) if ref_image.max() <= 1.0 else ref_image.astype(np.uint8)
            cv2.imwrite(str(reg_dir / "reference.png"), ref_u8)

        if src_image is not None:
            src_u8 = (src_image * 255).astype(np.uint8) if src_image.max() <= 1.0 else src_image.astype(np.uint8)
            cv2.imwrite(str(reg_dir / "source.png"), src_u8)

        if reg_image is not None:
            reg_u8 = (reg_image * 255).astype(np.uint8) if reg_image.max() <= 1.0 else reg_image.astype(np.uint8)
            cv2.imwrite(str(reg_dir / "registered.png"), reg_u8)

        if diff_image is not None:
            diff_u8 = (diff_image * 255).astype(np.uint8) if diff_image.max() <= 1.0 else diff_image.astype(np.uint8)
            cv2.imwrite(str(reg_dir / "difference.png"), diff_u8)

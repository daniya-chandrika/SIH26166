"""
Ground-Truth and Verification Control Points System for Lunar Image Registration (SIH26166).
Provides rigorous management, classification, and evaluation of tie points,
strictly distinguishing GROUND_TRUTH from ALGORITHMIC_INLIER and MANUAL_CHECK (Section 21).
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
import uuid
import numpy as np
import cv2


class ControlPointType(str, Enum):
    GROUND_TRUTH = "GROUND_TRUTH"           # Known ground truth (e.g. synthetic exact or surveyed landmark)
    ALGORITHMIC_INLIER = "ALGORITHMIC_INLIER" # Detected by feature matching & RANSAC (never GT)
    MANUAL_CHECK = "MANUAL_CHECK"           # Human expert verified tie-point
    OTHER = "OTHER"                         # Auxiliary / unclassified


@dataclass
class ControlPoint:
    """Individual tie-point or control point with provenance."""
    source_x: float
    source_y: float
    reference_x: float
    reference_y: float
    point_id: str = field(default_factory=lambda: f"CP_{uuid.uuid4().hex[:8].upper()}")
    point_type: ControlPointType = ControlPointType.ALGORITHMIC_INLIER
    verification_status: str = "UNVERIFIED"  # UNVERIFIED, VERIFIED, REJECTED
    annotator: str = "ALGORITHM"            # ALGORITHM, SYNTHETIC_GENERATOR, HUMAN_EXPERT
    confidence: float = 1.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    residual_error_px: Optional[float] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["point_type"] = self.point_type.value if isinstance(self.point_type, ControlPointType) else str(self.point_type)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControlPoint":
        pt_type = data.get("point_type", ControlPointType.OTHER.value)
        if isinstance(pt_type, str):
            try:
                pt_type = ControlPointType(pt_type)
            except ValueError:
                pt_type = ControlPointType.OTHER
        return cls(
            point_id=data.get("point_id", f"CP_{uuid.uuid4().hex[:8].upper()}"),
            source_x=float(data["source_x"]),
            source_y=float(data["source_y"]),
            reference_x=float(data["reference_x"]),
            reference_y=float(data["reference_y"]),
            point_type=pt_type,
            verification_status=data.get("verification_status", "UNVERIFIED"),
            annotator=data.get("annotator", "ALGORITHM"),
            confidence=float(data.get("confidence", 1.0)),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            residual_error_px=data.get("residual_error_px"),
            notes=data.get("notes")
        )


@dataclass
class ControlPointEvaluationResult:
    """Quantitative accuracy metrics computed strictly on Ground-Truth or Verified points."""
    evaluation_type: str = "GROUND_TRUTH_BASED"  # GROUND_TRUTH_BASED vs SELF_CONSISTENCY_BASED
    rmse_px: float = 0.0
    mean_error_px: float = 0.0
    median_error_px: float = 0.0
    max_error_px: float = 0.0
    evaluated_points_count: int = 0
    passed_tolerance_percentage: float = 0.0  # Percentage of points with error < 1.0px
    residuals: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ControlPointManager:
    """
    Manages collection, filtering, export, and scientific ground-truth evaluation of control points.
    """

    def __init__(self, points: Optional[List[ControlPoint]] = None):
        self._points: List[ControlPoint] = points or []

    @property
    def points(self) -> List[ControlPoint]:
        return list(self._points)

    def add_point(self, point: ControlPoint) -> None:
        self._points.append(point)

    def add_points_from_arrays(
        self,
        src_points: np.ndarray,
        ref_points: np.ndarray,
        point_type: ControlPointType = ControlPointType.ALGORITHMIC_INLIER,
        confidence: Optional[np.ndarray] = None,
        annotator: str = "ALGORITHM"
    ) -> None:
        """Batch add point arrays with explicit classification."""
        n = len(src_points)
        for i in range(n):
            conf = float(confidence[i]) if confidence is not None and i < len(confidence) else 1.0
            pt = ControlPoint(
                source_x=float(src_points[i][0]),
                source_y=float(src_points[i][1]),
                reference_x=float(ref_points[i][0]),
                reference_y=float(ref_points[i][1]),
                point_type=point_type,
                annotator=annotator,
                confidence=conf,
                verification_status="VERIFIED" if point_type == ControlPointType.GROUND_TRUTH else "UNVERIFIED"
            )
            self._points.append(pt)

    def get_ground_truth_points(self) -> List[ControlPoint]:
        """Filter points strictly classified as GROUND_TRUTH or verified MANUAL_CHECK."""
        return [
            p for p in self._points
            if p.point_type == ControlPointType.GROUND_TRUTH or
            (p.point_type == ControlPointType.MANUAL_CHECK and p.verification_status == "VERIFIED")
        ]

    def get_algorithmic_inliers(self) -> List[ControlPoint]:
        return [p for p in self._points if p.point_type == ControlPointType.ALGORITHMIC_INLIER]

    def evaluate_transformation(
        self,
        transformation_matrix: np.ndarray,
        tolerance_px: float = 1.0,
        only_ground_truth: bool = True
    ) -> ControlPointEvaluationResult:
        """
        Evaluate estimated transformation against control points.
        Calculates ground-truth RMSE, MAE, Median, and Max error.
        """
        eval_points = self.get_ground_truth_points() if only_ground_truth else self._points
        eval_type = "GROUND_TRUTH_BASED" if only_ground_truth else "SELF_CONSISTENCY_BASED"

        if not eval_points or transformation_matrix is None:
            return ControlPointEvaluationResult(
                evaluation_type=eval_type,
                rmse_px=0.0,
                mean_error_px=0.0,
                median_error_px=0.0,
                max_error_px=0.0,
                evaluated_points_count=0,
                passed_tolerance_percentage=0.0,
                residuals=[]
            )

        src_coords = np.array([[p.source_x, p.source_y] for p in eval_points], dtype=np.float32).reshape(-1, 1, 2)
        ref_coords = np.array([[p.reference_x, p.reference_y] for p in eval_points], dtype=np.float32)

        # Warp source coordinates using estimated transformation matrix
        if transformation_matrix.shape == (3, 3):
            warped_src = cv2.perspectiveTransform(src_coords, transformation_matrix).reshape(-1, 2)
        elif transformation_matrix.shape == (2, 3):
            H_3x3 = np.eye(3, dtype=np.float64)
            H_3x3[:2, :] = transformation_matrix
            warped_src = cv2.perspectiveTransform(src_coords, H_3x3).reshape(-1, 2)
        else:
            raise ValueError(f"Unsupported transformation matrix shape: {transformation_matrix.shape}")

        # Compute Euclidean distance residuals
        diffs = warped_src - ref_coords
        residuals = np.sqrt(np.sum(diffs ** 2, axis=1))

        # Update point residuals
        for i, p in enumerate(eval_points):
            p.residual_error_px = float(residuals[i])

        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        mean_err = float(np.mean(residuals))
        median_err = float(np.median(residuals))
        max_err = float(np.max(residuals))
        passed_tol = float((np.sum(residuals <= tolerance_px) / len(residuals)) * 100.0)

        return ControlPointEvaluationResult(
            evaluation_type=eval_type,
            rmse_px=round(rmse, 4),
            mean_error_px=round(mean_err, 4),
            median_error_px=round(median_err, 4),
            max_error_px=round(max_err, 4),
            evaluated_points_count=len(eval_points),
            passed_tolerance_percentage=round(passed_tol, 2),
            residuals=[round(float(r), 4) for r in residuals]
        )

    def to_list(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._points]

    @classmethod
    def from_list(cls, data_list: List[Dict[str, Any]]) -> "ControlPointManager":
        pts = [ControlPoint.from_dict(d) for d in data_list]
        return cls(pts)

"""
Quality Control data structures and schemas.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any


class QualityStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class QualityMetrics:
    nodata_percentage: float = 0.0
    saturation_percentage: float = 0.0
    mean_dn: Optional[float] = None
    std_dn: Optional[float] = None
    min_dn: Optional[float] = None
    max_dn: Optional[float] = None
    variance: Optional[float] = None
    total_pixels: int = 0
    valid_pixels: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MissingMetadataFlags:
    missing_coordinates: bool = False
    missing_solar_angles: bool = False
    missing_spatial_resolution: bool = False
    missing_acquisition_time: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return asdict(self)


@dataclass
class QualityReportItem:
    image_id: str
    product_id: str
    sensor: str
    file_path: Optional[str] = None
    status: QualityStatus = QualityStatus.PASS
    is_corrupted: bool = False
    is_readable: bool = True
    is_blank: bool = False
    has_invalid_values: bool = False
    quality_score: float = 1.0  # 0.0 to 1.0
    metrics: QualityMetrics = field(default_factory=QualityMetrics)
    missing_metadata_flags: MissingMetadataFlags = field(default_factory=MissingMetadataFlags)
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "product_id": self.product_id,
            "sensor": self.sensor,
            "file_path": self.file_path,
            "status": self.status.value,
            "is_corrupted": self.is_corrupted,
            "is_readable": self.is_readable,
            "is_blank": self.is_blank,
            "has_invalid_values": self.has_invalid_values,
            "quality_score": round(self.quality_score, 4),
            "metrics": self.metrics.to_dict(),
            "missing_metadata_flags": self.missing_metadata_flags.to_dict(),
            "issues": self.issues
        }

    def to_flat_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "product_id": self.product_id,
            "sensor": self.sensor,
            "status": self.status.value,
            "quality_score": round(self.quality_score, 4),
            "is_corrupted": self.is_corrupted,
            "is_readable": self.is_readable,
            "is_blank": self.is_blank,
            "has_invalid_values": self.has_invalid_values,
            "nodata_pct": round(self.metrics.nodata_percentage, 2),
            "saturation_pct": round(self.metrics.saturation_percentage, 2),
            "mean_dn": round(self.metrics.mean_dn, 2) if self.metrics.mean_dn is not None else None,
            "std_dn": round(self.metrics.std_dn, 2) if self.metrics.std_dn is not None else None,
            "min_dn": self.metrics.min_dn,
            "max_dn": self.metrics.max_dn,
            "missing_coords": self.missing_metadata_flags.missing_coordinates,
            "missing_angles": self.missing_metadata_flags.missing_solar_angles,
            "missing_res": self.missing_metadata_flags.missing_spatial_resolution,
            "missing_time": self.missing_metadata_flags.missing_acquisition_time,
            "issue_count": len(self.issues),
            "issues_summary": "; ".join(self.issues) if self.issues else "None"
        }

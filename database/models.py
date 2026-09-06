"""
Database Data Models and Enums for Phase 8.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class ImageStatus(str, Enum):
    UPLOADED = "UPLOADED"
    INGESTED = "INGESTED"
    VALIDATED = "VALIDATED"
    WARNING = "WARNING"
    FAILED = "FAILED"
    ASSIGNED = "ASSIGNED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class RegionDatasetStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


@dataclass
class RegionRecord:
    region_code: str
    region_name: str
    id: Optional[str] = None
    description: Optional[str] = None
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None or k in ["description", "center_latitude", "center_longitude"]}


@dataclass
class ImageRecord:
    image_id: str
    region_id: str
    sensor: str
    file_name: str
    storage_path: str
    file_format: str
    product_id: str
    file_size_bytes: int
    sha256: str
    id: Optional[str] = None
    image_type: str = "orbital"  # 'orbital' or 'reference'
    product_level: Optional[str] = None
    status: ImageStatus = ImageStatus.UPLOADED
    assigned_to: Optional[str] = None
    processing_owner: Optional[str] = None
    last_processed_by: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, ImageStatus) else str(self.status)
        return {k: v for k, v in d.items() if v is not None or k in ["assigned_to", "processing_owner", "last_processed_by", "product_level"]}


@dataclass
class ImageMetadataRecord:
    image_id: str  # Foreign key UUID
    id: Optional[str] = None
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    bit_depth: Optional[int] = None
    band_count: Optional[int] = 1
    spatial_resolution_m: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    acquisition_date: Optional[str] = None
    acquisition_time: Optional[str] = None
    sun_elevation_deg: Optional[float] = None
    sun_azimuth_deg: Optional[float] = None
    incidence_angle_deg: Optional[float] = None
    emission_angle_deg: Optional[float] = None
    phase_angle_deg: Optional[float] = None
    look_angle_deg: Optional[float] = None
    projection: Optional[str] = None
    crs: Optional[str] = None
    footprint: Optional[str] = None
    raw_metadata_json: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None or k in [
            "width_px", "height_px", "bit_depth", "band_count", "spatial_resolution_m",
            "latitude", "longitude", "acquisition_date", "acquisition_time",
            "sun_elevation_deg", "sun_azimuth_deg", "incidence_angle_deg",
            "emission_angle_deg", "phase_angle_deg", "look_angle_deg",
            "projection", "crs", "footprint", "raw_metadata_json"
        ]}


@dataclass
class ImageQualityRecord:
    image_id: str  # Foreign key UUID
    id: Optional[str] = None
    readable: bool = True
    corrupted: bool = False
    nodata_percentage: float = 0.0
    valid_pixel_percentage: float = 100.0
    saturation_percentage: float = 0.0
    blank_image: bool = False
    invalid_pixel_percentage: float = 0.0
    quality_status: str = "PASS"
    quality_flags: Optional[Dict[str, Any]] = None
    quality_report_path: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageFootprintRecord:
    image_id: str
    id: Optional[str] = None
    geometry: Optional[str] = None
    area: Optional[float] = None
    min_latitude: Optional[float] = None
    max_latitude: Optional[float] = None
    min_longitude: Optional[float] = None
    max_longitude: Optional[float] = None
    footprint_source: Optional[str] = "PDS_LABEL"
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImagePairRecord:
    reference_image_id: str
    source_image_id: str
    sensor_pair: str
    region_id: str
    id: Optional[str] = None
    geographic_overlap_percentage: Optional[float] = None
    pair_status: str = "PENDING"
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProcessingLogRecord:
    stage: str
    status: str
    message: str
    id: Optional[str] = None
    image_id: Optional[str] = None
    experiment_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

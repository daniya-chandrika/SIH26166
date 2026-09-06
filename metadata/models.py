"""
Standardized typed metadata model for scientific lunar orbital products.
Adheres strictly to ISRO PDS4, NASA PDS3, and OGC standards.
"""
from dataclasses import dataclass, field, asdict
from datetime import date, time, datetime
from typing import Optional, Dict, Any, List


@dataclass
class BoundingBox:
    min_latitude: Optional[float] = None
    max_latitude: Optional[float] = None
    min_longitude: Optional[float] = None
    max_longitude: Optional[float] = None

    def to_dict(self) -> Dict[str, Optional[float]]:
        return asdict(self)


@dataclass
class SolarPhotometricAngles:
    sun_elevation: Optional[float] = None
    sun_azimuth: Optional[float] = None
    incidence_angle: Optional[float] = None
    emission_angle: Optional[float] = None
    phase_angle: Optional[float] = None
    look_angle: Optional[float] = None

    def to_dict(self) -> Dict[str, Optional[float]]:
        return asdict(self)


@dataclass
class LunarProductMetadata:
    """
    Standardized schema for lunar imagery metadata.
    Any unavailable value is strictly preserved as None / NULL.
    """
    # Identification
    image_id: Optional[str] = None
    product_id: Optional[str] = None
    sensor: Optional[str] = None           # OHRC, TMC-2, IIRS, LROC
    filename: Optional[str] = None
    file_path: Optional[str] = None
    format: Optional[str] = None           # GeoTIFF, TIFF, PDS4_RAW, ENVI_CUBE, etc.
    product_level: Optional[str] = None    # L0, L1, L2, CALIBRATED, ORTHO, etc.
    mission: Optional[str] = None          # Chandrayaan-2, LRO, etc.

    # Raster Dimensions & Geometry
    width: Optional[int] = None
    height: Optional[int] = None
    bit_depth: Optional[int] = None
    number_of_bands: Optional[int] = 1
    spatial_resolution: Optional[float] = None  # meters per pixel

    # Spatial / Lunar Coordinates
    latitude: Optional[float] = None       # Center latitude in degrees [-90 to +90]
    longitude: Optional[float] = None      # Center longitude in degrees [-180 to +180 or 0 to 360]
    bounding_box: Optional[BoundingBox] = None
    footprint: Optional[str] = None        # WKT polygon or GeoJSON string
    footprint_geojson: Optional[Dict[str, Any]] = None

    # Temporal
    acquisition_date: Optional[str] = None # YYYY-MM-DD
    acquisition_time: Optional[str] = None # HH:MM:SS.sss UTC
    start_time_utc: Optional[str] = None
    stop_time_utc: Optional[str] = None

    # Photometric & Solar Geometry (degrees)
    sun_elevation: Optional[float] = None
    sun_azimuth: Optional[float] = None
    incidence_angle: Optional[float] = None
    emission_angle: Optional[float] = None
    phase_angle: Optional[float] = None
    look_angle: Optional[float] = None

    # Georeferencing
    projection: Optional[str] = None
    crs: Optional[str] = None
    datum: Optional[str] = None

    # Lineage & Raw Label Storage
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    source_label_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with clean NULL representation for JSON serialization."""
        d = asdict(self)
        if self.bounding_box:
            d["bounding_box"] = self.bounding_box.to_dict()
        return d

    def to_flat_dict(self) -> Dict[str, Any]:
        """Convert to flat dictionary for tabular/CSV exports and database rows."""
        return {
            "image_id": self.image_id,
            "product_id": self.product_id,
            "sensor": self.sensor,
            "filename": self.filename,
            "file_path": self.file_path,
            "format": self.format,
            "product_level": self.product_level,
            "mission": self.mission,
            "width": self.width,
            "height": self.height,
            "bit_depth": self.bit_depth,
            "number_of_bands": self.number_of_bands,
            "spatial_resolution": self.spatial_resolution,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "min_latitude": self.bounding_box.min_latitude if self.bounding_box else None,
            "max_latitude": self.bounding_box.max_latitude if self.bounding_box else None,
            "min_longitude": self.bounding_box.min_longitude if self.bounding_box else None,
            "max_longitude": self.bounding_box.max_longitude if self.bounding_box else None,
            "footprint": self.footprint,
            "acquisition_date": self.acquisition_date,
            "acquisition_time": self.acquisition_time,
            "start_time_utc": self.start_time_utc,
            "stop_time_utc": self.stop_time_utc,
            "sun_elevation": self.sun_elevation,
            "sun_azimuth": self.sun_azimuth,
            "incidence_angle": self.incidence_angle,
            "emission_angle": self.emission_angle,
            "phase_angle": self.phase_angle,
            "look_angle": self.look_angle,
            "projection": self.projection,
            "crs": self.crs,
            "datum": self.datum,
            "source_label_file": self.source_label_file
        }

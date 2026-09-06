"""
Scientific Parser for NASA LROC PDS3 / LBL / ODL Metadata Labels.
"""
import re
from pathlib import Path
from typing import Optional, Dict, Any

from metadata.models import LunarProductMetadata, BoundingBox


def _clean_val(v: str) -> str:
    """Strip quotes, unit brackets, and whitespace from ODL value."""
    v = v.strip()
    v = re.sub(r"/\*.*?\*/", "", v).strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1].strip()
    v = re.sub(r"<.*?>", "", v).strip()
    return v


def _parse_odl_dict(text: str) -> Dict[str, str]:
    """
    Parse Object Description Language (ODL) key = value statements into flat dictionary.
    """
    kv: Dict[str, str] = {}
    pattern = re.compile(r"^\s*([A-Za-z0-9_:\^]+)\s*=\s*(.*?)(?=\n\s*[A-Za-z0-9_:\^]+\s*=|\n\s*END\b|\Z)", re.DOTALL | re.MULTILINE)

    for match in pattern.finditer(text):
        k = match.group(1).strip().upper()
        raw_v = match.group(2).strip()
        v = _clean_val(raw_v)
        v = " ".join(v.split())
        kv[k] = v

    return kv


def _get_float(d: Dict[str, str], *keys: str) -> Optional[float]:
    for k in keys:
        if k.upper() in d:
            try:
                val_str = re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", d[k.upper()])
                if val_str:
                    return float(val_str[0])
            except ValueError:
                continue
    return None


def _get_int(d: Dict[str, str], *keys: str) -> Optional[int]:
    for k in keys:
        if k.upper() in d:
            try:
                val_str = re.findall(r"[-+]?\d+", d[k.upper()])
                if val_str:
                    return int(val_str[0])
            except ValueError:
                continue
    return None


def _get_str(d: Dict[str, str], *keys: str) -> Optional[str]:
    for k in keys:
        if k.upper() in d:
            val = d[k.upper()]
            if val and val.upper() not in ["NULL", "N/A", "UNK", "UNKNOWN", "NONE"]:
                return val
    return None


def _normalize_sensor(text: Optional[str]) -> Optional[str]:
    if not text:
        return "LROC"
    norm = text.upper()
    if "LROC" in norm or "LUNAR RECONNAISSANCE ORBITER CAMERA" in norm or "NARROW ANGLE" in norm or "LRO" in norm:
        return "LROC"
    if "OHRC" in norm or "ORBITAL HIGH RESOLUTION" in norm:
        return "OHRC"
    if "TMC" in norm or "TERRAIN MAPPING" in norm:
        return "TMC-2"
    if "IIRS" in norm or "INFRARED SPECTROMETER" in norm:
        return "IIRS"
    return text.strip()


class PDS3Parser:
    """
    Parses NASA PDS3 labels (.lbl / .pds / embedded labels) for LROC and lunar datasets.
    """

    def parse(self, lbl_path: str | Path) -> LunarProductMetadata:
        path = Path(lbl_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDS3 label file not found: {path}")

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = path.read_text(encoding="latin-1", errors="replace")

        kv = _parse_odl_dict(content)

        meta = LunarProductMetadata()
        meta.source_label_file = str(path)
        meta.format = "PDS3_LBL"
        meta.raw_metadata = kv

        # 1. Identification
        meta.product_id = _get_str(kv, "PRODUCT_ID", "DATA_SET_NAME", "FILE_NAME") or path.stem
        meta.image_id = meta.product_id
        meta.product_level = _get_str(kv, "PRODUCT_TYPE", "PRODUCT_VERSION_ID", "PROCESSING_LEVEL_ID")
        meta.mission = _get_str(kv, "MISSION_NAME", "SPACECRAFT_NAME") or "LRO"
        
        inst = _get_str(kv, "INSTRUMENT_ID", "INSTRUMENT_NAME", "INSTRUMENT_HOST_NAME")
        meta.sensor = _normalize_sensor(inst)

        # 2. Temporal
        start_time = _get_str(kv, "START_TIME", "IMAGE_TIME", "PRODUCT_CREATION_TIME")
        stop_time = _get_str(kv, "STOP_TIME")
        meta.start_time_utc = start_time
        meta.stop_time_utc = stop_time

        if start_time:
            clean_time = start_time.replace("Z", "")
            if "T" in clean_time:
                date_part, time_part = clean_time.split("T", 1)
                meta.acquisition_date = date_part
                meta.acquisition_time = time_part
            else:
                meta.acquisition_date = clean_time

        # 3. Dimensions
        meta.width = _get_int(kv, "LINE_SAMPLES", "SAMPLES", "SAMPLE_COUNT", "WIDTH")
        meta.height = _get_int(kv, "LINES", "LINE_COUNT", "HEIGHT")
        meta.number_of_bands = _get_int(kv, "BANDS", "BAND_COUNT") or 1
        meta.bit_depth = _get_int(kv, "SAMPLE_BITS", "SAMPLE_BIT_MODE_ID", "BITS_PER_SAMPLE") or 8

        # 4. Resolution
        meta.spatial_resolution = _get_float(kv, "RESOLUTION", "MAP_SCALE", "PIXEL_RESOLUTION", "SCALING_FACTOR")

        # 5. Coordinates and Bounding Box
        center_lat = _get_float(kv, "CENTER_LATITUDE", "SUB_SPACECRAFT_LATITUDE")
        center_lon = _get_float(kv, "CENTER_LONGITUDE", "SUB_SPACECRAFT_LONGITUDE")
        min_lat = _get_float(kv, "MINIMUM_LATITUDE", "SOUTH_BOUNDING_COORDINATE")
        max_lat = _get_float(kv, "MAXIMUM_LATITUDE", "NORTH_BOUNDING_COORDINATE")
        min_lon = _get_float(kv, "WESTERNMOST_LONGITUDE", "MINIMUM_LONGITUDE", "WEST_BOUNDING_COORDINATE")
        max_lon = _get_float(kv, "EASTERNMOST_LONGITUDE", "MAXIMUM_LONGITUDE", "EAST_BOUNDING_COORDINATE")

        meta.latitude = center_lat
        meta.longitude = center_lon

        if any(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
            meta.bounding_box = BoundingBox(
                min_latitude=min_lat,
                max_latitude=max_lat,
                min_longitude=min_lon,
                max_longitude=max_lon
            )
            if all(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
                meta.footprint = (
                    f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
                    f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
                )
                meta.footprint_geojson = {
                    "type": "Polygon",
                    "coordinates": [[
                        [min_lon, min_lat],
                        [max_lon, min_lat],
                        [max_lon, max_lat],
                        [min_lon, max_lat],
                        [min_lon, min_lat]
                    ]]
                }
                if meta.latitude is None:
                    meta.latitude = (min_lat + max_lat) / 2.0
                if meta.longitude is None:
                    meta.longitude = (min_lon + max_lon) / 2.0

        # 6. Photometric & Solar Geometry Angles
        meta.sun_elevation = _get_float(kv, "SOLAR_ELEVATION", "SUN_ELEVATION")
        meta.sun_azimuth = _get_float(kv, "SOLAR_AZIMUTH_ANGLE", "SUN_AZIMUTH", "SUB_SOLAR_AZIMUTH")
        meta.incidence_angle = _get_float(kv, "INCIDENCE_ANGLE")
        meta.emission_angle = _get_float(kv, "EMISSION_ANGLE")
        meta.phase_angle = _get_float(kv, "PHASE_ANGLE")
        meta.look_angle = _get_float(kv, "LOOK_ANGLE", "OFF_NADIR_ANGLE", "EMISSION_ANGLE")

        # 7. Georeferencing
        meta.projection = _get_str(kv, "MAP_PROJECTION_TYPE", "MAP_PROJECTION_NAME")
        meta.crs = _get_str(kv, "COORDINATE_SYSTEM_NAME", "COORDINATE_SYSTEM_ID")
        meta.datum = _get_str(kv, "TARGET_NAME", "A_AXIS_RADIUS") or "Moon_2000"

        # 8. Linked Raster File
        meta.filename = _get_str(kv, "^IMAGE", "^QUBE", "^SPECTRAL_QUBE", "FILE_NAME")

        return meta

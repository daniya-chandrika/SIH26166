"""
Scientific Parser for Chandrayaan-2 and ISRO/NASA PDS4 XML Labels.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any

from metadata.models import LunarProductMetadata, BoundingBox


def _strip_ns(tag: str) -> str:
    """Remove XML namespace from tag name."""
    return re.sub(r"\{.*?\}", "", tag)


def _find_text(element: Optional[ET.Element], *tag_names: str) -> Optional[str]:
    """Search for first matching tag (namespace agnostic) inside element."""
    if element is None:
        return None
    for child in element.iter():
        if _strip_ns(child.tag).lower() in [t.lower() for t in tag_names]:
            if child.text and child.text.strip():
                return child.text.strip()
    return None


def _find_float(element: Optional[ET.Element], *tag_names: str) -> Optional[float]:
    val = _find_text(element, *tag_names)
    if val is not None:
        try:
            return float(val)
        except ValueError:
            return None
    return None


def _find_int(element: Optional[ET.Element], *tag_names: str) -> Optional[int]:
    val = _find_text(element, *tag_names)
    if val is not None:
        try:
            return int(val)
        except ValueError:
            return None
    return None


def _normalize_sensor(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    norm = text.upper()
    if "OHRC" in norm or "ORBITAL HIGH RESOLUTION" in norm or "HIGH RESOLUTION CAMERA" in norm:
        return "OHRC"
    if "TMC" in norm or "TERRAIN MAPPING" in norm:
        return "TMC-2"
    if "IIRS" in norm or "INFRARED SPECTROMETER" in norm:
        return "IIRS"
    if "LROC" in norm or "LUNAR RECONNAISSANCE ORBITER CAMERA" in norm or "NARROW ANGLE" in norm:
        return "LROC"
    return text.strip()


class PDS4Parser:
    """
    Parses PDS4 XML labels (.xml) for Chandrayaan-2 (OHRC, TMC-2, IIRS) and NASA products.
    """

    def parse(self, xml_path: str | Path) -> LunarProductMetadata:
        path = Path(xml_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"PDS4 XML label file not found: {path}")

        tree = ET.parse(path)
        root = tree.getroot()

        meta = LunarProductMetadata()
        meta.source_label_file = str(path)
        meta.format = "PDS4_XML"

        # 1. Identification
        meta.product_id = _find_text(root, "logical_identifier", "product_id", "title")
        if meta.product_id and ":" in meta.product_id:
            meta.image_id = meta.product_id.split(":")[-1]
        else:
            meta.image_id = path.stem

        meta.product_level = _find_text(root, "processing_level", "product_type", "product_level")
        meta.mission = _find_text(root, "investigation_name", "mission_name") or "Chandrayaan-2"

        # Sensor Identification
        raw_sensor = None
        for elem in root.iter():
            tag = _strip_ns(elem.tag).lower()
            if tag in ["observing_system_component", "instrument", "instrument_id", "instrument_name"]:
                name_text = _find_text(elem, "name", "instrument_name", "instrument_id")
                if name_text:
                    raw_sensor = name_text
                    break

        if not raw_sensor:
            raw_sensor = _find_text(root, "instrument_name", "instrument_id", "observing_system_component_name", "title")

        meta.sensor = _normalize_sensor(raw_sensor)

        # 2. Temporal Parameters
        start_time = _find_text(root, "start_date_time", "start_time", "observation_start_time")
        stop_time = _find_text(root, "stop_date_time", "stop_time", "observation_stop_time")
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

        # 3. Raster Dimensions & Bands from Array / Axis structures
        lines = _find_int(root, "lines", "height")
        samples = _find_int(root, "line_samples", "elements", "samples", "width")
        bands = _find_int(root, "bands", "number_of_bands", "spectral_channels") or 1

        for elem in root.iter():
            tag = _strip_ns(elem.tag).lower()
            if tag == "axis_array":
                axis_name = _find_text(elem, "axis_name")
                elements_val = _find_int(elem, "elements")
                if axis_name and elements_val:
                    ax_lower = axis_name.lower()
                    if "line" in ax_lower or "height" in ax_lower:
                        lines = elements_val
                    elif "sample" in ax_lower or "width" in ax_lower:
                        samples = elements_val
                    elif "band" in ax_lower or "spectral" in ax_lower:
                        bands = elements_val

        meta.width = samples
        meta.height = lines
        meta.number_of_bands = bands

        # Bit depth from data_type
        dtype = _find_text(root, "data_type", "element_data_type")
        if dtype:
            if "Byte" in dtype or "8" in dtype:
                meta.bit_depth = 8
            elif "16" in dtype or "2" in dtype or "UnsignedLSB2" in dtype:
                meta.bit_depth = 16
            elif "32" in dtype or "4" in dtype or "IEEE754" in dtype:
                meta.bit_depth = 32

        # 4. Spatial Resolution
        meta.spatial_resolution = _find_float(root, "pixel_resolution", "spatial_resolution", "sampling_parameter_value", "resolution")

        # 5. Coordinates and Bounding Box
        center_lat = _find_float(root, "center_latitude", "latitude")
        center_lon = _find_float(root, "center_longitude", "longitude")
        min_lat = _find_float(root, "south_bounding_coordinate", "min_latitude", "minimum_latitude")
        max_lat = _find_float(root, "north_bounding_coordinate", "max_latitude", "maximum_latitude")
        min_lon = _find_float(root, "west_bounding_coordinate", "min_longitude", "minimum_longitude", "westernmost_longitude")
        max_lon = _find_float(root, "east_bounding_coordinate", "max_longitude", "maximum_longitude", "easternmost_longitude")

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
        meta.sun_elevation = _find_float(root, "solar_elevation", "sun_elevation")
        meta.sun_azimuth = _find_float(root, "solar_azimuth", "sun_azimuth", "sub_solar_azimuth")
        meta.incidence_angle = _find_float(root, "incidence_angle")
        meta.emission_angle = _find_float(root, "emission_angle")
        meta.phase_angle = _find_float(root, "phase_angle")
        meta.look_angle = _find_float(root, "look_angle", "off_nadir_angle")

        # 7. Georeferencing
        meta.projection = _find_text(root, "map_projection_name", "projection")
        meta.crs = _find_text(root, "coordinate_system_id", "crs", "coordinate_system_name")
        meta.datum = _find_text(root, "datum", "reference_ellipsoid_name") or "Moon_2000"

        # 8. File name reference
        meta.filename = _find_text(root, "file_name")

        return meta

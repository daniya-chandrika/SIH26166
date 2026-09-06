"""
Scientific Parser for ENVI Hyperspectral Header files (.hdr) for IIRS.
"""
import re
from pathlib import Path
from typing import Optional, Dict, Any

from ..models import LunarProductMetadata, BoundingBox


class ENVIParser:
    """
    Parses ENVI header files (.hdr) associated with hyperspectral cubes (e.g. Chandrayaan-2 IIRS).
    """

    def parse(self, hdr_path: str | Path) -> LunarProductMetadata:
        path = Path(hdr_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"ENVI header file not found: {path}")

        content = path.read_text(encoding="utf-8", errors="replace")

        meta = LunarProductMetadata()
        meta.source_label_file = str(path)
        meta.format = "ENVI_HEADER"
        meta.sensor = "IIRS"
        meta.mission = "Chandrayaan-2"
        meta.image_id = path.stem
        meta.product_id = path.stem

        # Parse ENVI key = value syntax
        # Blocks are delimited by curly braces { ... }
        kv: Dict[str, str] = {}
        pattern = re.compile(r"^\s*([a-zA-Z0-9_\s]+)\s*=\s*(\{.*?\}|[^\n\r]+)", re.DOTALL | re.MULTILINE)

        for match in pattern.finditer(content):
            k = match.group(1).strip().lower()
            v = match.group(2).strip()
            if v.startswith("{") and v.endswith("}"):
                v = v[1:-1].strip()
            kv[k] = v

        meta.raw_metadata = kv

        # Dimensions
        if "samples" in kv:
            try:
                meta.width = int(kv["samples"])
            except ValueError:
                pass

        if "lines" in kv:
            try:
                meta.height = int(kv["lines"])
            except ValueError:
                pass

        if "bands" in kv:
            try:
                meta.number_of_bands = int(kv["bands"])
            except ValueError:
                pass

        # Data type
        # 1: 8-bit byte, 2: 16-bit signed int, 3: 32-bit signed int, 4: 32-bit float, 12: 16-bit unsigned int
        if "data type" in kv:
            dtype_code = kv["data type"].strip()
            if dtype_code == "1":
                meta.bit_depth = 8
            elif dtype_code in ["2", "12"]:
                meta.bit_depth = 16
            elif dtype_code in ["3", "4"]:
                meta.bit_depth = 32

        # Map info: e.g. map info = {Equirectangular, 1.0, 1.0, 80.0, 10.0, 80.0, 80.0, Moon_2000, units=Meters}
        if "map info" in kv:
            map_parts = [p.strip() for p in kv["map info"].split(",")]
            if len(map_parts) >= 7:
                meta.projection = map_parts[0]
                try:
                    meta.spatial_resolution = float(map_parts[5])
                except ValueError:
                    pass
                if len(map_parts) >= 8:
                    meta.datum = map_parts[7]

        # Coordinate system string
        if "coordinate system string" in kv:
            meta.crs = kv["coordinate system string"]

        # Description / Product level
        if "description" in kv:
            meta.product_level = kv["description"]

        return meta

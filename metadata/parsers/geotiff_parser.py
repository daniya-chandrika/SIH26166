"""
Scientific GeoTIFF / TIFF Metadata Parser.
Extracts raster geometry, bit depth, pixel scale, and georeferencing tags.
"""
from pathlib import Path
from typing import Optional, Dict, Any

from PIL import Image, TiffTags
from metadata.models import LunarProductMetadata, BoundingBox


class GeoTIFFParser:
    """
    Parses GeoTIFF and standard TIFF image metadata.
    """

    def parse(self, tiff_path: str | Path) -> LunarProductMetadata:
        path = Path(tiff_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"TIFF file not found: {path}")

        meta = LunarProductMetadata()
        meta.file_path = str(path)
        meta.filename = path.name
        meta.format = "GeoTIFF" if path.suffix.lower() in [".tif", ".tiff"] else "IMAGE"
        meta.image_id = path.stem
        meta.product_id = path.stem

        try:
            with Image.open(path) as img:
                meta.width = img.width
                meta.height = img.height

                # Number of bands
                mode = img.mode
                if mode in ["L", "I", "F", "I;16", "I;16B", "I;16L"]:
                    meta.number_of_bands = 1
                elif mode == "RGB":
                    meta.number_of_bands = 3
                elif mode == "RGBA":
                    meta.number_of_bands = 4
                else:
                    meta.number_of_bands = len(mode)

                # Bit depth
                if mode == "L":
                    meta.bit_depth = 8
                elif mode in ["I;16", "I;16B", "I;16L", "I"]:
                    meta.bit_depth = 16
                elif mode == "F":
                    meta.bit_depth = 32
                elif mode in ["RGB", "RGBA"]:
                    meta.bit_depth = 8

                # Extract TIFF tags if present
                if hasattr(img, "tag_v2"):
                    tags = img.tag_v2
                    # 258: BitsPerSample
                    if 258 in tags:
                        bps = tags[258]
                        meta.bit_depth = bps[0] if isinstance(bps, tuple) else int(bps)

                    # 277: SamplesPerPixel
                    if 277 in tags:
                        spp = tags[277]
                        meta.number_of_bands = int(spp)

                    # 33550: ModelPixelScaleTag (ScaleX, ScaleY, ScaleZ) in meters/pixel
                    if 33550 in tags:
                        scales = tags[33550]
                        if len(scales) >= 2:
                            meta.spatial_resolution = float(scales[0])

                    # 34737: GeoAsciiParamsTag
                    if 34737 in tags:
                        meta.projection = str(tags[34737]).strip("| \x00")
                        meta.crs = meta.projection

        except Exception as e:
            meta.raw_metadata["error"] = str(e)

        return meta

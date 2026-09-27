"""
Geospatial Footprint Intersection and Overlap Engine for Lunar Orbital Imagery (SIH26166).
Uses Shapely geometry to compute spatial intersection polygons, area, and overlap percentages.
"""
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from shapely.geometry import Polygon, box, mapping
from shapely.ops import unary_union
import json

from metadata.models import LunarProductMetadata
from geospatial.base import GeospatialValidatorBase, FootprintOverlapResult


class GeospatialFootprintValidator(GeospatialValidatorBase):
    """
    Validates orbital swath footprints, calculates polygon intersection,
    and computes overlap percentage across lunar coordinate frames.
    """

    def __init__(self, min_overlap_threshold: float = 15.0):
        self.min_overlap_threshold = min_overlap_threshold

    @staticmethod
    def _extract_polygon(meta: LunarProductMetadata) -> Optional[Polygon]:
        """
        Extract a Shapely Polygon from metadata bounding box, footprint GeoJSON, or center coordinates.
        """
        # 1. Check if explicit footprint GeoJSON is available
        if meta.footprint_geojson and isinstance(meta.footprint_geojson, dict):
            try:
                coords = meta.footprint_geojson.get("coordinates")
                if coords:
                    # If Polygon GeoJSON
                    if meta.footprint_geojson.get("type") == "Polygon":
                        return Polygon(coords[0])
                    elif meta.footprint_geojson.get("type") == "MultiPolygon":
                        return Polygon(coords[0][0])
            except Exception:
                pass

        # 2. Check bounding box (min_lat, max_lat, min_lon, max_lon)
        bbox = meta.bounding_box
        if bbox and len(bbox) == 4:
            min_lat, max_lat, min_lon, max_lon = bbox
            if min_lat is not None and max_lat is not None and min_lon is not None and max_lon is not None:
                # box(minx, miny, maxx, maxy) -> box(min_lon, min_lat, max_lon, max_lat)
                return box(min_lon, min_lat, max_lon, max_lat)

        # 3. Fallback to center coordinates with resolution-estimated footprint
        if meta.latitude is not None and meta.longitude is not None:
            lat, lon = meta.latitude, meta.longitude
            # Approximate angular span based on image dimensions and GSD if available
            # Moon radius ~ 1737.4 km -> 1 deg lat ~ 30.32 km
            km_per_deg = 30.32
            gsd = meta.spatial_resolution or 1.0  # meters/px
            width = meta.width or 1024
            height = meta.height or 1024
            
            span_x_km = (width * gsd) / 1000.0
            span_y_km = (height * gsd) / 1000.0
            
            d_lon = max(0.01, (span_x_km / (km_per_deg * max(0.1, np.cos(np.radians(lat)))))) / 2.0
            d_lat = max(0.01, (span_y_km / km_per_deg)) / 2.0
            
            return box(lon - d_lon, lat - d_lat, lon + d_lon, lat + d_lat)

        return None

    def compute_overlap(
        self,
        source_meta: LunarProductMetadata,
        reference_meta: LunarProductMetadata
    ) -> FootprintOverlapResult:
        """
        Calculate spatial intersection polygon and percentage overlap between two lunar products.
        """
        src_id = source_meta.image_id or source_meta.product_id or "UNKNOWN_SRC"
        ref_id = reference_meta.image_id or reference_meta.product_id or "UNKNOWN_REF"

        poly_src = self._extract_polygon(source_meta)
        poly_ref = self._extract_polygon(reference_meta)

        if poly_src is None or poly_ref is None:
            return FootprintOverlapResult(
                source_image_id=src_id,
                reference_image_id=ref_id,
                overlap_percentage=0.0,
                intersection_wkt=None,
                intersection_geojson=None,
                is_valid_pair=False,
                validation_message="Missing geodetic coordinates or footprint bounding box in one or both products."
            )

        # Make valid if self-intersecting
        if not poly_src.is_valid:
            poly_src = poly_src.buffer(0)
        if not poly_ref.is_valid:
            poly_ref = poly_ref.buffer(0)

        # Compute intersection
        try:
            intersection = poly_src.intersection(poly_ref)
        except Exception as e:
            return FootprintOverlapResult(
                source_image_id=src_id,
                reference_image_id=ref_id,
                overlap_percentage=0.0,
                intersection_wkt=None,
                intersection_geojson=None,
                is_valid_pair=False,
                validation_message=f"Geometric intersection error: {str(e)}"
            )

        if intersection.is_empty or intersection.area <= 0:
            return FootprintOverlapResult(
                source_image_id=src_id,
                reference_image_id=ref_id,
                overlap_percentage=0.0,
                intersection_wkt=None,
                intersection_geojson=None,
                is_valid_pair=False,
                validation_message="No spatial overlap detected between product footprints."
            )

        # Overlap percentage relative to smaller image (or source image)
        min_area = min(poly_src.area, poly_ref.area)
        overlap_pct = float((intersection.area / max(1e-12, min_area)) * 100.0)
        overlap_pct = min(100.0, max(0.0, overlap_pct))

        is_valid = overlap_pct >= self.min_overlap_threshold
        msg = (
            f"Valid geographic overlap of {overlap_pct:.2f}% (>= {self.min_overlap_threshold}%)."
            if is_valid else
            f"Insufficient geographic overlap of {overlap_pct:.2f}% (< {self.min_overlap_threshold}%)."
        )

        geojson_dict = mapping(intersection) if not intersection.is_empty else None

        return FootprintOverlapResult(
            source_image_id=src_id,
            reference_image_id=ref_id,
            overlap_percentage=round(overlap_pct, 4),
            intersection_wkt=intersection.wkt,
            intersection_geojson=geojson_dict,
            is_valid_pair=is_valid,
            validation_message=msg
        )

    def validate_same_terrain(
        self,
        source_meta: LunarProductMetadata,
        reference_meta: LunarProductMetadata,
        min_overlap_threshold: Optional[float] = None
    ) -> bool:
        threshold = min_overlap_threshold if min_overlap_threshold is not None else self.min_overlap_threshold
        res = self.compute_overlap(source_meta, reference_meta)
        return res.is_valid_pair and res.overlap_percentage >= threshold

    def find_candidate_pairs(
        self,
        products: List[LunarProductMetadata],
        min_overlap_pct: float = 15.0
    ) -> List[FootprintOverlapResult]:
        """
        Discover all viable cross-sensor candidate pairs from a catalog of products.
        """
        results: List[FootprintOverlapResult] = []
        n = len(products)
        for i in range(n):
            for j in range(i + 1, n):
                p1 = products[i]
                p2 = products[j]
                # Compare different sensors or orbital vs reference
                overlap_res = self.compute_overlap(p1, p2)
                if overlap_res.overlap_percentage >= min_overlap_pct:
                    results.append(overlap_res)
        return results

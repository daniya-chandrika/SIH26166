"""
Scientific Quality Assurance and Validation Checkers.
"""
from pathlib import Path
from typing import Optional, List, Tuple
import numpy as np
from PIL import Image

from metadata.models import LunarProductMetadata
from quality.models import QualityReportItem, QualityStatus, QualityMetrics, MissingMetadataFlags


class RasterQualityChecker:
    """
    Performs comprehensive quality assessment on lunar rasters and associated metadata.
    """

    def __init__(
        self,
        max_nodata_percent: float = 50.0,
        max_saturation_percent: float = 15.0,
        min_variance_threshold: float = 1e-4,
        warn_on_missing_angles: bool = True
    ):
        self.max_nodata_percent = max_nodata_percent
        self.max_saturation_percent = max_saturation_percent
        self.min_variance_threshold = min_variance_threshold
        self.warn_on_missing_angles = warn_on_missing_angles

    def evaluate(self, metadata: LunarProductMetadata) -> QualityReportItem:
        image_id = metadata.image_id or "UNKNOWN_IMAGE"
        product_id = metadata.product_id or "UNKNOWN_PRODUCT"
        sensor = metadata.sensor or "UNKNOWN_SENSOR"
        file_path = metadata.file_path

        item = QualityReportItem(
            image_id=image_id,
            product_id=product_id,
            sensor=sensor,
            file_path=file_path
        )

        # 1. Metadata completeness evaluation
        self._check_metadata_completeness(metadata, item)

        # 2. Raster data checks (if physical raster file is present)
        if file_path and Path(file_path).exists() and Path(file_path).is_file():
            self._check_raster_file(file_path, metadata, item)
        else:
            # If no raster file available (e.g. metadata-only label ingested)
            item.issues.append("Scientific raster file not found or not linked to metadata label")
            item.status = QualityStatus.WARNING
            item.quality_score *= 0.8

        # 3. Final status determination
        self._determine_final_status(item)

        return item

    def _check_metadata_completeness(self, meta: LunarProductMetadata, item: QualityReportItem) -> None:
        flags = item.missing_metadata_flags

        if meta.latitude is None or meta.longitude is None:
            flags.missing_coordinates = True
            item.issues.append("Missing center spatial coordinates (latitude/longitude)")

        if meta.incidence_angle is None and meta.sun_elevation is None:
            flags.missing_solar_angles = True
            if self.warn_on_missing_angles:
                item.issues.append("Missing solar/photometric geometry angles (incidence/sun elevation)")

        if meta.spatial_resolution is None:
            flags.missing_spatial_resolution = True
            item.issues.append("Missing spatial resolution (meters/pixel)")

        if meta.acquisition_date is None:
            flags.missing_acquisition_time = True
            item.issues.append("Missing acquisition timestamp/date")

        # Deductions
        if flags.missing_coordinates:
            item.quality_score -= 0.15
        if flags.missing_solar_angles:
            item.quality_score -= 0.10
        if flags.missing_spatial_resolution:
            item.quality_score -= 0.10
        if flags.missing_acquisition_time:
            item.quality_score -= 0.05

    def _check_raster_file(self, file_path: str, meta: LunarProductMetadata, item: QualityReportItem) -> None:
        path = Path(file_path)
        ext = path.suffix.lower()

        # Handle standard raster formats with PIL / Numpy
        if ext in [".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"]:
            try:
                with Image.open(path) as img:
                    item.is_readable = True
                    arr = np.array(img, dtype=np.float64)

                    # Total pixels
                    total_pixels = arr.size
                    if total_pixels == 0:
                        item.is_blank = True
                        item.issues.append("Raster has 0 total pixels (empty raster)")
                        item.quality_score = 0.0
                        return

                    # Invalid values check (NaN, Inf)
                    has_nan = np.isnan(arr).any()
                    has_inf = np.isinf(arr).any()
                    if has_nan or has_inf:
                        item.has_invalid_values = True
                        item.issues.append("Raster contains NaN or Infinite pixel values")
                        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

                    # Compute statistics
                    min_val = float(np.min(arr))
                    max_val = float(np.max(arr))
                    mean_val = float(np.mean(arr))
                    std_val = float(np.std(arr))
                    variance_val = float(np.var(arr))

                    # Blank image check
                    if variance_val < self.min_variance_threshold or min_val == max_val:
                        item.is_blank = True
                        item.issues.append(f"Image appears blank / uniform with zero variance ({variance_val:.6f})")
                        item.quality_score -= 0.6

                    # NoData percentage (pixels == 0 or nodata)
                    nodata_count = int(np.sum(arr == 0))
                    nodata_pct = (nodata_count / total_pixels) * 100.0

                    # Saturation percentage
                    bit_depth = meta.bit_depth or 8
                    sat_val = (2 ** bit_depth) - 1 if bit_depth in [8, 16] else max_val
                    sat_count = int(np.sum(arr >= sat_val)) if sat_val > 0 else 0
                    sat_pct = (sat_count / total_pixels) * 100.0

                    if nodata_pct > self.max_nodata_percent:
                        item.issues.append(f"High NoData percentage: {nodata_pct:.1f}% (threshold: {self.max_nodata_percent}%)")
                        item.quality_score -= min(0.4, (nodata_pct / 100.0) * 0.5)

                    if sat_pct > self.max_saturation_percent:
                        item.issues.append(f"High pixel saturation: {sat_pct:.1f}% (threshold: {self.max_saturation_percent}%)")
                        item.quality_score -= min(0.3, (sat_pct / 100.0) * 0.4)

                    item.metrics = QualityMetrics(
                        nodata_percentage=nodata_pct,
                        saturation_percentage=sat_pct,
                        mean_dn=mean_val,
                        std_dn=std_val,
                        min_dn=min_val,
                        max_dn=max_val,
                        variance=variance_val,
                        total_pixels=total_pixels,
                        valid_pixels=total_pixels - nodata_count
                    )

            except Exception as e:
                item.is_corrupted = True
                item.is_readable = False
                item.issues.append(f"Corrupted or unreadable image raster: {str(e)}")
                item.quality_score = 0.0

        elif ext in [".dat", ".img", ".cub"]:
            # For raw / binary / ENVI / ISIS cubes
            try:
                size_bytes = path.stat().st_size
                if size_bytes == 0:
                    item.is_corrupted = True
                    item.is_readable = False
                    item.issues.append("Binary raster file has 0 bytes (empty file)")
                    item.quality_score = 0.0
                else:
                    item.is_readable = True
                    # Check if file size matches dimensions from metadata
                    if meta.width and meta.height and meta.bit_depth and meta.number_of_bands:
                        expected_bytes = meta.width * meta.height * meta.number_of_bands * (meta.bit_depth // 8)
                        if size_bytes < expected_bytes:
                            item.issues.append(f"Binary file size ({size_bytes} bytes) is smaller than expected dimensions ({expected_bytes} bytes)")
                            item.quality_score -= 0.3
            except Exception as e:
                item.is_corrupted = True
                item.issues.append(f"Error inspecting binary raster: {str(e)}")
                item.quality_score = 0.0

    def _determine_final_status(self, item: QualityReportItem) -> None:
        item.quality_score = max(0.0, min(1.0, item.quality_score))

        if item.is_corrupted or not item.is_readable or item.metrics.nodata_percentage >= 90.0:
            item.status = QualityStatus.FAIL
        elif item.issues or item.quality_score < 0.85:
            item.status = QualityStatus.WARNING
        else:
            item.status = QualityStatus.PASS

"""
Manifest to Supabase Database Synchronizer.
Synchronizes dataset_manifest.json / dataset_manifest.csv with Supabase tables without data loss.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

import pandas as pd
from database.repository import SupabaseLunarRepository
from database.models import (
    ImageRecord, ImageMetadataRecord, ImageQualityRecord, ImageStatus
)
from storage.manager import SupabaseStorageManager


class ManifestSynchronizer:
    """
    Synchronizes local manifest files with Supabase PostgreSQL database.
    """

    def __init__(
        self,
        repository: Optional[SupabaseLunarRepository] = None,
        storage_manager: Optional[SupabaseStorageManager] = None
    ):
        self.repo = repository or SupabaseLunarRepository()
        self.storage = storage_manager or SupabaseStorageManager()

    def sync_manifest(
        self,
        manifest_path: Union[str, Path] = "./reports/dataset_manifest.json",
        default_region_code: str = "R01"
    ) -> Dict[str, Any]:
        """
        Synchronize a manifest file with Supabase tables.
        """
        path = Path(manifest_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {path}")

        records: List[Dict[str, Any]] = []
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                records = data.get("products", [])
        elif path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
            records = df.to_dict(orient="records")
        else:
            raise ValueError(f"Unsupported manifest format: {path.suffix}")

        summary = {
            "total_records": len(records),
            "inserted_images": 0,
            "skipped_duplicates": 0,
            "metadata_synced": 0,
            "errors": []
        }

        # Ensure target region exists
        reg = self.repo.get_or_create_region(default_region_code)
        region_id = reg["id"]

        for prod in records:
            try:
                img_id = str(prod.get("image_id") or Path(str(prod.get("filename", "unknown"))).stem).lower()
                sensor = str(prod.get("sensor", "OHRC")).upper().replace("_", "-")
                filename = str(prod.get("filename") or f"{img_id}.tif")
                sha256_hash = prod.get("archive_sha256") or prod.get("sha256") or f"manifest_hash_{img_id}"

                existing_img = self.repo.find_image_by_sha256(sha256_hash)
                if existing_img:
                    summary["skipped_duplicates"] += 1
                    db_image_id = existing_img["id"]
                else:
                    storage_path = self.storage.build_raw_path(default_region_code, sensor, filename)
                    img_rec = ImageRecord(
                        image_id=img_id,
                        region_id=region_id,
                        sensor=sensor,
                        image_type="reference" if "LROC" in sensor else "orbital",
                        file_name=filename,
                        storage_path=storage_path,
                        file_format=str(prod.get("format", "GeoTIFF")),
                        product_id=str(prod.get("product_id", img_id)),
                        product_level=prod.get("product_level"),
                        file_size_bytes=int(prod.get("file_size_bytes", 0)),
                        sha256=sha256_hash,
                        status=ImageStatus.VALIDATED
                    )
                    db_img = self.repo.insert_image(img_rec)
                    db_image_id = db_img["id"]
                    summary["inserted_images"] += 1

                # Sync metadata if not already recorded
                existing_meta = self.repo.get_metadata_by_image_id(db_image_id)
                if not existing_meta:
                    meta_rec = ImageMetadataRecord(
                        image_id=db_image_id,
                        width_px=int(prod["width"]) if prod.get("width") and pd.notna(prod.get("width")) else None,
                        height_px=int(prod["height"]) if prod.get("height") and pd.notna(prod.get("height")) else None,
                        bit_depth=int(prod["bit_depth"]) if prod.get("bit_depth") and pd.notna(prod.get("bit_depth")) else None,
                        band_count=int(prod["number_of_bands"]) if prod.get("number_of_bands") and pd.notna(prod.get("number_of_bands")) else 1,
                        spatial_resolution_m=float(prod["spatial_resolution"]) if prod.get("spatial_resolution") and pd.notna(prod.get("spatial_resolution")) else None,
                        latitude=float(prod["latitude"]) if prod.get("latitude") and pd.notna(prod.get("latitude")) else None,
                        longitude=float(prod["longitude"]) if prod.get("longitude") and pd.notna(prod.get("longitude")) else None,
                        acquisition_date=str(prod["acquisition_date"]) if prod.get("acquisition_date") and pd.notna(prod.get("acquisition_date")) else None,
                        acquisition_time=str(prod["acquisition_time"]) if prod.get("acquisition_time") and pd.notna(prod.get("acquisition_time")) else None,
                        sun_elevation_deg=float(prod["sun_elevation"]) if prod.get("sun_elevation") and pd.notna(prod.get("sun_elevation")) else None,
                        sun_azimuth_deg=float(prod["sun_azimuth"]) if prod.get("sun_azimuth") and pd.notna(prod.get("sun_azimuth")) else None,
                        incidence_angle_deg=float(prod["incidence_angle"]) if prod.get("incidence_angle") and pd.notna(prod.get("incidence_angle")) else None,
                        emission_angle_deg=float(prod["emission_angle"]) if prod.get("emission_angle") and pd.notna(prod.get("emission_angle")) else None,
                        phase_angle_deg=float(prod["phase_angle"]) if prod.get("phase_angle") and pd.notna(prod.get("phase_angle")) else None,
                        look_angle_deg=float(prod["look_angle"]) if prod.get("look_angle") and pd.notna(prod.get("look_angle")) else None,
                        projection=str(prod["projection"]) if prod.get("projection") and pd.notna(prod.get("projection")) else None,
                        crs=str(prod["crs"]) if prod.get("crs") and pd.notna(prod.get("crs")) else None,
                        footprint=str(prod["footprint"]) if prod.get("footprint") and pd.notna(prod.get("footprint")) else None
                    )
                    self.repo.insert_image_metadata(meta_rec)
                    summary["metadata_synced"] += 1

            except Exception as e:
                summary["errors"].append(f"Error syncing product '{prod.get('image_id')}': {str(e)}")

        return summary

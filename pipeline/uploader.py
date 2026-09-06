"""
Supabase Lunar Dataset Ingestion & Upload Pipeline.
Implements pre-upload hashing, duplicate detection, sensor verification, storage upload, and DB cataloging.
"""
from pathlib import Path
from typing import Optional, Dict, Any, Union

from ingestion.models import SensorType
from ingestion.validator import calculate_sha256, validate_zip_archive
from ingestion.extractor import ArchiveExtractor
from ingestion.inspector import ArchiveInspector
from metadata.extractor import MetadataExtractor
from quality.checkers import RasterQualityChecker
from storage.manager import SupabaseStorageManager
from database.repository import SupabaseLunarRepository
from database.models import (
    ImageRecord, ImageMetadataRecord, ImageQualityRecord,
    ImageFootprintRecord, ImageStatus
)


class LunarDatasetUploader:
    """
    Coordinates the full end-to-end ingestion, storage upload, and database cataloging lifecycle.
    """

    def __init__(
        self,
        storage_manager: Optional[SupabaseStorageManager] = None,
        repository: Optional[SupabaseLunarRepository] = None,
        temp_extract_dir: str | Path = "./data/extracted"
    ):
        self.storage = storage_manager or SupabaseStorageManager()
        self.repo = repository or SupabaseLunarRepository()
        self.extractor = ArchiveExtractor(extracted_store_dir=temp_extract_dir)
        self.inspector = ArchiveInspector()
        self.metadata_extractor = MetadataExtractor()
        self.quality_checker = RasterQualityChecker()

    def upload_dataset(
        self,
        archive_path: Union[str, Path],
        region_code: str,
        sensor: Union[str, SensorType],
        image_type: str = "orbital"
    ) -> Dict[str, Any]:
        """
        Execute the robust upload lifecycle:
          ZIP -> SHA-256 -> Duplicate Check -> Storage Upload -> DB Records -> QC -> Status
        """
        path = Path(archive_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Archive file not found: {path}")

        sensor_enum = sensor if isinstance(sensor, SensorType) else SensorType.from_string(str(sensor))
        reg_code = region_code.strip().upper()

        # Step 1: Calculate SHA-256 Checksum
        sha256_hash = calculate_sha256(path)

        # Step 2: Duplicate File Detection
        existing_image = self.repo.find_image_by_sha256(sha256_hash)
        if existing_image:
            return {
                "status": "DUPLICATE_FILE",
                "message": f"File with SHA-256 '{sha256_hash}' already exists in database.",
                "image_id": existing_image["image_id"],
                "existing_record": existing_image,
                "sha256": sha256_hash,
                "region_code": reg_code,
                "sensor": sensor_enum.value
            }

        # Step 3: Validate ZIP Integrity
        val_result = validate_zip_archive(path)
        if not val_result.is_valid:
            raise ValueError(f"ZIP validation failed: {val_result.error_message}")

        # Step 4: Ensure Region exists in DB
        region = self.repo.get_or_create_region(reg_code)
        region_id = region["id"]

        # Step 5: Upload original archive to Supabase Storage (lunar-raw/Rxx/SENSOR/filename)
        storage_upload_res = self.storage.upload_raw_archive(
            archive_path=path,
            region_code=reg_code,
            sensor=sensor_enum
        )
        storage_rel_path = storage_upload_res["storage_path"]

        # Step 6: Create initial Database Image Record (status='UPLOADED')
        img_id = path.stem.lower()
        image_rec = ImageRecord(
            image_id=img_id,
            region_id=region_id,
            sensor=sensor_enum.value,
            image_type="reference" if sensor_enum == SensorType.LROC else image_type,
            file_name=path.name,
            storage_path=storage_rel_path,
            file_format="ZIP",
            product_id=img_id,
            file_size_bytes=path.stat().st_size,
            sha256=sha256_hash,
            status=ImageStatus.UPLOADED
        )
        db_image = self.repo.insert_image(image_rec)
        db_image_id = db_image["id"]

        self.repo.log_processing_step(
            stage="STORAGE_UPLOAD",
            status="SUCCESS",
            message=f"Uploaded raw ZIP to storage: {storage_rel_path}",
            image_db_id=db_image_id
        )

        # Step 7: Safe Extraction & Local Inspection
        _, extract_dir = self.extractor.extract(path, sensor=sensor_enum, preserve_in_raw=True)
        ing_result = self.inspector.inspect(
            extract_dir=extract_dir,
            sensor=sensor_enum,
            archive_path=path,
            archive_sha256=sha256_hash
        )

        # Step 8: Metadata Extraction & Verification
        extracted_metas = self.metadata_extractor.extract_from_ingestion(ing_result)
        primary_meta = extracted_metas[0] if extracted_metas else None

        # Check for sensor mismatch
        sensor_warning = None
        if primary_meta and primary_meta.sensor and primary_meta.sensor.upper() != sensor_enum.value.upper():
            sensor_warning = f"Sensor mismatch warning: User selected '{sensor_enum.value}' but label indicates '{primary_meta.sensor}'"
            self.repo.log_processing_step(
                stage="SENSOR_VERIFICATION",
                status="WARNING",
                message=sensor_warning,
                image_db_id=db_image_id
            )

        db_metadata_res = None
        if primary_meta:
            meta_rec = ImageMetadataRecord(
                image_id=db_image_id,
                width_px=primary_meta.width,
                height_px=primary_meta.height,
                bit_depth=primary_meta.bit_depth,
                band_count=primary_meta.number_of_bands or 1,
                spatial_resolution_m=primary_meta.spatial_resolution,
                latitude=primary_meta.latitude,
                longitude=primary_meta.longitude,
                acquisition_date=primary_meta.acquisition_date,
                acquisition_time=primary_meta.acquisition_time,
                sun_elevation_deg=primary_meta.sun_elevation,
                sun_azimuth_deg=primary_meta.sun_azimuth,
                incidence_angle_deg=primary_meta.incidence_angle,
                emission_angle_deg=primary_meta.emission_angle,
                phase_angle_deg=primary_meta.phase_angle,
                look_angle_deg=primary_meta.look_angle,
                projection=primary_meta.projection,
                crs=primary_meta.crs,
                footprint=primary_meta.footprint,
                raw_metadata_json=primary_meta.raw_metadata
            )
            db_metadata_res = self.repo.insert_image_metadata(meta_rec)

            if primary_meta.bounding_box:
                bb = primary_meta.bounding_box
                footprint_rec = ImageFootprintRecord(
                    image_id=db_image_id,
                    min_latitude=bb.min_latitude,
                    max_latitude=bb.max_latitude,
                    min_longitude=bb.min_longitude,
                    max_longitude=bb.max_longitude,
                    footprint_source="PDS_LABEL"
                )
                self.repo.insert_image_footprint(footprint_rec)

            self.repo.update_image_status(db_image_id, ImageStatus.INGESTED)

        # Step 9: Quality Control
        quality_item = None
        db_quality_res = None
        if primary_meta:
            quality_item = self.quality_checker.evaluate(primary_meta)
            qual_rec = ImageQualityRecord(
                image_id=db_image_id,
                readable=quality_item.is_readable,
                corrupted=quality_item.is_corrupted,
                nodata_percentage=quality_item.metrics.nodata_percentage,
                saturation_percentage=quality_item.metrics.saturation_percentage,
                blank_image=quality_item.is_blank,
                quality_status=quality_item.status.value,
                quality_flags=quality_item.missing_metadata_flags.to_dict()
            )
            db_quality_res = self.repo.insert_image_quality(qual_rec)

            final_status = ImageStatus.VALIDATED if quality_item.status.value == "PASS" else ImageStatus.WARNING
            if quality_item.status.value == "FAIL":
                final_status = ImageStatus.FAILED

            self.repo.update_image_status(db_image_id, final_status)
            self.repo.log_processing_step(
                stage="QUALITY_CONTROL",
                status=quality_item.status.value,
                message=f"QC evaluated: status={quality_item.status.value}, score={quality_item.quality_score:.2f}",
                image_db_id=db_image_id
            )

        return {
            "status": "SUCCESS",
            "image_id": img_id,
            "db_image_id": db_image_id,
            "region_code": reg_code,
            "sensor": sensor_enum.value,
            "storage_path": storage_rel_path,
            "sha256": sha256_hash,
            "metadata_recorded": db_metadata_res is not None,
            "quality_status": quality_item.status.value if quality_item else "UNKNOWN",
            "sensor_warning": sensor_warning
        }

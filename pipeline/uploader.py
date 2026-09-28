"""
Supabase Lunar Dataset Ingestion & Upload Pipeline.
Implements pre-upload hashing, duplicate detection, sensor verification, storage upload, and DB cataloging.
"""
from pathlib import Path
from typing import Optional, Dict, Any, Union

from ingestion.models import SensorType, IngestionResult, ExtractedFileInfo, FileCategory
from ingestion.validator import calculate_sha256, validate_zip_archive
from ingestion.extractor import ArchiveExtractor
from ingestion.inspector import ArchiveInspector, classify_file
from ingestion.detector import LunarSensorDetector
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
        region_code: str = "R01",
        sensor: Optional[Union[str, SensorType]] = None,
        image_type: str = "orbital"
    ) -> Dict[str, Any]:
        """
        Execute the robust upload lifecycle:
          File/ZIP -> SHA-256 -> Duplicate Check -> Sensor Detection -> Storage -> DB Records -> QC -> Status
        """
        path = Path(archive_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File or archive not found: {path}")

        reg_code = (region_code or "R01").strip().upper()

        # Step 1: Calculate SHA-256 Checksum
        sha256_hash = calculate_sha256(path)

        # Step 2: Duplicate File Detection
        existing_image = self.repo.find_image_by_sha256(sha256_hash)
        if existing_image:
            meta_exist = self.repo.get_metadata_by_image_id(existing_image["id"]) or {}
            qual_exist = self.repo.get_quality_by_image_id(existing_image["id"]) or {}
            return {
                "status": "DUPLICATE_FILE",
                "message": f"File with SHA-256 '{sha256_hash}' already exists in database.",
                "image_id": existing_image["image_id"],
                "product_id": existing_image.get("product_id", existing_image["image_id"]),
                "existing_record": existing_image,
                "sha256": sha256_hash,
                "region_code": reg_code,
                "sensor": existing_image.get("sensor", "OHRC"),
                "mission": "Chandrayaan-2" if existing_image.get("sensor") in ["OHRC", "TMC-2", "IIRS"] else "LRO",
                "metadata": meta_exist,
                "quality": qual_exist,
                "created_at": existing_image.get("created_at"),
                "storage_path": existing_image.get("storage_path")
            }

        # Step 3: Sensor Auto-Detection if not explicitly supplied or set to AUTO
        detected_sensor = None
        detection_reason = "User specified"
        if not sensor or str(sensor).upper() in ["AUTO", "AUTO_DETECT", "AUTODETECT", "NONE"]:
            detected_sensor, conf, detection_reason = LunarSensorDetector.detect_sensor(path)
            sensor_enum = detected_sensor
        else:
            sensor_enum = sensor if isinstance(sensor, SensorType) else SensorType.from_string(str(sensor))

        is_zip = path.suffix.lower() == ".zip"

        # Step 4: Validate ZIP Integrity (if ZIP)
        if is_zip:
            val_result = validate_zip_archive(path)
            if not val_result.is_valid:
                raise ValueError(f"ZIP validation failed: {val_result.error_message}")

        # Step 5: Ensure Region exists in DB
        region = self.repo.get_or_create_region(reg_code)
        region_id = region["id"]

        # Step 5: Upload original archive/file to Supabase Storage (lunar-raw/Rxx/SENSOR/filename)
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
            file_format="ZIP" if is_zip else path.suffix.upper().replace(".", ""),
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
            message=f"Uploaded raw dataset to storage: {storage_rel_path}",
            image_db_id=db_image_id
        )

        # Step 7: Safe Extraction & Local Inspection
        if is_zip:
            _, extract_dir = self.extractor.extract(path, sensor=sensor_enum, preserve_in_raw=True)
        else:
            import shutil
            extract_dir = Path("./data/extracted") / sensor_enum.value / img_id
            extract_dir.mkdir(parents=True, exist_ok=True)
            dest_file = extract_dir / path.name
            if path.resolve() != dest_file.resolve():
                shutil.copy2(path, dest_file)

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
                if hasattr(bb, "min_latitude"):
                    min_lt = bb.min_latitude
                    max_lt = bb.max_latitude
                    min_ln = bb.min_longitude
                    max_ln = bb.max_longitude
                elif isinstance(bb, (list, tuple)) and len(bb) >= 4:
                    min_lt, max_lt, min_ln, max_ln = bb[0], bb[1], bb[2], bb[3]
                else:
                    min_lt = max_lt = min_ln = max_ln = None

                footprint_rec = ImageFootprintRecord(
                    image_id=db_image_id,
                    min_latitude=min_lt,
                    max_latitude=max_lt,
                    min_longitude=min_ln,
                    max_longitude=max_ln,
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

        # Build comprehensive product card data
        bbox_list = None
        if primary_meta and primary_meta.bounding_box:
            bb = primary_meta.bounding_box
            if hasattr(bb, "min_latitude"):
                bbox_list = [bb.min_latitude, bb.max_latitude, bb.min_longitude, bb.max_longitude]
            elif isinstance(bb, (list, tuple)) and len(bb) >= 4:
                bbox_list = [bb[0], bb[1], bb[2], bb[3]]

        return {
            "status": "SUCCESS",
            "image_id": img_id,
            "product_id": primary_meta.product_id if primary_meta and primary_meta.product_id else img_id,
            "db_image_id": db_image_id,
            "region_code": reg_code,
            "sensor": sensor_enum.value,
            "mission": primary_meta.mission if primary_meta and primary_meta.mission else ("Chandrayaan-2" if sensor_enum.value in ["OHRC", "TMC-2", "IIRS"] else "LRO"),
            "storage_path": storage_rel_path,
            "sha256": sha256_hash,
            "spatial_resolution": primary_meta.spatial_resolution if primary_meta else None,
            "latitude": primary_meta.latitude if primary_meta else None,
            "longitude": primary_meta.longitude if primary_meta else None,
            "bounding_box": bbox_list,
            "width": primary_meta.width if primary_meta else None,
            "height": primary_meta.height if primary_meta else None,
            "bit_depth": primary_meta.bit_depth if primary_meta else None,
            "quality_status": quality_item.status.value if quality_item else "PASS",
            "quality_score": quality_item.quality_score if quality_item else 1.0,
            "metadata_recorded": db_metadata_res is not None,
            "quality_recorded": db_quality_res is not None,
            "footprint_available": primary_meta.footprint is not None if primary_meta else False,
            "sensor_detection": {
                "detected": detected_sensor.value if detected_sensor else sensor_enum.value,
                "reason": detection_reason
            },
            "sensor_warning": sensor_warning
        }

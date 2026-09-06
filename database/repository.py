"""
Data Repository for Supabase Database Operations.
Implements CRUD, duplicate queries, and atomic state transitions for all 8 tables.
"""
from typing import Optional, Dict, Any, List

from database.connection import SupabaseDBConnection
from database.models import (
    RegionRecord, ImageRecord, ImageMetadataRecord,
    ImageQualityRecord, ImageFootprintRecord, ImagePairRecord,
    ProcessingLogRecord, ImageStatus
)


class SupabaseLunarRepository:
    """
    Scientific Lunar Dataset Repository backed by Supabase PostgreSQL.
    """

    def __init__(self, db_connection: Optional[SupabaseDBConnection] = None):
        self.db = db_connection or SupabaseDBConnection()

    # --------------------------------------------------------------------------
    # REGIONS
    # --------------------------------------------------------------------------
    def get_region_by_code(self, region_code: str) -> Optional[Dict[str, Any]]:
        code = region_code.strip().upper()
        results = self.db.select("regions", {"region_code": f"eq.{code}"} if not self.db.use_mock else {"region_code": code})
        return results[0] if results else None

    def get_region_by_id(self, region_id: str) -> Optional[Dict[str, Any]]:
        results = self.db.select("regions", {"id": f"eq.{region_id}"} if not self.db.use_mock else {"id": region_id})
        return results[0] if results else None

    def get_all_regions(self) -> List[Dict[str, Any]]:
        return self.db.select("regions")

    def get_or_create_region(
        self,
        region_code: str,
        region_name: Optional[str] = None,
        description: Optional[str] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None
    ) -> Dict[str, Any]:
        existing = self.get_region_by_code(region_code)
        if existing:
            return existing

        rec = RegionRecord(
            region_code=region_code.strip().upper(),
            region_name=region_name or f"Lunar Target Region {region_code.upper()}",
            description=description or f"Dynamically initialized region {region_code.upper()}",
            center_latitude=center_lat,
            center_longitude=center_lon
        )
        res = self.db.insert("regions", rec.to_dict())
        return res[0]

    # --------------------------------------------------------------------------
    # IMAGES & DUPLICATE DETECTION
    # --------------------------------------------------------------------------
    def find_image_by_sha256(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        """
        Check if a file with this SHA-256 already exists in the database.
        """
        sha = sha256_hash.strip().lower()
        results = self.db.select("images", {"sha256": f"eq.{sha}"} if not self.db.use_mock else {"sha256": sha})
        return results[0] if results else None

    def find_image_by_image_id(self, image_id: str) -> Optional[Dict[str, Any]]:
        results = self.db.select("images", {"image_id": f"eq.{image_id}"} if not self.db.use_mock else {"image_id": image_id})
        return results[0] if results else None

    def get_images_by_region(self, region_id: str) -> List[Dict[str, Any]]:
        return self.db.select("images", {"region_id": f"eq.{region_id}"} if not self.db.use_mock else {"region_id": region_id})

    def get_all_images(self) -> List[Dict[str, Any]]:
        return self.db.select("images")

    def insert_image(self, record: ImageRecord) -> Dict[str, Any]:
        res = self.db.insert("images", record.to_dict())
        return res[0]

    def update_image_status(
        self,
        image_db_id: str,
        status: ImageStatus,
        assigned_to: Optional[str] = None,
        processing_owner: Optional[str] = None,
        clear_processing_owner: bool = False,
        last_processed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        update_data: Dict[str, Any] = {"status": status.value if isinstance(status, ImageStatus) else str(status)}
        if assigned_to is not None:
            update_data["assigned_to"] = assigned_to
        if clear_processing_owner:
            update_data["processing_owner"] = None
        elif processing_owner is not None:
            update_data["processing_owner"] = processing_owner
        if last_processed_by is not None:
            update_data["last_processed_by"] = last_processed_by

        match_param = {"id": f"eq.{image_db_id}"} if not self.db.use_mock else {"id": image_db_id}
        res = self.db.update("images", update_data, match_param)
        return res[0] if res else {}

    # --------------------------------------------------------------------------
    # METADATA & QUALITY
    # --------------------------------------------------------------------------
    def insert_image_metadata(self, record: ImageMetadataRecord) -> Dict[str, Any]:
        res = self.db.insert("image_metadata", record.to_dict())
        return res[0]

    def get_metadata_by_image_id(self, image_db_id: str) -> Optional[Dict[str, Any]]:
        results = self.db.select("image_metadata", {"image_id": f"eq.{image_db_id}"} if not self.db.use_mock else {"image_id": image_db_id})
        return results[0] if results else None

    def insert_image_quality(self, record: ImageQualityRecord) -> Dict[str, Any]:
        res = self.db.insert("image_quality", record.to_dict())
        return res[0]

    def get_quality_by_image_id(self, image_db_id: str) -> Optional[Dict[str, Any]]:
        results = self.db.select("image_quality", {"image_id": f"eq.{image_db_id}"} if not self.db.use_mock else {"image_id": image_db_id})
        return results[0] if results else None

    def insert_image_footprint(self, record: ImageFootprintRecord) -> Dict[str, Any]:
        res = self.db.insert("image_footprints", record.to_dict())
        return res[0]

    # --------------------------------------------------------------------------
    # LOGS & EXPERIMENTS
    # --------------------------------------------------------------------------
    def log_processing_step(
        self,
        stage: str,
        status: str,
        message: str,
        image_db_id: Optional[str] = None,
        experiment_db_id: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        rec = ProcessingLogRecord(
            stage=stage,
            status=status,
            message=message,
            image_id=image_db_id,
            experiment_id=experiment_db_id,
            error_details=error_details
        )
        res = self.db.insert("processing_logs", rec.to_dict())
        return res[0]

"""
Dataset Download and Retrieval API.
Provides secure signed URLs and metadata bundles for team members.
"""
from typing import Optional, Dict, Any, Union

from ingestion.models import SensorType
from database.repository import SupabaseLunarRepository
from storage.manager import SupabaseStorageManager


class DatasetDownloader:
    """
    Retrieves dataset records and generates time-limited signed download URLs.
    """

    def __init__(
        self,
        repository: Optional[SupabaseLunarRepository] = None,
        storage_manager: Optional[SupabaseStorageManager] = None
    ):
        self.repo = repository or SupabaseLunarRepository()
        self.storage = storage_manager or SupabaseStorageManager()

    def get_dataset(
        self,
        region_code: str,
        sensor: Union[str, SensorType],
        expires_in_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        Retrieve image metadata, storage location, and a secure signed download URL for team members.
        """
        reg_code = region_code.strip().upper()
        sensor_val = sensor.value if isinstance(sensor, SensorType) else str(sensor).upper()

        region = self.repo.get_region_by_code(reg_code)
        if not region:
            raise ValueError(f"Region '{reg_code}' not found in database.")

        region_id = region["id"]
        images = self.repo.get_images_by_region(region_id)

        target_img = None
        for img in images:
            img_s = img["sensor"].upper().replace("_", "-")
            if img_s == sensor_val or sensor_val in img_s:
                target_img = img
                break

        if not target_img:
            raise FileNotFoundError(f"No product found for sensor '{sensor_val}' in region '{reg_code}'.")

        db_image_id = target_img["id"]
        metadata = self.repo.get_metadata_by_image_id(db_image_id)
        quality = self.repo.get_quality_by_image_id(db_image_id)

        # Generate signed URL
        storage_path = target_img["storage_path"]
        signed_url = self.storage.generate_signed_url(
            bucket=self.storage.BUCKET_RAW,
            storage_path=storage_path,
            expires_in_seconds=expires_in_seconds
        )

        return {
            "image_id": target_img["image_id"],
            "product_id": target_img["product_id"],
            "sensor": target_img["sensor"],
            "region_code": reg_code,
            "region_name": region["region_name"],
            "file_name": target_img["file_name"],
            "storage_path": storage_path,
            "download_url": signed_url,
            "url_expires_in_seconds": expires_in_seconds,
            "processing_status": target_img["status"],
            "assigned_to": target_img.get("assigned_to"),
            "file_size_bytes": target_img["file_size_bytes"],
            "sha256": target_img["sha256"],
            "metadata": metadata or {},
            "quality": quality or {}
        }

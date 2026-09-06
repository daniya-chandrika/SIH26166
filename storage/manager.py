"""
Supabase Storage Manager.
Manages bucket hierarchies, dynamic region paths, archive uploads, and signed download URLs.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union

from ingestion.models import SensorType
from storage.client import SupabaseAPIClient
from storage.emulator import MockSupabaseStorage


class SupabaseStorageManager:
    """
    Manages structured storage paths in Supabase Object Storage:
      - lunar-raw/<region_code>/<sensor>/<filename>
      - lunar-metadata/<region_code>/<sensor>/<filename>
      - lunar-processed/<region_code>/<sensor>/<filename>
      - lunar-results/<experiment_id>/<filename>
    """

    BUCKET_RAW = os.getenv("STORAGE_BUCKET_RAW", "lunar-raw")
    BUCKET_METADATA = os.getenv("STORAGE_BUCKET_METADATA", "lunar-metadata")
    BUCKET_PROCESSED = os.getenv("STORAGE_BUCKET_PROCESSED", "lunar-processed")
    BUCKET_RESULTS = os.getenv("STORAGE_BUCKET_RESULTS", "lunar-results")

    def __init__(
        self,
        api_client: Optional[SupabaseAPIClient] = None,
        use_mock: bool = False,
        mock_storage: Optional[MockSupabaseStorage] = None
    ):
        self.client = api_client or SupabaseAPIClient()
        self.use_mock = use_mock or (not self.client.is_configured)
        self.mock_storage = mock_storage or MockSupabaseStorage()

    @staticmethod
    def normalize_sensor_folder(sensor: Union[str, SensorType]) -> str:
        s_val = sensor.value if isinstance(sensor, SensorType) else str(sensor)
        return s_val.replace("-", "")  # 'TMC-2' -> 'TMC2', 'OHRC' -> 'OHRC', etc.

    @classmethod
    def build_raw_path(cls, region_code: str, sensor: Union[str, SensorType], filename: str) -> str:
        reg = region_code.strip().upper()
        s_folder = cls.normalize_sensor_folder(sensor)
        return f"{reg}/{s_folder}/{Path(filename).name}"

    @classmethod
    def build_metadata_path(cls, region_code: str, sensor: Union[str, SensorType], filename: str) -> str:
        reg = region_code.strip().upper()
        s_folder = cls.normalize_sensor_folder(sensor)
        return f"{reg}/{s_folder}/{Path(filename).name}"

    @classmethod
    def build_processed_path(cls, region_code: str, sensor: Union[str, SensorType], filename: str) -> str:
        reg = region_code.strip().upper()
        s_folder = cls.normalize_sensor_folder(sensor)
        return f"{reg}/{s_folder}/{Path(filename).name}"

    @classmethod
    def build_results_path(cls, experiment_id: str, filename: str) -> str:
        exp = experiment_id.strip()
        return f"{exp}/{Path(filename).name}"

    def upload_raw_archive(
        self,
        archive_path: Union[str, Path],
        region_code: str,
        sensor: Union[str, SensorType]
    ) -> Dict[str, Any]:
        """
        Upload an original raw ZIP archive to lunar-raw/<region>/<sensor>/<filename>.
        """
        path = Path(archive_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Raw archive file not found: {path}")

        storage_rel_path = self.build_raw_path(region_code, sensor, path.name)

        if self.use_mock:
            result = self.mock_storage.upload(
                bucket=self.BUCKET_RAW,
                storage_path=storage_rel_path,
                file_data=path,
                content_type="application/zip"
            )
        else:
            result = self.client.storage_upload(
                bucket=self.BUCKET_RAW,
                storage_path=storage_rel_path,
                file_bytes=path,
                content_type="application/zip"
            )

        return {
            "bucket": self.BUCKET_RAW,
            "storage_path": storage_rel_path,
            "full_uri": f"{self.BUCKET_RAW}/{storage_rel_path}",
            "size_bytes": path.stat().st_size,
            "response": result
        }

    def upload_metadata_file(
        self,
        file_path: Union[str, Path],
        region_code: str,
        sensor: Union[str, SensorType]
    ) -> Dict[str, Any]:
        """
        Upload metadata XML/LBL/HDR to lunar-metadata/<region>/<sensor>/<filename>.
        """
        path = Path(file_path).resolve()
        storage_rel_path = self.build_metadata_path(region_code, sensor, path.name)

        if self.use_mock:
            result = self.mock_storage.upload(
                bucket=self.BUCKET_METADATA,
                storage_path=storage_rel_path,
                file_data=path,
                content_type="application/xml" if path.suffix == ".xml" else "text/plain"
            )
        else:
            result = self.client.storage_upload(
                bucket=self.BUCKET_METADATA,
                storage_path=storage_rel_path,
                file_bytes=path,
                content_type="application/xml" if path.suffix == ".xml" else "text/plain"
            )

        return {
            "bucket": self.BUCKET_METADATA,
            "storage_path": storage_rel_path,
            "full_uri": f"{self.BUCKET_METADATA}/{storage_rel_path}",
            "response": result
        }

    def generate_signed_url(
        self,
        bucket: str,
        storage_path: str,
        expires_in_seconds: int = 3600
    ) -> str:
        """
        Generate a secure temporary signed URL for downloading scientific assets.
        """
        if self.use_mock:
            return self.mock_storage.create_signed_url(bucket, storage_path, expires_in_seconds)
        return self.client.storage_create_signed_url(bucket, storage_path, expires_in_seconds)

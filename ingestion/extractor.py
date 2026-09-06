"""
Safe extraction engine for scientific lunar ZIP archives.
"""
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from .models import SensorType, ArchiveValidationResult
from .validator import validate_zip_archive, is_safe_extraction_path


class ArchiveExtractor:
    """
    Safely unpacks ZIP archives preserving originals and protecting against path traversal.
    """

    def __init__(self, raw_store_dir: str | Path = "./data/raw", extracted_store_dir: str | Path = "./data/extracted"):
        self.raw_store_dir = Path(raw_store_dir).resolve()
        self.extracted_store_dir = Path(extracted_store_dir).resolve()
        self.raw_store_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_store_dir.mkdir(parents=True, exist_ok=True)

    def extract(
        self,
        archive_path: str | Path,
        sensor: SensorType,
        custom_extract_dir: Optional[str | Path] = None,
        preserve_in_raw: bool = True
    ) -> Tuple[ArchiveValidationResult, Path]:
        """
        Validate, preserve, and safely extract a sensor ZIP archive.
        Returns the validation result and the path to the extraction directory.
        """
        src_path = Path(archive_path).resolve()
        val_result = validate_zip_archive(src_path)

        if not val_result.is_valid:
            raise ValueError(f"ZIP validation failed for {src_path.name}: {val_result.error_message}")

        # Preserve original ZIP archive
        if preserve_in_raw:
            sensor_raw_dir = self.raw_store_dir / sensor.value
            sensor_raw_dir.mkdir(parents=True, exist_ok=True)
            dest_archive_path = sensor_raw_dir / src_path.name
            if src_path != dest_archive_path and not dest_archive_path.exists():
                shutil.copy2(src_path, dest_archive_path)

        # Determine target extraction directory
        product_stem = src_path.stem
        if custom_extract_dir:
            target_extract_dir = Path(custom_extract_dir).resolve()
        else:
            target_extract_dir = self.extracted_store_dir / sensor.value / product_stem

        target_extract_dir.mkdir(parents=True, exist_ok=True)

        # Unpack safely
        with zipfile.ZipFile(src_path, "r") as zf:
            for member in zf.infolist():
                # Defend against Zip-Slip
                if not is_safe_extraction_path(target_extract_dir, member.filename):
                    raise SecurityError(
                        f"Potentially malicious path traversal detected inside archive: '{member.filename}'"
                    )
                zf.extract(member, target_extract_dir)

        return val_result, target_extract_dir

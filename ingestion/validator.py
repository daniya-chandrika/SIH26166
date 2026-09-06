"""
Validation utilities for ZIP archives and checksum calculations.
"""
import hashlib
import os
import zipfile
from pathlib import Path
from typing import Tuple

from .models import ArchiveValidationResult


def calculate_sha256(file_path: str | Path, chunk_size: int = 65536) -> str:
    """
    Calculate the SHA-256 hex digest of a file in streaming chunks.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found for SHA-256 calculation: {file_path}")

    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_safe_extraction_path(base_dir: str | Path, target_path: str | Path) -> bool:
    """
    Ensure the resolved extraction path stays strictly inside base_dir
    to prevent Zip-Slip / path traversal vulnerabilities.
    """
    base = Path(base_dir).resolve()
    target = (base / target_path).resolve()
    try:
        target.relative_to(base)
        return True
    except ValueError:
        return False


def validate_zip_archive(archive_path: str | Path) -> ArchiveValidationResult:
    """
    Validate the physical existence, size, SHA-256 hash, and internal CRC integrity of a ZIP archive.
    """
    path = Path(archive_path).resolve()
    if not path.exists():
        return ArchiveValidationResult(
            is_valid=False,
            sha256_hash="",
            archive_path=str(path),
            size_bytes=0,
            file_count=0,
            error_message=f"Archive file does not exist: {path}"
        )

    if not path.is_file():
        return ArchiveValidationResult(
            is_valid=False,
            sha256_hash="",
            archive_path=str(path),
            size_bytes=0,
            file_count=0,
            error_message=f"Path is not a regular file: {path}"
        )

    try:
        size_bytes = path.stat().st_size
        sha256_hash = calculate_sha256(path)

        if not zipfile.is_zipfile(path):
            return ArchiveValidationResult(
                is_valid=False,
                sha256_hash=sha256_hash,
                archive_path=str(path),
                size_bytes=size_bytes,
                file_count=0,
                error_message="File is not a valid ZIP archive or header is corrupted"
            )

        with zipfile.ZipFile(path, "r") as zf:
            corrupt_file = zf.testzip()
            if corrupt_file is not None:
                return ArchiveValidationResult(
                    is_valid=False,
                    sha256_hash=sha256_hash,
                    archive_path=str(path),
                    size_bytes=size_bytes,
                    file_count=0,
                    error_message=f"Corrupt file encountered inside ZIP archive: {corrupt_file}"
                )
            file_count = len(zf.infolist())

        return ArchiveValidationResult(
            is_valid=True,
            sha256_hash=sha256_hash,
            archive_path=str(path),
            size_bytes=size_bytes,
            file_count=file_count,
            error_message=None
        )
    except Exception as e:
        return ArchiveValidationResult(
            is_valid=False,
            sha256_hash="",
            archive_path=str(path),
            size_bytes=0,
            file_count=0,
            error_message=f"Failed to validate ZIP archive: {str(e)}"
        )

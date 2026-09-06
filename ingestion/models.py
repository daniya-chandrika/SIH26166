"""
Data models and Enums for Data Ingestion Module.
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class SensorType(str, Enum):
    OHRC = "OHRC"
    TMC_2 = "TMC-2"
    IIRS = "IIRS"
    LROC = "LROC"

    @classmethod
    def from_string(cls, value: str) -> "SensorType":
        normalized = value.strip().upper().replace("_", "-")
        for member in cls:
            if member.value.upper() == normalized or member.name.upper() == normalized:
                return member
        raise ValueError(f"Unknown sensor type: '{value}'. Must be one of {[s.value for s in cls]}")


class FileCategory(str, Enum):
    SCIENTIFIC_IMAGE = "SCIENTIFIC_IMAGE"
    METADATA = "METADATA"
    BROWSE_IMAGE = "BROWSE_IMAGE"
    AUXILIARY = "AUXILIARY"
    UNKNOWN = "UNKNOWN"


@dataclass
class ExtractedFileInfo:
    relative_path: str
    absolute_path: str
    filename: str
    extension: str
    file_size_bytes: int
    category: FileCategory
    mime_type: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "filename": self.filename,
            "extension": self.extension,
            "file_size_bytes": self.file_size_bytes,
            "category": self.category.value,
            "mime_type": self.mime_type,
            "extra": self.extra
        }


@dataclass
class ArchiveValidationResult:
    is_valid: bool
    sha256_hash: str
    archive_path: str
    size_bytes: int
    file_count: int
    error_message: Optional[str] = None


@dataclass
class IngestionResult:
    sensor: SensorType
    archive_path: str
    archive_sha256: str
    extract_dir: str
    is_valid: bool
    files: List[ExtractedFileInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def scientific_images(self) -> List[ExtractedFileInfo]:
        return [f for f in self.files if f.category == FileCategory.SCIENTIFIC_IMAGE]

    @property
    def metadata_files(self) -> List[ExtractedFileInfo]:
        return [f for f in self.files if f.category == FileCategory.METADATA]

    @property
    def browse_images(self) -> List[ExtractedFileInfo]:
        return [f for f in self.files if f.category == FileCategory.BROWSE_IMAGE]

    @property
    def auxiliary_files(self) -> List[ExtractedFileInfo]:
        return [f for f in self.files if f.category == FileCategory.AUXILIARY]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor": self.sensor.value,
            "archive_path": str(self.archive_path),
            "archive_sha256": self.archive_sha256,
            "extract_dir": str(self.extract_dir),
            "is_valid": self.is_valid,
            "total_files": len(self.files),
            "scientific_images_count": len(self.scientific_images),
            "metadata_files_count": len(self.metadata_files),
            "browse_images_count": len(self.browse_images),
            "auxiliary_files_count": len(self.auxiliary_files),
            "files": [f.to_dict() for f in self.files],
            "errors": self.errors
        }

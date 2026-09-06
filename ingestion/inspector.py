"""
Recursive file inspector and categorizer for lunar orbital products.
"""
import mimetypes
import os
from pathlib import Path
from typing import List

from .models import ExtractedFileInfo, FileCategory, SensorType, IngestionResult
from .validator import calculate_sha256

# Known file extensions by category
SCIENTIFIC_IMAGE_EXTS = {".tif", ".tiff", ".img", ".cub", ".fits", ".fit", ".dat", ".jp2", ".raw", ".bil", ".bip", ".bsq"}
METADATA_EXTS = {".xml", ".lbl", ".pds", ".hdr", ".json", ".txt", ".tfw", ".jpw"}
BROWSE_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
AUXILIARY_EXTS = {".tab", ".csv", ".spk", ".bsp", ".bc", ".geo", ".ephem", ".tls", ".tpc", ".tf", ".idx", ".log"}


def classify_file(path: Path) -> FileCategory:
    """
    Classify a file based on its extension, name patterns, and conventions.
    """
    filename_lower = path.name.lower()
    ext_lower = path.suffix.lower()

    # Browse heuristics (even if .tif or .png)
    is_browse_name = any(keyword in filename_lower for keyword in ["browse", "thumb", "thumbnail", "preview", "quicklook", "_ql", "_brws"])
    if is_browse_name and (ext_lower in BROWSE_IMAGE_EXTS or ext_lower in {".tif", ".tiff", ".png", ".jpg"}):
        return FileCategory.BROWSE_IMAGE

    if ext_lower in BROWSE_IMAGE_EXTS:
        return FileCategory.BROWSE_IMAGE

    if ext_lower in METADATA_EXTS:
        # Check if it's an aux table or standard label
        if ext_lower in {".txt", ".json"} and any(k in filename_lower for k in ["manifest", "report", "log", "summary"]):
            return FileCategory.AUXILIARY
        return FileCategory.METADATA

    if ext_lower in SCIENTIFIC_IMAGE_EXTS:
        return FileCategory.SCIENTIFIC_IMAGE

    if ext_lower in AUXILIARY_EXTS:
        return FileCategory.AUXILIARY

    return FileCategory.UNKNOWN


class ArchiveInspector:
    """
    Recursively inspects extracted product directories and generates file categorization manifests.
    """

    def inspect(self, extract_dir: str | Path, sensor: SensorType, archive_path: str | Path, archive_sha256: str) -> IngestionResult:
        base_dir = Path(extract_dir).resolve()
        if not base_dir.exists() or not base_dir.is_dir():
            raise NotADirectoryError(f"Extraction directory not found: {base_dir}")

        files_info: List[ExtractedFileInfo] = []
        errors: List[str] = []

        for root, _, filenames in os.walk(base_dir):
            for fname in filenames:
                file_path = Path(root) / fname
                try:
                    rel_path = file_path.relative_to(base_dir).as_posix()
                    size_bytes = file_path.stat().st_size
                    ext = file_path.suffix.lower()
                    category = classify_file(file_path)
                    mime, _ = mimetypes.guess_type(str(file_path))

                    files_info.append(
                        ExtractedFileInfo(
                            relative_path=rel_path,
                            absolute_path=str(file_path.resolve()),
                            filename=fname,
                            extension=ext,
                            file_size_bytes=size_bytes,
                            category=category,
                            mime_type=mime,
                            extra={
                                "sha256": calculate_sha256(file_path) if size_bytes < 20 * 1024 * 1024 else None
                            }
                        )
                    )
                except Exception as e:
                    errors.append(f"Error inspecting file '{file_path}': {str(e)}")

        return IngestionResult(
            sensor=sensor,
            archive_path=str(Path(archive_path).resolve()),
            archive_sha256=archive_sha256,
            extract_dir=str(base_dir),
            is_valid=len(errors) == 0,
            files=files_info,
            errors=errors
        )

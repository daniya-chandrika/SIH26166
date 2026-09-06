"""
Region Dataset Validation Engine.
Validates the presence of the 4 required orbital products (OHRC, TMC-2, IIRS, LROC) per region.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from database.models import RegionDatasetStatus
from database.repository import SupabaseLunarRepository

REQUIRED_SENSORS = ["OHRC", "TMC-2", "IIRS", "LROC"]


@dataclass
class RegionValidationResult:
    region_code: str
    region_id: str
    region_name: str
    status: RegionDatasetStatus  # COMPLETE or INCOMPLETE
    present_sensors: List[str] = field(default_factory=list)
    missing_sensors: List[str] = field(default_factory=list)
    images_by_sensor: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    summary_message: str = ""

    @property
    def is_complete(self) -> bool:
        return self.status == RegionDatasetStatus.COMPLETE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_code": self.region_code,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "status": self.status.value,
            "is_complete": self.is_complete,
            "present_sensors": self.present_sensors,
            "missing_sensors": self.missing_sensors,
            "summary_message": self.summary_message,
            "total_images": len(self.images_by_sensor)
        }


class DatasetValidator:
    """
    Validates region datasets for complete 4-image quad coverage.
    """

    def __init__(self, repository: Optional[SupabaseLunarRepository] = None):
        self.repo = repository or SupabaseLunarRepository()

    def validate_region_dataset(self, region_code_or_id: str) -> RegionValidationResult:
        """
        Validate whether a specific region has all 4 required products: OHRC, TMC-2, IIRS, LROC.
        """
        # Resolve region
        reg = None
        if len(region_code_or_id) <= 4:  # Likely a code like 'R01'
            reg = self.repo.get_region_by_code(region_code_or_id)
        if not reg:
            reg = self.repo.get_region_by_id(region_code_or_id)
        if not reg:
            reg = self.repo.get_region_by_code(region_code_or_id)

        if not reg:
            return RegionValidationResult(
                region_code=region_code_or_id,
                region_id="",
                region_name="UNKNOWN",
                status=RegionDatasetStatus.INCOMPLETE,
                missing_sensors=REQUIRED_SENSORS.copy(),
                summary_message=f"{region_code_or_id} -> UNKNOWN REGION"
            )

        region_id = reg["id"]
        region_code = reg["region_code"]
        region_name = reg["region_name"]

        images = self.repo.get_images_by_region(region_id)

        present_sensors: List[str] = []
        images_by_sensor: Dict[str, Dict[str, Any]] = {}

        for img in images:
            raw_s = img["sensor"]
            norm_s = raw_s.replace("_", "-").upper()
            if "OHRC" in norm_s:
                s_key = "OHRC"
            elif "TMC" in norm_s:
                s_key = "TMC-2"
            elif "IIRS" in norm_s:
                s_key = "IIRS"
            elif "LROC" in norm_s:
                s_key = "LROC"
            else:
                s_key = raw_s

            if s_key in REQUIRED_SENSORS and s_key not in present_sensors:
                present_sensors.append(s_key)
                images_by_sensor[s_key] = img

        missing_sensors = [s for s in REQUIRED_SENSORS if s not in present_sensors]
        is_complete = len(missing_sensors) == 0

        if is_complete:
            summary_msg = f"{region_code} -> COMPLETE"
            status = RegionDatasetStatus.COMPLETE
        else:
            missing_str = ", ".join(missing_sensors)
            summary_msg = f"{region_code} -> MISSING {missing_str}"
            status = RegionDatasetStatus.INCOMPLETE

        return RegionValidationResult(
            region_code=region_code,
            region_id=region_id,
            region_name=region_name,
            status=status,
            present_sensors=present_sensors,
            missing_sensors=missing_sensors,
            images_by_sensor=images_by_sensor,
            summary_message=summary_msg
        )

    def generate_database_validation_report(self) -> Dict[str, Any]:
        """
        Inspect all regions across the database and summarize readiness for registration.
        """
        all_regions = self.repo.get_all_regions()
        region_results = [self.validate_region_dataset(r["region_code"]) for r in all_regions]

        total_regions = len(region_results)
        complete_regions = [r for r in region_results if r.is_complete]
        incomplete_regions = [r for r in region_results if not r.is_complete]

        missing_ohrc = [r.region_code for r in region_results if "OHRC" in r.missing_sensors]
        missing_tmc2 = [r.region_code for r in region_results if "TMC-2" in r.missing_sensors]
        missing_iirs = [r.region_code for r in region_results if "IIRS" in r.missing_sensors]
        missing_lroc = [r.region_code for r in region_results if "LROC" in r.missing_sensors]

        all_images = self.repo.get_all_images()
        warning_images = [img for img in all_images if img.get("status") == "WARNING"]
        failed_images = [img for img in all_images if img.get("status") == "FAILED"]

        return {
            "total_regions": total_regions,
            "complete_regions_count": len(complete_regions),
            "incomplete_regions_count": len(incomplete_regions),
            "complete_regions": [r.region_code for r in complete_regions],
            "missing_ohrc": missing_ohrc,
            "missing_tmc2": missing_tmc2,
            "missing_iirs": missing_iirs,
            "missing_lroc": missing_lroc,
            "total_images_in_db": len(all_images),
            "warning_images_count": len(warning_images),
            "failed_images_count": len(failed_images),
            "region_summaries": [r.to_dict() for r in region_results]
        }

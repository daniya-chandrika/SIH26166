"""
Quality Report generator for JSON and CSV exports.
"""
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from .models import QualityReportItem, QualityStatus


class QualityReporter:
    """
    Aggregates quality evaluation items and exports JSON and CSV reports.
    """

    def __init__(self, output_dir: str | Path = "./reports"):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, items: List[QualityReportItem]) -> Dict[str, Any]:
        total_items = len(items)
        passed_count = sum(1 for item in items if item.status == QualityStatus.PASS)
        warning_count = sum(1 for item in items if item.status == QualityStatus.WARNING)
        failed_count = sum(1 for item in items if item.status == QualityStatus.FAIL)

        report_data = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_evaluated": total_items,
                "passed": passed_count,
                "warnings": warning_count,
                "failed": failed_count,
                "overall_status": "FAIL" if failed_count > 0 else ("WARNING" if warning_count > 0 else "PASS")
            },
            "items": [item.to_dict() for item in items]
        }

        # Export JSON
        json_path = self.output_dir / "quality_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # Export CSV
        csv_path = self.output_dir / "quality_report.csv"
        flat_records = [item.to_flat_dict() for item in items]
        if flat_records:
            df = pd.DataFrame(flat_records)
            df.to_csv(csv_path, index=False)
        else:
            # Create empty CSV with columns
            pd.DataFrame(columns=[
                "image_id", "product_id", "sensor", "status", "quality_score",
                "is_corrupted", "is_readable", "is_blank", "has_invalid_values",
                "nodata_pct", "saturation_pct", "mean_dn", "std_dn",
                "min_dn", "max_dn", "missing_coords", "missing_angles",
                "missing_res", "missing_time", "issue_count", "issues_summary"
            ]).to_csv(csv_path, index=False)

        return report_data

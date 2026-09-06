"""
Lunar Dataset Health and Completeness Dashboard (CLI).
Displays live 4-image status per region across R01 - R10.
"""
import sys
from typing import Optional

from database.repository import SupabaseLunarRepository
from database.validation import DatasetValidator


def render_dashboard(validator: Optional[DatasetValidator] = None):
    val = validator or DatasetValidator()
    report = val.generate_database_validation_report()

    print("\n" + "=" * 95)
    print(" LUNAR REGISTRATION DATASET DASHBOARD - 4-IMAGE QUAD REPOSITORY (SIH26166)")
    print("=" * 95)

    headers = f"{'Region':<8} | {'OHRC':<6} | {'TMC-2':<6} | {'IIRS':<6} | {'LROC':<6} | {'Quad Status':<12} | {'Assigned':<12} | {'Quality':<10}"
    print(headers)
    print("-" * 95)

    for summary in report["region_summaries"]:
        r_code = summary["region_code"]
        present = summary["present_sensors"]
        is_comp = summary["is_complete"]

        ohrc_mark = "[OK]" if "OHRC" in present else "[--]"
        tmc2_mark = "[OK]" if "TMC-2" in present else "[--]"
        iirs_mark = "[OK]" if "IIRS" in present else "[--]"
        lroc_mark = "[OK]" if "LROC" in present else "[--]"

        status_str = "COMPLETE" if is_comp else "INCOMPLETE"
        
        # Check assigned member / quality
        assigned_name = "Unassigned"
        quality_str = "PENDING"
        for s_key, img_data in summary.get("images_by_sensor", {}).items():
            if img_data.get("assigned_to"):
                assigned_name = img_data["assigned_to"]
            if img_data.get("status") in ["VALIDATED", "WARNING", "FAILED"]:
                quality_str = img_data["status"]

        line = f"{r_code:<8} | {ohrc_mark:<6} | {tmc2_mark:<6} | {iirs_mark:<6} | {lroc_mark:<6} | {status_str:<12} | {assigned_name:<12} | {quality_str:<10}"
        print(line)

    print("-" * 95)
    print(f"Total Regions: {report['total_regions']} | Complete: {report['complete_regions_count']} | Incomplete: {report['incomplete_regions_count']} | Total Images: {report['total_images_in_db']}")
    if report["incomplete_regions_count"] > 0:
        print("\nMissing Sensors by Region:")
        if report["missing_ohrc"]:
            print(f"  - Missing OHRC : {', '.join(report['missing_ohrc'])}")
        if report["missing_tmc2"]:
            print(f"  - Missing TMC-2: {', '.join(report['missing_tmc2'])}")
        if report["missing_iirs"]:
            print(f"  - Missing IIRS : {', '.join(report['missing_iirs'])}")
        if report["missing_lroc"]:
            print(f"  - Missing LROC : {', '.join(report['missing_lroc'])}")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    render_dashboard()

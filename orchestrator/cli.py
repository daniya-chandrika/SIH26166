"""
Command Line Interface (CLI) for SIH26166 Lunar Image Registration Pipeline.
"""
import argparse
import sys
from pathlib import Path
from typing import Dict

from ingestion.models import SensorType
from orchestrator.pipeline import LunarPipelineOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="SIH26166: Scientific Lunar Image Registration Foundation Pipeline"
    )

    parser.add_argument(
        "--ohrc",
        type=str,
        required=False,
        help="Path to Chandrayaan-2 OHRC orbital product ZIP archive"
    )
    parser.add_argument(
        "--tmc2",
        type=str,
        required=False,
        help="Path to Chandrayaan-2 TMC-2 orbital product ZIP archive"
    )
    parser.add_argument(
        "--iirs",
        type=str,
        required=False,
        help="Path to Chandrayaan-2 IIRS orbital product ZIP archive"
    )
    parser.add_argument(
        "--lroc",
        type=str,
        required=False,
        help="Path to NASA LROC lunar reference product ZIP archive"
    )

    # Optional paths
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="./data/raw",
        help="Directory to preserve original raw archives (default: ./data/raw)"
    )
    parser.add_argument(
        "--extracted-dir",
        type=str,
        default="./data/extracted",
        help="Directory for extracted files (default: ./data/extracted)"
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default="./reports",
        help="Directory to save dataset manifests and quality reports (default: ./reports)"
    )
    parser.add_argument(
        "--max-nodata",
        type=float,
        default=50.0,
        help="Maximum allowed NoData percentage before warning/failure (default: 50.0)"
    )
    parser.add_argument(
        "--max-saturation",
        type=float,
        default=15.0,
        help="Maximum allowed pixel saturation percentage before warning (default: 15.0)"
    )

    args = parser.parse_args()

    sensor_archives: Dict[SensorType, str | Path] = {}
    if args.ohrc:
        sensor_archives[SensorType.OHRC] = args.ohrc
    if args.tmc2:
        sensor_archives[SensorType.TMC_2] = args.tmc2
    if args.iirs:
        sensor_archives[SensorType.IIRS] = args.iirs
    if args.lroc:
        sensor_archives[SensorType.LROC] = args.lroc

    if not sensor_archives:
        print("Error: At least one sensor ZIP archive must be specified via --ohrc, --tmc2, --iirs, or --lroc.")
        parser.print_help()
        sys.exit(1)

    orchestrator = LunarPipelineOrchestrator(
        raw_dir=args.raw_dir,
        extracted_dir=args.extracted_dir,
        reports_dir=args.reports_dir,
        max_nodata_percent=args.max_nodata,
        max_saturation_percent=args.max_saturation
    )

    result = orchestrator.run(sensor_archives)
    if not result.success:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

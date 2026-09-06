"""
Convenience Script: Synchronize dataset_manifest.json with Supabase Database.
Usage: python sync_manifest_to_supabase.py [--manifest ./reports/dataset_manifest.json] [--region R01]
"""
import argparse
import sys
from pathlib import Path

from pipeline.sync import ManifestSynchronizer


def main():
    parser = argparse.ArgumentParser(description="Synchronize local dataset manifest with Supabase PostgreSQL")
    parser.add_argument("--manifest", type=str, default="./reports/dataset_manifest.json", help="Path to manifest JSON or CSV")
    parser.add_argument("--region", type=str, default="R01", help="Target region code (default: R01)")

    args = parser.parse_args()
    manifest_path = Path(args.manifest)

    if not manifest_path.exists():
        print(f"Error: Manifest file not found at {manifest_path}")
        sys.exit(1)

    synchronizer = ManifestSynchronizer()
    print(f"Synchronizing '{manifest_path}' to Supabase region '{args.region}'...")
    result = synchronizer.sync_manifest(manifest_path, default_region_code=args.region)

    print("\n--- Synchronization Summary ---")
    print(f"Total Records Evaluated : {result['total_records']}")
    print(f"New Images Inserted     : {result['inserted_images']}")
    print(f"Metadata Records Synced : {result['metadata_synced']}")
    print(f"Skipped Duplicates      : {result['skipped_duplicates']}")
    if result["errors"]:
        print(f"Errors Encountered      : {len(result['errors'])}")
        for err in result["errors"]:
            print(f"  - {err}")
    else:
        print("Status                  : SUCCESS (0 errors)")


if __name__ == "__main__":
    main()

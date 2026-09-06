"""
Dataset Manifest Generator for SIH26166 Lunar Image Registration.
Produces dataset_manifest.json and dataset_manifest.csv.
"""
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from ingestion.models import IngestionResult
from metadata.models import LunarProductMetadata


class ManifestGenerator:
    """
    Builds and exports comprehensive dataset manifests in JSON and CSV formats.
    """

    def __init__(self, output_dir: str | Path = "./reports"):
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_manifest(
        self,
        ingestion_results: List[IngestionResult],
        products_metadata: List[LunarProductMetadata]
    ) -> Dict[str, Any]:
        """
        Generate dataset_manifest.json and dataset_manifest.csv from ingestion and metadata stages.
        """
        sensors_present = list(set([ing.sensor.value for ing in ingestion_results]))

        manifest_data = {
            "manifest_version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_archives": len(ingestion_results),
                "total_products": len(products_metadata),
                "sensors": sensors_present,
                "total_scientific_rasters": sum(len(r.scientific_images) for r in ingestion_results),
                "total_metadata_files": sum(len(r.metadata_files) for r in ingestion_results),
                "total_browse_images": sum(len(r.browse_images) for r in ingestion_results),
                "total_auxiliary_files": sum(len(r.auxiliary_files) for r in ingestion_results)
            },
            "archives": [ing.to_dict() for ing in ingestion_results],
            "products": [prod.to_dict() for prod in products_metadata]
        }

        # Export JSON
        json_path = self.output_dir / "dataset_manifest.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # Export CSV (flattened products list with archive hashes)
        csv_path = self.output_dir / "dataset_manifest.csv"
        flat_records = []
        for prod in products_metadata:
            flat_dict = prod.to_flat_dict()
            # Find matching archive sha256
            matching_ing = next((ing for ing in ingestion_results if ing.sensor.value == prod.sensor), None)
            flat_dict["archive_sha256"] = matching_ing.archive_sha256 if matching_ing else None
            flat_dict["original_archive"] = Path(matching_ing.archive_path).name if matching_ing else None
            flat_records.append(flat_dict)

        if flat_records:
            df = pd.DataFrame(flat_records)
            df.to_csv(csv_path, index=False)
        else:
            pd.DataFrame(columns=[
                "image_id", "product_id", "sensor", "filename", "file_path",
                "format", "product_level", "mission", "width", "height",
                "bit_depth", "number_of_bands", "spatial_resolution",
                "latitude", "longitude", "min_latitude", "max_latitude",
                "min_longitude", "max_longitude", "footprint", "acquisition_date",
                "acquisition_time", "start_time_utc", "stop_time_utc",
                "sun_elevation", "sun_azimuth", "incidence_angle", "emission_angle",
                "phase_angle", "look_angle", "projection", "crs", "datum",
                "source_label_file", "archive_sha256", "original_archive"
            ]).to_csv(csv_path, index=False)

        return manifest_data

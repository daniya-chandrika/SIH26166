"""
Integration test for full Lunar Image Registration Foundation Pipeline.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from orchestrator.pipeline import LunarPipelineOrchestrator
from ingestion.models import SensorType
from tests.make_synthetic_dataset import create_synthetic_datasets


class TestPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_pipeline_run(self):
        # 1. Generate synthetic ZIPs
        zips_dir = self.tmp_path / "zips"
        created_zips = create_synthetic_datasets(zips_dir)

        raw_dir = self.tmp_path / "data" / "raw"
        extracted_dir = self.tmp_path / "data" / "extracted"
        reports_dir = self.tmp_path / "reports"

        # 2. Run orchestrator
        orchestrator = LunarPipelineOrchestrator(
            raw_dir=raw_dir,
            extracted_dir=extracted_dir,
            reports_dir=reports_dir
        )

        sensor_archives = {
            SensorType.OHRC: created_zips["OHRC"],
            SensorType.TMC_2: created_zips["TMC-2"],
            SensorType.IIRS: created_zips["IIRS"],
            SensorType.LROC: created_zips["LROC"],
        }

        summary = orchestrator.run(sensor_archives)

        # 3. Assertions
        self.assertTrue(summary.success)
        self.assertEqual(len(summary.ingestion_results), 4)
        self.assertGreaterEqual(len(summary.products_metadata), 4)
        self.assertGreaterEqual(len(summary.quality_items), 4)

        # Verify report files existence
        manifest_json = reports_dir / "dataset_manifest.json"
        manifest_csv = reports_dir / "dataset_manifest.csv"
        quality_json = reports_dir / "quality_report.json"
        quality_csv = reports_dir / "quality_report.csv"

        self.assertTrue(manifest_json.exists())
        self.assertTrue(manifest_csv.exists())
        self.assertTrue(quality_json.exists())
        self.assertTrue(quality_csv.exists())

        # Check manifest JSON content
        with open(manifest_json, "r") as f:
            manifest_data = json.load(f)
        self.assertEqual(manifest_data["summary"]["total_archives"], 4)
        self.assertEqual(set(manifest_data["summary"]["sensors"]), {"OHRC", "TMC-2", "IIRS", "LROC"})

        # Check quality JSON content
        with open(quality_json, "r") as f:
            quality_data = json.load(f)
        self.assertGreaterEqual(quality_data["summary"]["total_evaluated"], 4)


if __name__ == "__main__":
    unittest.main()

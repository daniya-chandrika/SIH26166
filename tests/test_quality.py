"""
Unit tests for Quality Control and Quality Reporter.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image

from quality.checkers import RasterQualityChecker
from quality.reporter import QualityReporter
from quality.models import QualityStatus
from metadata.models import LunarProductMetadata


class TestQuality(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_quality_checker_valid_image(self):
        img_path = self.tmp_path / "valid_crater.tif"
        arr = (np.random.normal(120, 20, (100, 100))).clip(10, 240).astype(np.uint8)
        Image.fromarray(arr).save(img_path)

        meta = LunarProductMetadata(
            image_id="test_001",
            product_id="test_001",
            sensor="OHRC",
            file_path=str(img_path),
            width=100,
            height=100,
            bit_depth=8,
            spatial_resolution=0.25,
            latitude=-70.9,
            longitude=22.8,
            incidence_angle=40.0,
            acquisition_date="2023-08-15"
        )

        checker = RasterQualityChecker()
        report_item = checker.evaluate(meta)

        self.assertEqual(report_item.status, QualityStatus.PASS)
        self.assertFalse(report_item.is_corrupted)
        self.assertFalse(report_item.is_blank)
        self.assertEqual(report_item.metrics.nodata_percentage, 0.0)
        self.assertGreaterEqual(report_item.quality_score, 0.90)

    def test_quality_checker_blank_image(self):
        img_path = self.tmp_path / "blank.tif"
        arr = np.zeros((100, 100), dtype=np.uint8)
        Image.fromarray(arr).save(img_path)

        meta = LunarProductMetadata(
            image_id="blank_001",
            product_id="blank_001",
            sensor="OHRC",
            file_path=str(img_path),
            width=100,
            height=100,
            bit_depth=8
        )

        checker = RasterQualityChecker()
        report_item = checker.evaluate(meta)

        self.assertTrue(report_item.is_blank)
        self.assertIn(report_item.status, [QualityStatus.WARNING, QualityStatus.FAIL])

    def test_quality_reporter_export(self):
        reporter = QualityReporter(output_dir=self.tmp_path)
        meta = LunarProductMetadata(image_id="item1", product_id="item1", sensor="LROC")
        checker = RasterQualityChecker()
        item = checker.evaluate(meta)

        report_dict = reporter.generate_report([item])

        self.assertIn("summary", report_dict)
        self.assertTrue((self.tmp_path / "quality_report.json").exists())
        self.assertTrue((self.tmp_path / "quality_report.csv").exists())


if __name__ == "__main__":
    unittest.main()

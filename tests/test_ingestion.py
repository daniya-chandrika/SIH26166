"""
Unit tests for Ingestion and Validation module.
"""
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from ingestion.validator import calculate_sha256, validate_zip_archive, is_safe_extraction_path
from ingestion.inspector import classify_file, ArchiveInspector
from ingestion.extractor import ArchiveExtractor
from ingestion.models import SensorType, FileCategory


class TestIngestion(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tmp_path = Path(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sha256_calculation(self):
        test_file = self.tmp_path / "sample.bin"
        test_file.write_bytes(b"LUNAR_REGISTRATION_SIH26166")
        sha = calculate_sha256(test_file)
        self.assertEqual(len(sha), 64)
        self.assertIsInstance(sha, str)

    def test_safe_path_protection(self):
        base = Path("/safe/workspace/data")
        self.assertTrue(is_safe_extraction_path(base, "product/image.tif"))
        self.assertFalse(is_safe_extraction_path(base, "../../../etc/passwd"))

    def test_zip_validation_valid(self):
        zip_path = self.tmp_path / "test_valid.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "hello moon")

        result = validate_zip_archive(zip_path)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.file_count, 1)
        self.assertIsNone(result.error_message)
        self.assertEqual(len(result.sha256_hash), 64)

    def test_zip_validation_corrupt(self):
        corrupt_path = self.tmp_path / "corrupt.zip"
        corrupt_path.write_bytes(b"NOT_A_VALID_ZIP_HEADER")

        result = validate_zip_archive(corrupt_path)
        self.assertFalse(result.is_valid)
        self.assertIn("not a valid ZIP", result.error_message)

    def test_file_classification(self):
        self.assertEqual(classify_file(Path("ohrc_img.tif")), FileCategory.SCIENTIFIC_IMAGE)
        self.assertEqual(classify_file(Path("dataset_label.xml")), FileCategory.METADATA)
        self.assertEqual(classify_file(Path("lroc_label.lbl")), FileCategory.METADATA)
        self.assertEqual(classify_file(Path("ch2_preview_browse.jpg")), FileCategory.BROWSE_IMAGE)
        self.assertEqual(classify_file(Path("orbit_geometry.tab")), FileCategory.AUXILIARY)


if __name__ == "__main__":
    unittest.main()

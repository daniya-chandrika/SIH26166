"""
Unit tests for Metadata Parsers and Extractor.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from metadata.parsers.pds4_parser import PDS4Parser
from metadata.parsers.pds3_parser import PDS3Parser
from metadata.parsers.geotiff_parser import GeoTIFFParser
from metadata.parsers.envi_parser import ENVIParser
from metadata.extractor import MetadataExtractor
from tests.make_synthetic_dataset import create_synthetic_datasets
from ingestion.extractor import ArchiveExtractor
from ingestion.models import SensorType


class TestMetadata(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.zips_dir = Path(cls.temp_dir) / "zips"
        cls.synthetic_zips = create_synthetic_datasets(cls.zips_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_pds4_parser(self):
        extract_root = Path(self.temp_dir) / "extracted_ohrc"
        extractor = ArchiveExtractor(extracted_store_dir=extract_root)
        _, extract_dir = extractor.extract(self.synthetic_zips["OHRC"], sensor=SensorType.OHRC)

        xml_files = list(extract_dir.rglob("*.xml"))
        self.assertGreaterEqual(len(xml_files), 1)

        parser = PDS4Parser()
        meta = parser.parse(xml_files[0])

        self.assertEqual(meta.sensor, "OHRC")
        self.assertEqual(meta.spatial_resolution, 0.25)
        self.assertEqual(meta.incidence_angle, 42.5)
        self.assertEqual(meta.emission_angle, 3.2)
        self.assertEqual(meta.phase_angle, 40.1)
        self.assertEqual(meta.sun_elevation, 47.5)
        self.assertEqual(meta.sun_azimuth, 112.45)
        self.assertEqual(meta.acquisition_date, "2023-08-15")
        self.assertEqual(meta.width, 512)
        self.assertEqual(meta.height, 512)
        self.assertIsNotNone(meta.footprint)

    def test_pds3_parser(self):
        extract_root = Path(self.temp_dir) / "extracted_lroc"
        extractor = ArchiveExtractor(extracted_store_dir=extract_root)
        _, extract_dir = extractor.extract(self.synthetic_zips["LROC"], sensor=SensorType.LROC)

        lbl_files = list(extract_dir.rglob("*.lbl"))
        self.assertGreaterEqual(len(lbl_files), 1)

        parser = PDS3Parser()
        meta = parser.parse(lbl_files[0])

        self.assertEqual(meta.sensor, "LROC")
        self.assertEqual(meta.product_id, "M1142442434RE")
        self.assertEqual(meta.spatial_resolution, 0.5)
        self.assertEqual(meta.incidence_angle, 45.3)
        self.assertEqual(meta.emission_angle, 4.1)
        self.assertEqual(meta.phase_angle, 42.1)
        self.assertEqual(meta.width, 512)
        self.assertEqual(meta.height, 512)

    def test_envi_parser(self):
        extract_root = Path(self.temp_dir) / "extracted_iirs"
        extractor = ArchiveExtractor(extracted_store_dir=extract_root)
        _, extract_dir = extractor.extract(self.synthetic_zips["IIRS"], sensor=SensorType.IIRS)

        hdr_files = list(extract_dir.rglob("*.hdr"))
        self.assertGreaterEqual(len(hdr_files), 1)

        parser = ENVIParser()
        meta = parser.parse(hdr_files[0])

        self.assertEqual(meta.sensor, "IIRS")
        self.assertEqual(meta.width, 64)
        self.assertEqual(meta.height, 64)
        self.assertEqual(meta.number_of_bands, 16)
        self.assertEqual(meta.spatial_resolution, 80.0)


if __name__ == "__main__":
    unittest.main()

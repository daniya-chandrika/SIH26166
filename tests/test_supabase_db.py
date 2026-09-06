"""
Unit tests for Supabase Database repository operations.
"""
import unittest
import uuid

from database.models import (
    RegionRecord, ImageRecord, ImageMetadataRecord,
    ImageQualityRecord, ImageStatus
)
from database.connection import SupabaseDBConnection
from database.repository import SupabaseLunarRepository
from storage.emulator import MockSupabaseDB


class TestSupabaseDB(unittest.TestCase):

    def setUp(self):
        self.mock_db = MockSupabaseDB()
        self.conn = SupabaseDBConnection(use_mock=True, mock_db=self.mock_db)
        self.repo = SupabaseLunarRepository(db_connection=self.conn)

    def test_region_crud(self):
        # Default seeded regions exist
        r01 = self.repo.get_region_by_code("R01")
        self.assertIsNotNone(r01)
        self.assertEqual(r01["region_code"], "R01")

        # Create dynamic region
        r99 = self.repo.get_or_create_region("R99", region_name="Far Side Crater")
        self.assertIsNotNone(r99["id"])
        self.assertEqual(r99["region_code"], "R99")

        # Fetch again should return existing
        r99_fetch = self.repo.get_region_by_code("R99")
        self.assertEqual(r99_fetch["id"], r99["id"])

    def test_image_and_metadata_insertion(self):
        region = self.repo.get_region_by_code("R01")
        img_rec = ImageRecord(
            image_id="test_ohrc_001",
            region_id=region["id"],
            sensor="OHRC",
            file_name="test_ohrc.zip",
            storage_path="R01/OHRC/test_ohrc.zip",
            file_format="ZIP",
            product_id="test_ohrc_001",
            file_size_bytes=1048576,
            sha256="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abc",
            status=ImageStatus.UPLOADED
        )
        db_img = self.repo.insert_image(img_rec)
        self.assertIsNotNone(db_img["id"])
        self.assertEqual(db_img["status"], "UPLOADED")

        # Insert metadata
        meta_rec = ImageMetadataRecord(
            image_id=db_img["id"],
            width_px=1024,
            height_px=1024,
            spatial_resolution_m=0.25,
            incidence_angle_deg=45.0
        )
        db_meta = self.repo.insert_image_metadata(meta_rec)
        self.assertEqual(db_meta["image_id"], db_img["id"])
        self.assertEqual(db_meta["spatial_resolution_m"], 0.25)

        # Insert quality
        qual_rec = ImageQualityRecord(
            image_id=db_img["id"],
            readable=True,
            nodata_percentage=2.5,
            quality_status="PASS"
        )
        db_qual = self.repo.insert_image_quality(qual_rec)
        self.assertEqual(db_qual["quality_status"], "PASS")

        # Update status
        updated = self.repo.update_image_status(db_img["id"], ImageStatus.VALIDATED)
        self.assertEqual(updated["status"], "VALIDATED")


if __name__ == "__main__":
    unittest.main()

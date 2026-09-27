"""
Unit Tests for Remote Orbital Archive Client and Windowed Retrieval (Mode B).
"""
import unittest
import tempfile
from pathlib import Path

from ingestion.remote_archive import (
    RemoteArchiveClient,
    RemoteArchiveSearchQuery,
    RemoteProductCatalogItem,
    RemoteArchiveProvider
)


class TestRemoteArchive(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.client = RemoteArchiveClient(cache_dir=self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_search_south_pole_products(self):
        """Verify discovery of Chandrayaan-2 and LROC products at Shackleton (R01)."""
        q = RemoteArchiveSearchQuery(
            min_latitude=-90.0,
            max_latitude=-89.0,
            min_longitude=-10.0,
            max_longitude=10.0
        )
        results = self.client.search_products(q)
        self.assertGreater(len(results), 0)
        sensors = [r.sensor for r in results]
        self.assertTrue("OHRC" in sensors or "LROC" in sensors)

    def test_find_cross_mission_pairs(self):
        """Verify cross-mission pair discovery for Apollo 11 (R04)."""
        pairs = self.client.find_cross_mission_pairs(
            min_latitude=0.0,
            max_latitude=1.0,
            min_longitude=23.0,
            max_longitude=24.0,
            ch2_sensor="OHRC",
            ref_sensor="LROC"
        )
        self.assertGreater(len(pairs), 0)
        ch2, ref, overlap = pairs[0]
        self.assertEqual(ch2.sensor, "OHRC")
        self.assertEqual(ref.sensor, "LROC")
        self.assertGreater(overlap, 10.0)

    def test_windowed_retrieval_and_caching(self):
        """Verify spatial window retrieval caches array on disk without downloading full archive."""
        item = RemoteProductCatalogItem(
            product_id="test_remote_item_01",
            sensor="OHRC",
            mission="Chandrayaan-2",
            archive_provider=RemoteArchiveProvider.ISRO_PRADAN,
            center_latitude=-89.90,
            center_longitude=0.0,
            min_latitude=-90.0,
            max_latitude=-89.8,
            min_longitude=-1.0,
            max_longitude=1.0,
            spatial_resolution_m=0.25,
            acquisition_date="2021-03-14",
            download_url="https://pradan.issdc.gov.in/test.zip",
            file_size_mb=450.0
        )

        arr, cache_path = self.client.retrieve_spatial_window(item, window_size_px=128)
        self.assertEqual(arr.shape, (128, 128))
        self.assertTrue(cache_path.exists())

        # Second call should load from cache
        arr2, cache_path2 = self.client.retrieve_spatial_window(item, window_size_px=128)
        self.assertEqual(cache_path, cache_path2)


if __name__ == "__main__":
    unittest.main()

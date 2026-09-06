"""
Unit tests for multi-user team workflows and concurrency locks.
"""
import unittest

from database.models import ImageRecord, ImageStatus
from database.connection import SupabaseDBConnection
from database.repository import SupabaseLunarRepository
from database.team import TeamWorkflowManager
from storage.emulator import MockSupabaseDB


class TestTeamWorkflow(unittest.TestCase):

    def setUp(self):
        self.mock_db = MockSupabaseDB()
        self.conn = SupabaseDBConnection(use_mock=True, mock_db=self.mock_db)
        self.repo = SupabaseLunarRepository(db_connection=self.conn)
        self.team_mgr = TeamWorkflowManager(repository=self.repo)

        region = self.repo.get_region_by_code("R01")
        img_rec = ImageRecord(
            image_id="task_img_001",
            region_id=region["id"],
            sensor="OHRC",
            file_name="task_ohrc.zip",
            storage_path="R01/OHRC/task_ohrc.zip",
            file_format="ZIP",
            product_id="task_img_001",
            file_size_bytes=1024,
            sha256="hash_task_001_unique",
            status=ImageStatus.VALIDATED
        )
        self.db_img = self.repo.insert_image(img_rec)

    def test_assignment_and_concurrency_lock(self):
        img_id = self.db_img["id"]

        # 1. Assign to Alice
        assigned = self.team_mgr.assign_image(img_id, member_name="Alice")
        self.assertEqual(assigned["status"], "ASSIGNED")
        self.assertEqual(assigned["assigned_to"], "Alice")

        # 2. Alice acquires processing lock
        locked = self.team_mgr.acquire_processing_lock(img_id, member_name="Alice")
        self.assertEqual(locked["status"], "PROCESSING")
        self.assertEqual(locked["processing_owner"], "Alice")

        # 3. Bob attempts to acquire lock on the same image while Alice is processing -> PermissionError
        with self.assertRaises(PermissionError):
            self.team_mgr.acquire_processing_lock(img_id, member_name="Bob")

        # 4. Alice completes processing and releases lock
        completed = self.team_mgr.release_processing_lock(
            img_id,
            member_name="Alice",
            final_status=ImageStatus.COMPLETED,
            notes="Registration candidate verified"
        )
        self.assertEqual(completed["status"], "COMPLETED")
        self.assertIsNone(completed["processing_owner"])
        self.assertEqual(completed["last_processed_by"], "Alice")


if __name__ == "__main__":
    unittest.main()

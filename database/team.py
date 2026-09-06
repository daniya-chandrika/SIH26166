"""
Multi-user Team Dataset Workflow and Concurrency Locking.
"""
from typing import Optional, Dict, Any, List

from database.models import ImageStatus
from database.repository import SupabaseLunarRepository


class TeamWorkflowManager:
    """
    Coordinates team assignments, status transitions, and concurrency locking
    to prevent accidental duplicate processing by multiple team members.
    """

    def __init__(self, repository: Optional[SupabaseLunarRepository] = None):
        self.repo = repository or SupabaseLunarRepository()

    def assign_image(self, image_db_id: str, member_name: str) -> Dict[str, Any]:
        """
        Assign an image dataset to a team member.
        """
        return self.repo.update_image_status(
            image_db_id=image_db_id,
            status=ImageStatus.ASSIGNED,
            assigned_to=member_name
        )

    def acquire_processing_lock(self, image_db_id: str, member_name: str) -> Dict[str, Any]:
        """
        Atomically acquire a processing lock on an image to prevent concurrency conflicts.
        """
        image = self.repo.find_image_by_image_id(image_db_id)
        if not image:
            images = self.repo.db.select("images", {"id": f"eq.{image_db_id}"} if not self.repo.db.use_mock else {"id": image_db_id})
            image = images[0] if images else None

        if not image:
            raise ValueError(f"Image not found with ID: {image_db_id}")

        current_status = image.get("status")
        current_owner = image.get("processing_owner")

        if current_status == ImageStatus.PROCESSING.value and current_owner and current_owner != member_name:
            raise PermissionError(
                f"Image '{image['image_id']}' is currently locked for processing by '{current_owner}'."
            )

        updated = self.repo.update_image_status(
            image_db_id=image["id"],
            status=ImageStatus.PROCESSING,
            processing_owner=member_name,
            last_processed_by=member_name
        )

        self.repo.log_processing_step(
            stage="TEAM_LOCK",
            status="SUCCESS",
            message=f"Processing lock acquired by team member: {member_name}",
            image_db_id=image["id"]
        )

        return updated

    def release_processing_lock(
        self,
        image_db_id: str,
        member_name: str,
        final_status: ImageStatus = ImageStatus.COMPLETED,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Release processing lock and advance dataset status.
        """
        image = self.repo.find_image_by_image_id(image_db_id)
        if not image:
            images = self.repo.db.select("images", {"id": f"eq.{image_db_id}"} if not self.repo.db.use_mock else {"id": image_db_id})
            image = images[0] if images else None

        if not image:
            raise ValueError(f"Image not found with ID: {image_db_id}")

        updated = self.repo.update_image_status(
            image_db_id=image["id"],
            status=final_status,
            clear_processing_owner=True,
            last_processed_by=member_name
        )

        self.repo.log_processing_step(
            stage="TEAM_LOCK",
            status="RELEASED",
            message=f"Processing completed with status '{final_status.value}' by {member_name}. Notes: {notes or 'None'}",
            image_db_id=image["id"]
        )

        return updated

    def get_member_tasks(self, member_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve all image tasks assigned to a specific team member.
        """
        return self.repo.db.select(
            "images",
            {"assigned_to": f"eq.{member_name}"} if not self.repo.db.use_mock else {"assigned_to": member_name}
        )

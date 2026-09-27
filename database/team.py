"""
Multi-user Team Dataset Workflow and Concurrency Locking.
"""
from typing import Optional, Dict, Any, List

from database.models import ImageStatus
from database.repository import SupabaseLunarRepository

TEAM_REGIONS = [
    {"code": "R01", "name": "South Pole - Shackleton Rim", "center_lat": -89.90, "center_lon": 0.00, "description": "High-priority lunar south pole crater rim"},
    {"code": "R02", "name": "South Pole - Faustini / Shoemaker", "center_lat": -87.10, "center_lon": 84.30, "description": "Permanently shadowed region"},
    {"code": "R03", "name": "Tycho Crater Central Peak", "center_lat": -43.31, "center_lon": -11.36, "description": "Prominent Copernican impact crater"},
    {"code": "R04", "name": "Mare Tranquillitatis - Apollo 11", "center_lat": 0.67, "center_lon": 23.47, "description": "Basaltic mare plain"},
    {"code": "R05", "name": "Oceanus Procellarum - Aristarchus", "center_lat": 23.70, "center_lon": -47.40, "description": "High-albedo pyroclastic deposits"},
    {"code": "R06", "name": "South Pole-Aitken Basin Interior", "center_lat": -53.00, "center_lon": 169.00, "description": "Deepest lunar far side basin"},
    {"code": "R07", "name": "Mare Imbrium - Archimedes Crater", "center_lat": 29.70, "center_lon": -4.00, "description": "Large impact basin floor"},
    {"code": "R08", "name": "Copernicus Crater Rim & Floor", "center_lat": 9.62, "center_lon": -20.08, "description": "Terraced rayed impact crater"},
    {"code": "R09", "name": "Mare Serenitatis - Posidonius", "center_lat": 31.80, "center_lon": 29.90, "description": "Floor-fractured crater"},
    {"code": "R10", "name": "Hertzsprung Basin Far-Side", "center_lat": 1.60, "center_lon": -128.60, "description": "Multi-ringed far-side basin"}
]



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

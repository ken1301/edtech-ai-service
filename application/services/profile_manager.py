from domain.ports.profile_store_port import ProfileStorePort

from domain.models.curriculum import Subject
from domain.models.profile import TopicMastery, StudentPreference, StudentProfile

from domain.exceptions import ProfileManagerError, ProfileStoreError

from infrastructure.logging import logger

class ProfileManager:
    """Service responsible for managing student profiles, including retrieving and updating student information."""

    def __init__(
        self,
        profile_store: ProfileStorePort
    ):
        self._profile_store = profile_store

    async def get_student_profile(self, user_id: str) -> StudentProfile:
        """Fetch the student profile from the profile store (MongoDB) using the user ID."""
        try: 
            student_profile = await self._profile_store.get_student_profile(user_id=user_id)
            logger.info(
                "profile_manager.get_student_profile.completed",
                log_type="business",
                user_id=user_id,
            )
            return student_profile
        
        except ProfileStoreError as e:
            raise ProfileManagerError("Failed to retrieve student profile from the profile store.") from e

        except Exception as e:
            logger.error(
                "profile_manager.get_student_profile.unexpected.failed",
                log_type="technical",
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise ProfileManagerError("Unexpected error while retrieving student profile.") from e

    async def update_student_profile(
        self,
        user_id: str,
        subject: Subject,
        topic: str,
        student_preference: StudentPreference,
        topic_mastery: TopicMastery
    ):
        """Update the student profile in the profile store (MongoDB) with the new preference and knowledge map."""
        try:
            await self._profile_store.update_student_profile(
                user_id=user_id,
                subject=subject,
                topic=topic,
                student_preference=student_preference,
                topic_mastery=topic_mastery
            )
            
            logger.info(
                "profile_manager.update_student_profile.completed",
                log_type="business",
                user_id=user_id,
            )
        
        except ProfileStoreError as e:
            raise ProfileManagerError("Failed to update student profile in the profile store.") from e
        
        except Exception as e:
            logger.error(
                "profile_manager.update_student_profile.unexpected.failed",
                log_type="technical",
                user_id=user_id,
                subject=subject,
                topic=topic,
                error=str(e),
                exc_info=True,
            )
            raise ProfileManagerError("Unexpected error while updating student profile.") from e
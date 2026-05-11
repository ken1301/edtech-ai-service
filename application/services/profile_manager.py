from domain.ports.profile_store_port import ProfileStorePort

from domain.models.profile import TopicMastery, StudentPreference, Subject

from domain.exceptions import ProfileManagerError, ProfileStoreError

from infrastructure.logging import logger

class ProfileManager:
    """Service responsible for managing student profiles, including retrieving and updating student information."""

    def __init__(
        self,
        profile_store: ProfileStorePort
    ):
        self._profile_store = profile_store

    async def update_student_profile(
        self,
        student_id: str,
        subject: Subject,
        topic: str,
        student_preference: StudentPreference,
        topic_mastery: TopicMastery
    ):
        """Update the student profile in the profile store (MongoDB) with the new preference and knowledge map."""
        try:
            await self._profile_store.update_student_profile(
                student_id=student_id,
                subject=subject,
                topic=topic,
                student_preference=student_preference,
                topic_mastery=topic_mastery
            )
            
            logger.info(
                "profile_manager.update_student_profile.completed",
                log_type="business",
                student_id=student_id,
            )
        
        except ProfileStoreError as e:
            logger.error(
                "profile_manager.update_student_profile.failed",
                log_type="technical",
                student_id=student_id,
                subject=subject,
                topic=topic,
                error=str(e),
            )
            raise ProfileManagerError("Failed to update student profile in the profile store.") from e
        
        except Exception as e:
            logger.error(
                "profile_manager.update_student_profile.unexpected.failed",
                log_type="technical",
                student_id=student_id,
                subject=subject,
                topic=topic,
                error=str(e),
            )
            raise ProfileManagerError("Unexpected error while updating student profile.") from e
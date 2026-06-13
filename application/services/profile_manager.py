from domain.ports.profile_store_port import ProfileStorePort

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.profile import StudentPreference, StudentProfile, LearningDetail

from domain.exceptions import ProfileManagerError, ProfileStoreError

from infrastructure.logging import logger

class ProfileManager:
    """Service responsible for managing student profiles, including retrieving and updating student information."""

    def __init__(
        self,
        profile_store: ProfileStorePort
    ):
        self._profile_store = profile_store

    async def get_student_profile(self, user_id: str) -> StudentProfile | None:
        """Fetch the student profile from the profile store (MongoDB) using the user ID."""
        try: 
            student_profile = await self._profile_store.get_student_profile(user_id=user_id)

            if not student_profile:
                logger.warning(
                    "profile_manager.get_student_profile.not_found",
                    log_type="business",
                    user_id=user_id,
                )
                return None

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
        topic: Topic,
        concept: Concept,
        student_preference: StudentPreference,
        learning_detail: LearningDetail
    ):
        """Update the student profile in the profile store (MongoDB) with the new preference and knowledge map."""
        try:
            await self._profile_store.update_student_profile(
                user_id=user_id,
                subject=subject,
                topic=topic,
                concept=concept,
                student_preference=student_preference,
                learning_detail=learning_detail
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
                concept=concept,
                error=str(e),
                exc_info=True,
            )
            raise ProfileManagerError("Unexpected error while updating student profile.") from e
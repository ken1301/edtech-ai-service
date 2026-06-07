from abc import ABC, abstractmethod

from domain.models.overall_models.profile import StudentPreference, LearningDetail, StudentProfile
from domain.models.overall_models.curriculum import Subject, Topic, Concept

class ProfileStorePort(ABC):
    """
    Abstract port for student profile storage.

    One concrete adapter implements this port:
        - MongoProfileAdapter — persistent profile store (MongoDB)
    """

    @abstractmethod
    async def get_student_profile(self, user_id: str) -> StudentProfile | None:
        """
        Return the full student profile for the given ID, or None if not found.
        """

    @abstractmethod
    async def update_student_profile(
        self,
        user_id: str,
        subject: Subject,
        topic: Topic,
        concept: Concept,
        student_preference: StudentPreference,
        learning_detail: LearningDetail
    ) -> None:
        """
        Upsert the student profile with updated preference and topic mastery.

        - Merges `topic_mastery` into the knowledge map under
          `knowledge_map.<subject>.<topic>` without touching other entries.
        - Overwrites the `preferences` block entirely with the latest values.
        - Creates the profile document if it does not yet exist.
        """
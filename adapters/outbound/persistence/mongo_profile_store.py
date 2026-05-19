from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from domain.ports.profile_store_port import ProfileStorePort
from domain.models.profile import (
    StudentProfile,
    TopicMastery,
    StudentPreference,
    Subject,
)
from domain.exceptions import ProfileStoreError

from infrastructure.logging import logger


class MongoProfileAdapter(ProfileStorePort):
    """
    MongoDB adapter for student profile storage.

    Collection: `student_profiles`

    Document shape:
    {
        "_id": ObjectId,
        "user_id": str  (unique index),
        "full_name": str | None,
        "grade": str | None,
        "preferences": {StudentPreference fields},
        "knowledge_map": {
            "math": {
                "fractions": {TopicMastery fields},
                ...
            },
            "physics": { ... },
        },
        "created_at": datetime,
        "updated_at": datetime
    }
    """

    _COLLECTION = "student_profiles"

    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[self._COLLECTION]

    # ── ProfileStorePort interface ────────────────────────────────────────────

    async def get_student_profile(self, user_id: str) -> StudentProfile | None:
        """Return the student profile document, or None if not found."""
        try:
            doc = await self._col.find_one({"user_id": user_id})
        except PyMongoError as e:
            logger.error(
                "mongo_profile_adapter.get_student_profile.failed",
                log_type="technical",
                user_id=user_id,
                error=str(e),
            )
            raise ProfileStoreError(
                f"Failed to fetch profile for user '{user_id}' from MongoDB."
            ) from e

        if not doc:
            logger.warning(
                "mongo_profile_adapter.get_student_profile.not_found",
                log_type="technical",
                user_id=user_id,
            )
            return None

        try:
            return self._deserialize_profile(doc)
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "mongo_profile_adapter.get_student_profile.deserialize_failed",
                log_type="technical",
                user_id=user_id,
                error=str(e),
            )
            raise ProfileStoreError(
                f"Corrupt profile document for user '{user_id}'."
            ) from e

    async def update_student_profile(
        self,
        user_id: str,
        subject: Subject,
        topic: str,
        student_preference: StudentPreference,
        topic_mastery: TopicMastery,
    ) -> None:
        """
        Upsert a student profile.
        - Merges the new topic mastery into the existing knowledge map via
          dot-notation so other subjects/topics are never overwritten.
        - Overwrites the preference block with the latest observed values.
        """
        now = datetime.now(timezone.utc)

        update = {
            "$set": {
                f"knowledge_map.{subject.value}.{topic}": topic_mastery.model_dump(),
                "preferences": student_preference.model_dump(),
                "updated_at":  now,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": now,
            },
        }

        try:
            await self._col.update_one(
                {"user_id": user_id},
                update,
                upsert=True,
            )
        except PyMongoError as e:
            logger.error(
                "mongo_profile_adapter.update_student_profile.failed",
                log_type="technical",
                user_id=user_id,
                subject=subject.value,
                topic=topic,
                error=str(e),
            )
            raise ProfileStoreError(
                f"Failed to update profile for user '{user_id}' in MongoDB."
            ) from e

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _deserialize_profile(doc: dict) -> StudentProfile:
        return StudentProfile(
            user_id=doc["user_id"],
            full_name=doc.get("full_name"),
            grade=doc.get("grade"),
            preferences=(
                StudentPreference(**doc["preferences"])
                if doc.get("preferences") else None
            ),
            knowledge_map={
                subject: {
                    topic: TopicMastery(**mastery)
                    for topic, mastery in topics.items()
                }
                for subject, topics in doc.get("knowledge_map", {}).items()
            },
        )
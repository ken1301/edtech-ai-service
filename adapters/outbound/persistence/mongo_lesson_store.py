import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from domain.ports.lesson_store_port import LessonStorePort

from domain.models.lesson2_models.exercise import Exercise
from domain.models.overall_models.lesson1 import LessonArtifact

from domain.exceptions import LessonStoreError

from infrastructure.logging import logger

class MongoLessonAdapter(LessonStorePort):

    _COLLECTION = "exercises"
    _OWNERSHIP_INDEX_NAME = "user_id_exercise_id_unique"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[self._COLLECTION]
        self._index_lock = asyncio.Lock()
        self._indexes_ready = False

    async def _ensure_indexes(self) -> None:
        if self._indexes_ready:
            return

        async with self._index_lock:
            if self._indexes_ready:
                return

            await self._col.create_index(
                [("user_id", ASCENDING), ("exercise_id", ASCENDING)],
                unique=True,
                name=self._OWNERSHIP_INDEX_NAME,
                partialFilterExpression={
                    "user_id": {"$type": "string"},
                    "exercise_id": {"$type": "string"},
                },
            )
            self._indexes_ready = True

    async def save_exercise(
        self,
        exercise_id: str,
        user_id: str,
        exercise: LessonArtifact,
    ) -> bool:
        now = datetime.now(timezone.utc)
        payload = exercise.model_dump(mode="json", exclude_none=True)
        if payload.get("lesson1") is None:
            payload["lesson1"] = {}
        if payload.get("lesson2") is None:
            payload["lesson2"] = {}

        try:
            await self._ensure_indexes()
            result = await self._col.update_one(
                {"exercise_id": exercise_id, "user_id": user_id},
                {
                    "$set": {
                        **payload,
                        "user_id": user_id,
                        "updated_at": now,
                        "subject": exercise.subject.value,
                        "topic": exercise.topic.value,
                        "concept": exercise.concept.value,
                    },
                    "$setOnInsert": {
                        "exercise_id": exercise_id,
                        "created_at": now,
                    },
                },
                upsert=True,
            )
            logger.debug(
                "mongo_lesson_store.save_exercise.completed",
                log_type="debug",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            return result.acknowledged
        except PyMongoError as e:
            logger.error(
                "mongo_lesson_store.save_exercise.failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Failed to save exercise '{exercise_id}' to MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_lesson_store.save_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while saving an exercise.") from e

    async def get_lesson_artifact(self, exercise_id: str, user_id: str) -> LessonArtifact:
        try:
            await self._ensure_indexes()
            doc = await self._col.find_one({"exercise_id": exercise_id, "user_id": user_id})
        except PyMongoError as e:
            logger.error(
                "mongo_lesson_store.get_lesson_artifact.failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Failed to fetch lesson artifact '{exercise_id}' from MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_lesson_store.get_lesson_artifact.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while fetching a lesson artifact.") from e

        if not doc:
            logger.error(
                "mongo_lesson_store.get_lesson_artifact.not_found",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            raise LessonStoreError(f"Lesson artifact '{exercise_id}' was not found in MongoDB.")

        try:
            doc = dict(doc)
            if doc.get("lesson1") == {}:
                doc["lesson1"] = None
            if doc.get("lesson2") == {}:
                doc["lesson2"] = None
            logger.debug(
                "mongo_lesson_store.get_lesson_artifact.completed",
                log_type="debug",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            return LessonArtifact(**doc)
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "mongo_lesson_store.get_lesson_artifact.deserialize_failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Corrupt lesson artifact document for '{exercise_id}'.") from e
        except Exception as e:
            logger.error(
                "mongo_lesson_store.get_lesson_artifact.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while deserializing a lesson artifact.") from e

    async def get_exercise(self, exercise_id: str, user_id: str) -> Exercise:
        doc = await self.get_lesson_artifact(exercise_id=exercise_id, user_id=user_id)
        try:
            logger.debug(
                "mongo_lesson_store.get_exercise.completed",
                log_type="debug",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            if doc.lesson2 is None:
                raise LessonStoreError(f"Exercise '{exercise_id}' does not contain lesson 2 data.")
            return doc.lesson2.exercise
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "mongo_lesson_store.get_exercise.deserialize_failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Corrupt exercise document for '{exercise_id}'.") from e
        except LessonStoreError:
            raise
        except Exception as e:
            logger.error(
                "mongo_lesson_store.get_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while deserializing an exercise.") from e

    @staticmethod
    def _public_lesson_filters(exercise_id: str) -> list[dict]:
        filters: list[dict] = [
            {"exercise_id": exercise_id},
            {"root_lesson_id": exercise_id},
        ]
        if ObjectId.is_valid(exercise_id):
            filters.append({"_id": ObjectId(exercise_id)})
        return filters

    async def _find_public_lesson_doc(self, exercise_id: str) -> dict | None:
        return await self._col.find_one(
            {
                "$or": self._public_lesson_filters(exercise_id),
                "lesson2.exercise": {"$exists": True},
            }
        )

    async def _find_draft_bridge_doc(self, exercise_id: str) -> dict | None:
        return await self._col.find_one(
            {
                "$or": self._public_lesson_filters(exercise_id),
                "lesson2_exercise_id": {"$type": "string"},
            }
        )

    async def get_public_exercise(self, exercise_id: str) -> Exercise | None:
        try:
            await self._ensure_indexes()
            doc = await self._find_public_lesson_doc(exercise_id)

            if not doc:
                bridge_doc = await self._find_draft_bridge_doc(exercise_id)
                linked_exercise_id = bridge_doc.get("lesson2_exercise_id") if bridge_doc else None
                if isinstance(linked_exercise_id, str) and linked_exercise_id:
                    doc = await self._find_public_lesson_doc(linked_exercise_id)
        except PyMongoError as e:
            logger.error(
                "mongo_lesson_store.get_public_exercise.failed",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise LessonStoreError(f"Failed to fetch published lesson 2 exercise '{exercise_id}' from MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_lesson_store.get_public_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while fetching a published lesson 2 exercise.") from e

        if not doc:
            logger.info(
                "mongo_lesson_store.get_public_exercise.not_found",
                log_type="business",
                exercise_id=exercise_id,
            )
            return None

        try:
            artifact = LessonArtifact(**dict(doc))
            if artifact.lesson2 is None:
                return None
            logger.debug(
                "mongo_lesson_store.get_public_exercise.completed",
                log_type="debug",
                exercise_id=exercise_id,
            )
            return artifact.lesson2.exercise
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "mongo_lesson_store.get_public_exercise.deserialize_failed",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise LessonStoreError(f"Corrupt published lesson 2 exercise document for '{exercise_id}'.") from e
        except Exception as e:
            logger.error(
                "mongo_lesson_store.get_public_exercise.unexpected_deserialize_error",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while deserializing a published lesson 2 exercise.") from e

    async def delete_exercise(self, exercise_id: str, user_id: str) -> bool:
        try:
            await self._ensure_indexes()
            result = await self._col.delete_one({"exercise_id": exercise_id, "user_id": user_id})
            logger.debug(
                "mongo_lesson_store.delete_exercise.completed",
                log_type="debug",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(
                "mongo_lesson_store.delete_exercise.failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Failed to delete exercise '{exercise_id}' from MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_lesson_store.delete_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while deleting an exercise.") from e

    async def attach_root_lesson_id(self, exercise_id: str, user_id: str, root_lesson_id: str) -> bool:
        try:
            await self._ensure_indexes()
            result = await self._col.update_one(
                {"exercise_id": exercise_id, "user_id": user_id},
                {
                    "$set": {
                        "root_lesson_id": root_lesson_id,
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            logger.debug(
                "mongo_lesson_store.attach_root_lesson_id.completed",
                log_type="debug",
                exercise_id=exercise_id,
                user_id=user_id,
                root_lesson_id=root_lesson_id,
            )
            matched_count = getattr(result, "matched_count", 1)
            return result.acknowledged and matched_count > 0
        except PyMongoError as e:
            logger.error(
                "mongo_lesson_store.attach_root_lesson_id.failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                root_lesson_id=root_lesson_id,
                error=str(e),
            )
            raise LessonStoreError(
                f"Failed to attach root lesson id for exercise '{exercise_id}'."
            ) from e
        except Exception as e:
            logger.error(
                "mongo_lesson_store.attach_root_lesson_id.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                root_lesson_id=root_lesson_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while attaching root lesson id.") from e

    async def save_lesson_creation_metadata(self, *args, **kwargs):
        raise NotImplementedError("save_lesson_creation_metadata is a Redis operation.")

    async def get_lesson_creation_metadata(self, *args, **kwargs):
        raise NotImplementedError("get_lesson_creation_metadata is a Redis operation.")

    async def delete_lesson_creation_metadata(self, *args, **kwargs):
        raise NotImplementedError("delete_lesson_creation_metadata is a Redis operation.")
    
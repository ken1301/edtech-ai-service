import asyncio
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING
from pymongo.errors import PyMongoError

from domain.ports.lesson_store_port import LessonStorePort

from domain.models.lesson2_models.exercise import Exercise

from domain.exceptions import LessonStoreError

from infrastructure.logging import logger

class MongoExerciseAdapter(LessonStorePort):

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
                    "user_id": {"$exists": True, "$ne": None},
                    "exercise_id": {"$exists": True, "$ne": None},
                },
            )
            self._indexes_ready = True

    async def save_exercise(
        self,
        exercise_id: str,
        user_id: str,
        exercise: Exercise
    ) -> bool:
        now = datetime.now(timezone.utc)

        try:
            await self._ensure_indexes()
            result = await self._col.update_one(
                {"exercise_id": exercise_id, "user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "exercise": exercise.model_dump(mode="json"),
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
                "mongo_exercise_store.save_exercise.completed",
                log_type="debug",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            return result.acknowledged
        except PyMongoError as e:
            logger.error(
                "mongo_exercise_store.save_exercise.failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Failed to save exercise '{exercise_id}' to MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_exercise_store.save_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while saving an exercise.") from e

    async def get_exercise(self, exercise_id: str, user_id: str) -> Exercise:
        try:
            await self._ensure_indexes()
            doc = await self._col.find_one({"exercise_id": exercise_id, "user_id": user_id})
        except PyMongoError as e:
            logger.error(
                "mongo_exercise_store.get_exercise.failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Failed to fetch exercise '{exercise_id}' from MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_exercise_store.get_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while fetching an exercise.") from e

        if not doc:
            logger.error(
                "mongo_exercise_store.get_exercise.not_found",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            raise LessonStoreError(f"Exercise '{exercise_id}' was not found in MongoDB.")

        try:
            logger.debug(
                "mongo_exercise_store.get_exercise.completed",
                log_type="debug",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            return Exercise(**doc["exercise"])
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "mongo_exercise_store.get_exercise.deserialize_failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Corrupt exercise document for '{exercise_id}'.") from e
        except Exception as e:
            logger.error(
                "mongo_exercise_store.get_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while deserializing an exercise.") from e

    async def delete_exercise(self, exercise_id: str, user_id: str) -> bool:
        try:
            await self._ensure_indexes()
            result = await self._col.delete_one({"exercise_id": exercise_id, "user_id": user_id})
            logger.debug(
                "mongo_exercise_store.delete_exercise.completed",
                log_type="debug",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(
                "mongo_exercise_store.delete_exercise.failed",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError(f"Failed to delete exercise '{exercise_id}' from MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_exercise_store.delete_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                user_id=user_id,
                error=str(e),
            )
            raise LessonStoreError("An unexpected error occurred while deleting an exercise.") from e

    async def save_lesson_creation_metadata(self, *args, **kwargs):
        raise NotImplementedError("save_lesson_creation_metadata is a Redis operation.")

    async def get_lesson_creation_metadata(self, *args, **kwargs):
        raise NotImplementedError("get_lesson_creation_metadata is a Redis operation.")
    
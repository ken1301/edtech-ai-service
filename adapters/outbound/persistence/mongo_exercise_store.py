from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError

from domain.ports.exercise_store_port import ExerciseStorePort

from domain.models.lesson2_models.exercise import Exercise

from domain.exceptions import ExerciseStoreError

from infrastructure.logging import logger

class MongoExerciseAdapter(ExerciseStorePort):

    _COLLECTION = "exercises"
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[self._COLLECTION]

    async def save_exercise(
        self,
        exercise_id: str,
        author_id: str,
        exercise: Exercise
    ) -> bool:
        now = datetime.now(timezone.utc)

        try:
            result = await self._col.update_one(
                {"exercise_id": exercise_id},
                {
                    "$set": {
                        "author_id": author_id,
                        "exercise": exercise.model_dump(mode="json"),
                        "updated_at": now,
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
                author_id=author_id,
            )
            return result.acknowledged
        except PyMongoError as e:
            logger.error(
                "mongo_exercise_store.save_exercise.failed",
                log_type="technical",
                exercise_id=exercise_id,
                author_id=author_id,
                error=str(e),
            )
            raise ExerciseStoreError(f"Failed to save exercise '{exercise_id}' to MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_exercise_store.save_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                author_id=author_id,
                error=str(e),
            )
            raise ExerciseStoreError("An unexpected error occurred while saving an exercise.") from e

    async def get_exercise_by_id(self, exercise_id: str) -> Exercise:
        try:
            doc = await self._col.find_one({"exercise_id": exercise_id})
        except PyMongoError as e:
            logger.error(
                "mongo_exercise_store.get_exercise_by_id.failed",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise ExerciseStoreError(f"Failed to fetch exercise '{exercise_id}' from MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_exercise_store.get_exercise_by_id.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise ExerciseStoreError("An unexpected error occurred while fetching an exercise.") from e

        if not doc:
            logger.error(
                "mongo_exercise_store.get_exercise_by_id.not_found",
                log_type="technical",
                exercise_id=exercise_id,
            )
            raise ExerciseStoreError(f"Exercise '{exercise_id}' was not found in MongoDB.")

        try:
            logger.debug(
                "mongo_exercise_store.get_exercise_by_id.completed",
                log_type="debug",
                exercise_id=exercise_id
            )
            return Exercise(**doc["exercise"])
        except (KeyError, TypeError, ValueError) as e:
            logger.error(
                "mongo_exercise_store.get_exercise_by_id.deserialize_failed",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise ExerciseStoreError(f"Corrupt exercise document for '{exercise_id}'.") from e
        except Exception as e:
            logger.error(
                "mongo_exercise_store.get_exercise_by_id.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise ExerciseStoreError("An unexpected error occurred while deserializing an exercise.") from e

    async def delete_exercise(self, exercise_id: str) -> bool:
        try:
            result = await self._col.delete_one({"exercise_id": exercise_id})
            logger.debug(
                "mongo_exercise_store.delete_exercise.completed",
                log_type="debug",
                exercise_id=exercise_id,
            )
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(
                "mongo_exercise_store.delete_exercise.failed",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise ExerciseStoreError(f"Failed to delete exercise '{exercise_id}' from MongoDB.") from e
        except Exception as e:
            logger.error(
                "mongo_exercise_store.delete_exercise.unexpected_error",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
            )
            raise ExerciseStoreError("An unexpected error occurred while deleting an exercise.") from e
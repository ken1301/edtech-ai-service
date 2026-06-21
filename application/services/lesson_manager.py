from domain.ports.lesson_store_port import LessonStorePort

from domain.models.lesson2_models.exercise import Exercise
from domain.models.overall_models.lesson1 import CreateLessonMetadata

from domain.exceptions import LessonManagerError, LessonStoreError

from infrastructure.logging import logger


class LessonManager:
    """Service responsible for managing lesson metadata and exercises."""

    def __init__(
        self,
        exercise_store_port: LessonStorePort,
        lesson_creation_store_port: LessonStorePort,
    ):
        self._exercise_store_port = exercise_store_port
        self._lesson_creation_store_port = lesson_creation_store_port

    async def save_lesson_creation_metadata(self, lesson_id: str, metadata: CreateLessonMetadata) -> bool:
        try:
            result = await self._lesson_creation_store_port.save_lesson_creation_metadata(
                lesson_id=lesson_id,
                metadata=metadata
            )
            logger.info(
                "lesson_manager.save_lesson_creation_metadata.completed",
                log_type="business",
                lesson_id=lesson_id,
            )
            return result

        except LessonStoreError as e:
            raise LessonManagerError("Failed to save lesson creation metadata.") from e

        except Exception as e:
            logger.error(
                "lesson_manager.save_lesson_creation_metadata.unexpected.failed",
                log_type="technical",
                lesson_id=lesson_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonManagerError("Unexpected error while saving lesson creation metadata.") from e

    async def get_lesson_creation_metadata(self, lesson_id: str) -> CreateLessonMetadata:
        try:
            metadata = await self._lesson_creation_store_port.get_lesson_creation_metadata(lesson_id=lesson_id)
            logger.info(
                "lesson_manager.get_lesson_creation_metadata.completed",
                log_type="business",
                lesson_id=lesson_id,
            )
            return metadata

        except LessonStoreError as e:
            raise LessonManagerError("Failed to retrieve lesson creation metadata.") from e

        except Exception as e:
            logger.error(
                "lesson_manager.get_lesson_creation_metadata.unexpected.failed",
                log_type="technical",
                lesson_id=lesson_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonManagerError("Unexpected error while retrieving lesson creation metadata.") from e

    async def save_exercise(
        self, 
        exercise_id: str,
        user_id: str,
        exercise: Exercise
    ) -> bool:
        """Save an exercise to the exercise store."""
        try:
            result = await self._exercise_store_port.save_exercise(
                exercise_id=exercise_id,
                user_id=user_id,
                exercise=exercise
            )
            logger.info(
                "lesson_manager.save_exercise.completed",
                log_type="business",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            return result
        
        except LessonStoreError as e:
            raise LessonManagerError("Failed to save exercise to the exercise store.") from e

        except Exception as e:
            logger.error(
                "lesson_manager.save_exercise.unexpected.failed",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonManagerError("Unexpected error while saving exercise.") from e

    async def get_exercise(self, exercise_id: str, user_id: str) -> Exercise:
        """Retrieve an exercise from the exercise store using its unique identifier."""
        try:
            exercise = await self._exercise_store_port.get_exercise(exercise_id=exercise_id)

            if not exercise:
                logger.warning(
                    "lesson_manager.get_exercise.not_found",
                    log_type="business",
                    exercise_id=exercise_id,
                    user_id=user_id,
                )
                raise LessonManagerError(f"Exercise with ID '{exercise_id}' not found.")

            logger.info(
                "lesson_manager.get_exercise.completed",
                log_type="business",
                exercise_id=exercise_id,
                user_id=user_id,
            )
            return exercise
        
        except LessonStoreError as e:
            raise LessonManagerError("Failed to retrieve exercise from the exercise store.") from e

        except Exception as e:
            logger.error(
                "lesson_manager.get_exercise.unexpected.failed",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
                exc_info=True,
            )
            raise LessonManagerError("Unexpected error while retrieving exercise.") from e
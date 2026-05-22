from domain.ports.exercise_store_port import ExerciseStorePort
from domain.models.exercise import Exercise

from domain.exceptions import ExerciseManagerError, ExerciseStoreError

from infrastructure.logging import logger


class ExerciseManager:
    """Service responsible for managing exercises, including retrieval and selection of exercises based on specific criteria."""

    def __init__(self, exercise_store_port: ExerciseStorePort):
        self._exercise_store_port = exercise_store_port

    async def save_exercise(
        self, 
        exercise_id: str,
        author_id: str,
        exercise: Exercise
    ) -> bool:
        """Save an exercise to the exercise store."""
        try:
            result = await self._exercise_store_port.save_exercise(
                exercise_id=exercise_id,
                author_id=author_id,
                exercise=exercise
            )
            logger.info(
                "exercise_manager.save_exercise.completed",
                log_type="business",
                exercise_id=exercise_id,
                author_id=author_id,
            )
            return result
        
        except ExerciseStoreError as e:
            raise ExerciseManagerError("Failed to save exercise to the exercise store.") from e

        except Exception as e:
            logger.error(
                "exercise_manager.save_exercise.unexpected.failed",
                log_type="technical",
                exercise_id=exercise_id,
                error=str(e),
                exc_info=True,
            )
            raise ExerciseManagerError("Unexpected error while saving exercise.") from e

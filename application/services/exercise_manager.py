from typing import List

from domain.ports.exercise_store_port import ExerciseStorePort
from domain.models.exercise import Exercise



class ExerciseManager:
    """Service responsible for managing exercises, including retrieval and selection of exercises based on specific criteria."""

    def __init__(self, exercise_store_port: ExerciseStorePort):
        self._exercise_store_port = exercise_store_port

    async def save_exercise(self, exercise: Exercise) -> bool:
        """Save an exercise to the exercise store."""
        pass

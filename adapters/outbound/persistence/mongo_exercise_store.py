from typing import List

from domain.ports.exercise_store_port import ExerciseStorePort

from domain.models.exercise import Exercise

from domain.exceptions import ExerciseStoreError

from infrastructure.logging import logger

class MongoExerciseAdapter(ExerciseStorePort):
    
    def __init__(self):
        pass

    async def save_exercise(self, exercise: Exercise) -> bool:
        pass

    async def get_exercise_by_id(self, exercise_id: str) -> Exercise:
        pass

    async def delete_exercise(self, exercise_id: str) -> bool:
        pass
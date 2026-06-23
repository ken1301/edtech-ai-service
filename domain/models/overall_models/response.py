from typing import Any, List, Union

from pydantic import BaseModel

from domain.models.lesson2_models.exercise import Exercise
from domain.models.overall_models.lesson1 import Lesson1CreationOutput
from domain.models.overall_models.token_usage import TokenUsage

class LLMResponse(BaseModel):
    content: Union[str, BaseModel]
    model_name: str
    finish_reason: str
    usage: TokenUsage

class Lesson1CreationResponse(BaseModel):
    exercise_id: str
    output: Lesson1CreationOutput
    usage: TokenUsage

class Lesson2ChatResponse(BaseModel):
    content: str
    usage: List[Any]
    current_progress: float

class SyncAndCloseResponse(BaseModel):
    status: str
    detail: str


class Lesson2ExerciseExtractionOutput(BaseModel):
    exercise: Exercise
    summary: str


class Lesson2ExerciseExtractionResponse(BaseModel):
    exercise_id: str
    output: Lesson2ExerciseExtractionOutput
    usage: TokenUsage


class FinalizeLessonResponse(BaseModel):
    status: str
    lesson_id: str
    lesson1_exercise_id: str
    lesson2_exercise_id: str

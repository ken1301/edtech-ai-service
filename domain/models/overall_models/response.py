from pydantic import BaseModel
from typing import Dict, Any, Union, List

from domain.models.lesson2_models.exercise import Exercise
from domain.models.overall_models.lesson1 import Lesson1CreationOutput
from domain.models.overall_models.token_usage import TokenUsage

class LLMResponse(BaseModel):
    content: Union[str, BaseModel]
    model_name: str
    finish_reason: str
    usage: TokenUsage

class Lesson1CreationResponse(BaseModel):
    output: Lesson1CreationOutput
    usage: TokenUsage
    correlation_id: str

class Lesson2ChatResponse(BaseModel):
    content: str
    usage: List[Any]
    correlation_id: str
    current_progress: float


class SyncAndCloseResponse(BaseModel):
    status: str
    detail: str
    correlation_id: str

class Lesson2ExerciseExtractionResponse(BaseModel):
    exercise_id: str
    output: Exercise
    usage: TokenUsage
    correlation_id: str

from pydantic import BaseModel
from typing import Optional, Dict, Any, Union, List

from domain.models.lesson2_models.exercise import Exercise

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: Optional[float] = None


class LLMResponse(BaseModel):
    content: Union[str, BaseModel]
    model_name: str
    finish_reason: str
    usage: TokenUsage


class Lesson2ChatResponse(BaseModel):
    content: str
    usage: List[Any]
    correlation_id: str
    current_progress: float


class ExerciseExtractionResponse(BaseModel):
    output: Exercise
    usage: TokenUsage
    correlation_id: str

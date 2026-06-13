from pydantic import BaseModel
from typing import Optional, Literal

from domain.models.lesson2_models.meta import Lesson2Request

ChatRequest = Lesson2Request

class ExerciseExtractionRequest(BaseModel):
    user_id: str
    corr_id: str

    document_url: str

    subject: str
    topic: str
    concept: str



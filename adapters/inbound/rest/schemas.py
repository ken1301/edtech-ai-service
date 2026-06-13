from pydantic import BaseModel
from typing import Optional, Literal, List

from domain.models.lesson2_models.exercise import Problem
from domain.models.lesson2_models.meta import Lesson2Request

from domain.models.overall_models.curriculum import Subject, Topic, Concept

ChatRequest = Lesson2Request

class ExerciseExtractionRequest(BaseModel):
    user_id: str
    correlation_id: str

    document_url: str

    subject: Subject
    topic: Topic
    concept: Concept

class ExerciseSelectionRequest(BaseModel):
    exercise_id: str
    user_id: str
    correlation_id: str

class ExerciseSelectionResponse(BaseModel):
    selected_problems: List[Problem]
    correlation_id: str

class SyncAndCloseRequest(BaseModel):
    user_id: str
    session_id: str
    correlation_id: str
    subject: Subject
    topic: Topic
    concept: Concept

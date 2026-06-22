from pydantic import BaseModel, Field
from typing import Optional, Literal, List

from domain.models.lesson2_models.exercise import Problem
from domain.models.lesson2_models.meta import Lesson2Request, NonEmptyId

from domain.models.overall_models.curriculum import Subject, Topic, Concept

ChatRequest = Lesson2Request

class DocumentExtractionRequest(BaseModel):
    user_id: NonEmptyId
    correlation_id: NonEmptyId
    lesson_id: NonEmptyId

    document_url: Optional[str] = None
    previous_lesson: List[Concept] = Field(default_factory=list)
    
    subject: Subject
    topic: Topic
    concept: Concept
    
class ExerciseExtractionRequest(BaseModel):
    user_id: NonEmptyId
    correlation_id: NonEmptyId
    lesson_id: NonEmptyId

    document_url: Optional[str] = None

    subject: Subject
    topic: Topic
    concept: Concept

class ExerciseSelectionRequest(BaseModel):
    exercise_id: NonEmptyId
    user_id: NonEmptyId
    correlation_id: NonEmptyId

class ExerciseSelectionResponse(BaseModel):
    selected_problems: List[Problem]
    correlation_id: str

class SyncAndCloseRequest(BaseModel):
    user_id: NonEmptyId
    session_id: NonEmptyId
    correlation_id: NonEmptyId
    subject: Subject
    topic: Topic
    concept: Concept

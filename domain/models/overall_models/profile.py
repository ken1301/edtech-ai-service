from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.overall_models.common import (
    ConceptType,
    BloomLevel,
    ProblemRole,
    ApproachStrength,
    ApproachWeakness,
    DifficultyLevel,
    CognitiveOperation,
    Representation,
    StudentStrength,
    StudentWeakness
)


class StudentPattern(BaseModel):
    cognitive_operation: List[CognitiveOperation] = []
    representation: List[Representation] = []


class Performance(BaseModel):
    score: float
    bloom_level: BloomLevel
    strengths: List[ApproachStrength]
    weaknesses: List[ApproachWeakness]
    pattern: StudentPattern


class LearningDetail(BaseModel):
    avg_score: float
    last_practiced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    mastering_at: List[ConceptType] = []
    struggling_at: List[ConceptType] = []

    finished_exercise: Dict[ProblemRole, Performance] = {}


class LearningStyle(BaseModel):
    cognitive_operation: List[CognitiveOperation] = []
    representation: List[Representation] = []


class StudentPreference(BaseModel):
    summary: Optional[str] = None
    strengths: List[StudentStrength] = []
    weaknesses: List[StudentWeakness] = []
    learning_style: Optional[LearningStyle] = None
    preferred_difficulty: Optional[DifficultyLevel] = None
    other_preferences: Dict[str, Any] = Field(default_factory=dict)


class StudentProfile(BaseModel):
    user_id: str = Field(..., alias="_id")
    full_name: Optional[str] = None
    grade: Optional[str | int] = None

    preferences: StudentPreference = Field(default_factory=StudentPreference)

    knowledge_map: Dict[Subject, Dict[Topic, Dict[Concept, LearningDetail]]] = Field(default_factory=dict)

    metadata: Dict[str, Any] = Field(default_factory=lambda: {"total_sessions": 0})
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True


class SessionSummary(BaseModel):
    """To summarize chat session history, using this to update student profile"""

    summary: str
    strengths: List[StudentStrength]
    weaknesses: List[StudentWeakness]
    learning_style: Optional[LearningStyle] = None
    preferred_difficulty: Optional[DifficultyLevel] = None

    mastering_at: List[ConceptType] = []
    struggling_at: List[ConceptType] = []

    finished_exercise: Dict[ProblemRole, Performance] = {}

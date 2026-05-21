from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone

from domain.models.curriculum import Subject, Topic, Concept
from domain.models.standard import (
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
from domain.models.exercise import Pattern

class StudentPattern(BaseModel):
    cognitive_operation: List[CognitiveOperation] = []
    representation: List[Representation] = []

class Perfermance(BaseModel):
    score: float
    bloom_level: BloomLevel
    strengths: List[ApproachStrength]
    weaknesses: List[ApproachWeakness]
    pattern: StudentPattern 
    # Pattern mà học sinh đã áp dụng trong bài tập, nó khác với pattern của bài tập

class LearningDetail(BaseModel):
    avg_score: float
    last_practiced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    mastering_at: List[ConceptType] = []
    struggling_at: List[ConceptType] = []

    finished_exercise: Dict[ProblemRole, Perfermance] = {}

class LearningStyle(BaseModel):
    cognitive_operation: List[CognitiveOperation] = []
    representation: List[Representation] = []

class StudentPreference(BaseModel):
    summary: Optional[str] = None
    strengths: List[StudentStrength] = []  # Điểm mạnh của học sinh
    weaknesses: List[StudentWeakness] = []  # Điểm yếu của học sinh
    learning_style: Optional[LearningStyle] = None  # Phong cách học tập
    preferred_difficulty: Optional[DifficultyLevel] = None  # Mức độ khó ưa thích
    other_preferences: Dict[str, Any] = Field(default_factory=dict)  # Các sở thích khác (ví dụ: thời gian học, loại bài tập yêu thích, v.v.)

class StudentProfile(BaseModel):
    user_id: str = Field(..., alias="_id") 
    full_name: str
    grade: int

    preferences: StudentPreference = Field(default_factory=StudentPreference)

    knowledge_map: Dict[Subject, Dict[Topic, Dict[Concept, LearningDetail]]] = Field(default_factory=dict)

    metadata: Dict[str, Any] = Field(default_factory=lambda: {"total_sessions": 0})
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True


class SessionSummary(BaseModel):
    """To summarize chat session history, using this to update student profile"""

    # --- Student preferences ---
    summary: str
    strengths: List[StudentStrength]
    weaknesses: List[StudentWeakness]
    learning_style: Optional[LearningStyle] = None
    preferred_difficulty: Optional[DifficultyLevel] = None

    # --- Knowledge map ---
    mastering_at: List[ConceptType] = []
    struggling_at: List[ConceptType] = []

    finished_exercise: Dict[ProblemRole, Perfermance] = {}

    


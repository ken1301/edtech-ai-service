from typing import List, Dict, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from domain.models.overall_models.common import ConceptType
from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.lesson2_models.common import Phase, SubmissionData
from domain.models.lesson2_models.evaluate import AffectiveState
from domain.models.lesson2_models.exercise import Problem

class Lesson2Request(BaseModel):
    user_id: str
    session_id: str
    correlation_id: str

    subject: Subject
    topic: Topic
    concept: Concept

    user_msg: str
    is_submission: bool
    submission_data: SubmissionData


class CompressedHistoryMsgInput(BaseModel):
    """Input for the compress_history prompt: the older messages to fold into a summary,
    plus the running compression and lesson context to preserve continuity."""
    messages_to_compress: str = ""
    existing_compression: Optional[str] = None
    concept_name: Optional[str] = None
    current_problem_id: Optional[int] = None


class SummarizeSessionInput(BaseModel):
    """Input for the summarize_session prompt: the full conversation + per-problem outcomes
    used to produce a durable student-profile summary at session close."""
    messages: str = ""
    existing_compression: Optional[str] = None
    concept_name: Optional[str] = None
    problem_outcomes: str = ""
    misconceptions: str = ""
    current_progress: float = 0.0


class SubmissionRecord(BaseModel):
    submitted_value: str
    result_status: bool
    approach_verdict: str
    matched_approach_id: Optional[int]
    matched_weakness: Optional[str]
    farming_signal: tuple[bool, int]


class ApproachState(BaseModel):
    reasoning: str
    attempts_made: int
    last_solution_proximity: float
    process_state: Optional[str] = None
    outcome: Literal["active", "switched_voluntarily", "switched_after_limit", "correct", "incorrect", "abandoned"]


class PerProblemState(BaseModel):
    current_approach_id: Optional[int] = None
    approach_list: List[ApproachState] = Field(default_factory=list)
    approach_trial_count: int = 0
    submission_state: List[SubmissionRecord] = Field(default_factory=list)
    phase_history: List[Phase] = Field(default_factory=list)
    awarded_progress: float = 0.0  # progress already credited for this problem (caps per-problem gain)
    solved: bool = False


class EmotionalState(BaseModel):
    frustration: float
    engagement: float
    confidence: float
    # can add more dimensions like risk, stuck, etc.

class Misconception(BaseModel):
    misconception_type: ConceptType
    description: str
    fixed: bool = False

class SessionMetadata(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None

    subject: Optional[Subject] = None
    topic: Optional[Topic] = None
    concept: Optional[Concept] = None

    history_phase: List[Phase] = Field(default_factory=list)
    phase_cycle_count: int = 0

    problem_list: List[Problem] = Field(default_factory=list)
    current_problem_id: Optional[int] = None
    problem_state: Dict[int, PerProblemState] = Field(default_factory=dict)

    misconception_list: List[Misconception] = Field(default_factory=list)

    emotion_history: List[EmotionalState] = Field(default_factory=list)

    last_evaluate_summary: Optional[str] = None

    history_compression: Optional[str] = None

    created_at: Optional[datetime] = None
    turn_count: int = 0
    history_summary: Optional[str] = ""
    current_progress: float = 0.0
    is_active: bool = True
    closed_at: Optional[datetime] = None

    class Config:
        extra = "allow"

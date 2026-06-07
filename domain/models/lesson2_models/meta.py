from typing import List, Dict, Literal, Optional
from pydantic import BaseModel
from datetime import datetime

from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.lesson2_models.common import Phase
from domain.models.lesson2_models.evaluate import AffectiveState
from domain.models.lesson2_models.exercise import Problem, Approach
from domain.models.lesson2_models.evaluate import Misconception


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


class ProblemState(BaseModel):
    current_approach_id: Optional[int]
    approach_list: List[ApproachState]
    approach_trial_count: int
    submission_state: List[SubmissionRecord] = []


class EmotionalState(BaseModel):
    emotional_signal: dict
    distress_level: str
    disengagement_level: str


class SessionMetadata(BaseModel):
    session_id: Optional[str] = None
    student_id: Optional[str] = None

    subject: Optional[Subject] = None
    topic: Optional[Topic] = None
    concept: Optional[Concept] = None

    history_phase: List[Phase] = []
    phase_cycle_count: int = 0

    problem_list: List[Problem] = []
    current_problem_id: Optional[int] = None
    problem_state: Dict[int, ProblemState] = {}

    misconception_list: List[Misconception] = []

    emotion_history: List[EmotionalState] = []

    last_evaluate_summary: Optional[str] = None

    history_compression_summary: Optional[str] = None

    created_at: Optional[datetime] = None
    turn_count: int = 0
    safety_state: Literal["normal", "monitoring", "diverted"] = "normal"
    current_progress: float = 0.0
    is_active: bool = True
    closed_at: Optional[datetime] = None

    class Config:
        extra = "allow"

from datetime import datetime

from pydantic import BaseModel
from typing import Optional, Dict, Tuple, List, Literal

from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.ground import GroundOutput
from domain.models.lesson2_models.evaluate import EvaluateOutput
from domain.models.lesson2_models.decide import DecideOutput

from domain.models.response import TokenUsage
from domain.models.exercise import ExerciseForPurpose
from domain.models.standard import ProblemRole
from domain.models.message import Message
from domain.models.lesson2_models.evaluate import Phase, Misconception, EvaluateOutput

class SubmissionData(BaseModel):
    status: bool
    is_process_farm: Tuple[bool, int]

class Lesson2ChatRequest(BaseModel):
    """Request model for Lesson 2 operations."""
    msg: str
    is_submission: bool
    submission_data: Optional[SubmissionData] = None
    current_process: float

class Lesson2ChatResponse(BaseModel):
    """Response model for Lesson 2 operations."""
    pass

class Lesson2LayerUsage(BaseModel):
    output: ClassifyOutput | GroundOutput | EvaluateOutput | DecideOutput | str
    usage: TokenUsage

class ApproachHistoryEntry(BaseModel):
    approach_id: Optional[int]
    started_at_turn: int
    attempts_made: int
    outcome: Literal["active","switched_voluntarily","switched_after_limit","correct","incorrect","abandoned"]

class PerProblemState(BaseModel):
    problem_id: int
    problem_role: ProblemRole
    submitted_attempts: int                  # total submissions on this problem
    attempts_on_current_approach: int        # resets on approach switch
    approaches_tried: int                    # increments on approach switch
    current_approach_id: Optional[int]       # null if novel/unmatched
    approach_history: List[ApproachHistoryEntry]
    misconception_history: List[Misconception]
    phase_history: List[Phase]               # forward-only append; one entry per turn on this problem
    # last_submission: Optional[SubmissionRecord]
    progress_credit: float                   # 0..1 per-problem progress contribution
    advanced: bool                           # true when bot has moved past this problem
    intervention_state: Literal["none","warned","intervened","skipped_with_credit"]
    max_attempts_per_approach: int           # mirrored from Problem
    max_approached_per_problem: int          # mirrored from Problem


class SubmissionRecord(BaseModel):
    turn_index: int
    submitted_value: str
    result_status: bool                      # from NestJS submission_data.status
    approach_verdict: Literal["CORRECT","WEAK","INCORRECT"]
    matched_approach_id: Optional[int]
    matched_weakness: Optional[str]
    farming_signal: Tuple[bool, int]   

class SessionMetadata(BaseModel):
    # Identity
    session_id: str
    student_id: str
    concept_id: str
    lesson_id: Literal["lesson_2"]

    # Curriculum
    exercise: ExerciseForPurpose
    problem_sequence: List[int]              # ordered problem_ids for P1..P4
    current_problem_index: int               # 0..3 → P1..P4

    # Per-problem state — keyed by problem_id
    problem_state: Dict[int, PerProblemState]

    # Session-wide
    session_started_at: datetime
    last_turn_at: datetime
    raw_messages: List[Message]          # bounded; see compression
    compressed_summary: str                  # rolling summary; replaces dropped raw turns
    prior_evaluate_outputs: List[EvaluateOutput]   # last N (default N=5)
    safety_state: Literal["normal", "monitoring", "diverted"]
    farming_callout_count: int               # cumulative across session

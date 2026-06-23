from typing import Annotated, Any, List, Dict, Literal, Optional
from pydantic import BaseModel, Field, StringConstraints, model_validator
from datetime import datetime

from domain.models.overall_models.common import ConceptType
from domain.models.overall_models.curriculum import Subject, Topic, Concept
from domain.models.lesson2_models.common import Phase, SubmissionData
from domain.models.lesson2_models.evaluate import AffectiveState
from domain.models.lesson2_models.exercise import Problem, ROLE_ORDER


NonEmptyId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]

class Lesson2Request(BaseModel):
    user_id: NonEmptyId
    session_id: NonEmptyId
    correlation_id: NonEmptyId

    subject: Subject
    topic: Topic
    concept: Concept

    user_msg: Optional[str] = None 

    is_submission: bool = False
    submission_data: Optional[SubmissionData] = None

    @model_validator(mode="after")
    def validate_submission_data(self) -> "Lesson2Request":
        normalized_user_msg = self.user_msg.strip() if isinstance(self.user_msg, str) else None

        if self.is_submission:
            self.user_msg = normalized_user_msg or ""
        elif not normalized_user_msg:
            raise ValueError("user_msg is required when is_submission=False")
        else:
            self.user_msg = normalized_user_msg

        if self.is_submission and self.submission_data is None:
            raise ValueError("submission_data is required when is_submission=True")
        return self


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
    matched_approach_id: Optional[int] = Field(default=None, ge=0)
    matched_weakness: Optional[str]
    farming_signal: tuple[bool, int]

    @model_validator(mode="after")
    def validate_farming_signal(self) -> "SubmissionRecord":
        if self.farming_signal[1] < 0:
            raise ValueError("farming_signal count must be non-negative")
        return self


class ApproachState(BaseModel):
    reasoning: str
    attempts_made: int = Field(ge=0, le=20)
    last_solution_proximity: float = Field(ge=0.0, le=1.0)
    process_state: Optional[str] = None
    outcome: Literal["active", "switched_voluntarily", "switched_after_limit", "correct", "incorrect", "abandoned"]


class PerProblemState(BaseModel):
    current_approach_id: Optional[int] = Field(default=None, ge=0)
    approach_list: List[ApproachState] = Field(default_factory=list)
    approach_trial_count: int = Field(default=0, ge=0, le=20)
    submission_state: List[SubmissionRecord] = Field(default_factory=list)
    phase_history: List[Phase] = Field(default_factory=list)
    awarded_progress: float = Field(default=0.0, ge=0.0, le=100.0)  # progress already credited for this problem (caps per-problem gain)
    solved: bool = False

    @model_validator(mode="after")
    def validate_semantics(self) -> "PerProblemState":
        if self.current_approach_id is not None and self.current_approach_id >= len(self.approach_list):
            raise ValueError("current_approach_id must reference an approach in approach_list")

        if self.approach_trial_count < len(self.submission_state):
            raise ValueError("approach_trial_count cannot be less than the number of submissions")

        return self


class EmotionalState(BaseModel):
    frustration: float = Field(ge=0.0, le=1.0)
    engagement: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    # Coarse engagement/distress bands carried from Evaluate's AffectiveState so the
    # affect trajectory (not just the scalars) is preserved across the session.
    disengagement_level: Optional[str] = None
    distress_level: Optional[str] = None

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
    phase_cycle_count: int = Field(default=0, ge=0)

    problem_list: List[Problem] = Field(default_factory=list)
    current_problem_id: Optional[int] = Field(default=None, gt=0)
    problem_state: Dict[int, PerProblemState] = Field(default_factory=dict)

    misconception_list: List[Misconception] = Field(default_factory=list)

    emotion_history: List[EmotionalState] = Field(default_factory=list)

    last_evaluate_summary: Optional[str] = None

    history_compression: Optional[str] = None

    created_at: Optional[datetime] = None
    turn_count: int = Field(default=0, ge=0)
    history_summary: Optional[str] = ""
    current_progress: float = Field(default=0.0, ge=0.0, le=100.0)
    is_active: bool = True
    is_closing: bool = False
    expired_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    active_correlation_id: Optional[str] = None
    last_completed_correlation_id: Optional[str] = None
    last_response_content: Optional[str] = None
    last_response_usage: List[Any] = Field(default_factory=list)
    last_response_progress: Optional[float] = None

    @model_validator(mode="after")
    def validate_semantics(self) -> "SessionMetadata":
        problem_ids = {problem.problem_id for problem in self.problem_list}

        if self.problem_list:
            if len(self.problem_list) > len(ROLE_ORDER):
                raise ValueError("problem_list cannot contain more than four runtime lesson 2 problems")

            observed_role_order = [problem.recommended_problem_role for problem in self.problem_list]
            expected_prefix = list(ROLE_ORDER[: len(self.problem_list)])
            if observed_role_order != expected_prefix:
                raise ValueError(
                    "problem_list must preserve the runtime lesson 2 role order prefix: "
                    + " -> ".join(role.value for role in ROLE_ORDER)
                )

        if self.current_problem_id is not None and problem_ids and self.current_problem_id not in problem_ids:
            raise ValueError("current_problem_id must reference a problem in problem_list")

        invalid_problem_state_ids = [problem_id for problem_id in self.problem_state if problem_id not in problem_ids]
        if invalid_problem_state_ids:
            raise ValueError("problem_state keys must reference problems in problem_list")

        if self.closed_at is not None and self.is_active:
            raise ValueError("closed sessions cannot remain active")

        if self.last_response_progress is not None and not 0.0 <= self.last_response_progress <= 100.0:
            raise ValueError("last_response_progress must be between 0 and 100")

        return self

    class Config:
        extra = "allow"

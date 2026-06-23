from typing import Annotated, List, Optional

from pydantic import BaseModel, Field, StringConstraints, model_validator

from domain.models.overall_models.message import Message
from domain.models.overall_models.common import ConceptType, ProblemRole
from domain.models.lesson2_models.common import (
    Phase,
    DisengagementLevel,
    DistressLevel,
    ProcessState,
    Lesson2LayerUsage,
)
from domain.models.lesson2_models.ground import ApproachVerdict


SummaryText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class AffectiveState(BaseModel):
    """Perceived emotional/engagement state of the student this turn (0..1 scalars)."""
    frustration: float = Field(ge=0.0, le=1.0)
    engagement: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    disengagement_level: DisengagementLevel = DisengagementLevel.ENGAGED
    distress_level: DistressLevel = DistressLevel.NONE


class MisconceptionSignal(BaseModel):
    """A misconception the Evaluate layer perceives in the student's reasoning."""
    misconception_type: ConceptType
    description: SummaryText


class EvaluateInput(BaseModel):
    session_id: Optional[str] = None
    recent_messages: List[Message] = Field(default_factory=list, max_length=12)

    # Problem context (from session_metadata — source of truth)
    problem_question: str = Field(default="", max_length=4000)
    problem_role: Optional[ProblemRole] = None
    open_approach: bool = False

    # Catalog of valid approaches for this problem, indexed by position (id).
    # Summaries only — never approach_answer/final_answer (design rule #3) — so the
    # layer can map the student's reasoning onto a concrete approach id.
    available_approaches: List[str] = Field(default_factory=list, max_length=12)

    # Approach context carried across turns via metadata
    current_approach_id: Optional[int] = Field(default=None, ge=0)
    current_approach_reasoning: str = Field(default="", max_length=4000)
    attempts_made: int = Field(default=0, ge=0, le=20)
    max_attempts: int = Field(default=3, ge=1, le=20)

    # Submission context — verdict only, never the raw final answer (design rule #3)
    is_submission: bool = False
    ground_verdict: Optional[ApproachVerdict] = None
    matched_weakness: Optional[str] = Field(default=None, max_length=4000)

    # History
    phase_history: List[Phase] = Field(default_factory=list, max_length=50)
    last_evaluate_summary: Optional[str] = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_semantics(self) -> "EvaluateInput":
        # Allow attempts_made > max_attempts so the pipeline can gracefully handle exceeded limits.
        # if self.attempts_made > self.max_attempts:
        #     raise ValueError("attempts_made must be less than or equal to max_attempts")

        if self.current_approach_id is not None:
            if not self.available_approaches:
                raise ValueError("current_approach_id requires available_approaches")
            if self.current_approach_id >= len(self.available_approaches):
                raise ValueError("current_approach_id must reference an available approach")

        if self.is_submission and self.ground_verdict is None:
            raise ValueError("ground_verdict is required when is_submission=True")

        if not self.is_submission and self.ground_verdict is not None:
            raise ValueError("ground_verdict is only valid for submission turns")

        return self


class EvaluateOutput(BaseModel):
    """Perception only — the Evaluate layer observes, it does not decide."""
    # Phase
    phase: Phase
    phase_confidence: float = Field(ge=0.0, le=1.0)

    # Approach / learning signals
    current_approach_id: Optional[int] = Field(default=None, ge=0)
    process_state: ProcessState = ProcessState.DISCOVERING
    solution_proximity: float = Field(default=0.0, ge=0.0, le=1.0) # khoảng cách từ solution hiện tại đến solution đúng, 0.0 (xa) .. 1.0 (gần)
    stuck: bool = False

    # True when the student appears to be abandoning their prior approach for a new one
    # this turn (lets Decide raise APPROACH_SWITCH_WARNING before attempts are wasted).
    approach_switched: bool = False

    # Compressed running reasoning for the active approach (written back to metadata)
    student_reasoning_compressed: str = Field(default="", max_length=4000)

    # Misconceptions perceived this turn
    misconceptions: List[MisconceptionSignal] = Field(default_factory=list, max_length=10)

    # Affect
    affect: AffectiveState

    summary: str = Field(default="", max_length=4000)

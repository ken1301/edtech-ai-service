from typing import List, Optional
from pydantic import BaseModel, Field

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


class AffectiveState(BaseModel):
    """Perceived emotional/engagement state of the student this turn (0..1 scalars)."""
    frustration: float
    engagement: float
    confidence: float
    disengagement_level: DisengagementLevel = DisengagementLevel.ENGAGED
    distress_level: DistressLevel = DistressLevel.NONE


class MisconceptionSignal(BaseModel):
    """A misconception the Evaluate layer perceives in the student's reasoning."""
    misconception_type: ConceptType
    description: str


class EvaluateInput(BaseModel):
    session_id: Optional[str] = None
    recent_messages: List[Message] = Field(default_factory=list)

    # Problem context (from session_metadata — source of truth)
    problem_question: str = ""
    problem_role: Optional[ProblemRole] = None
    open_approach: bool = False

    # Approach context carried across turns via metadata
    current_approach_id: Optional[int] = None
    current_approach_reasoning: str = ""
    attempts_made: int = 0

    # Submission context — verdict only, never the raw final answer (design rule #3)
    is_submission: bool = False
    ground_verdict: Optional[ApproachVerdict] = None
    matched_weakness: Optional[str] = None

    # History
    phase_history: List[Phase] = Field(default_factory=list)
    last_evaluate_summary: Optional[str] = None


class EvaluateOutput(BaseModel):
    """Perception only — the Evaluate layer observes, it does not decide."""
    # Phase
    phase: Phase
    phase_confidence: float

    # Approach / learning signals
    current_approach_id: Optional[int] = None
    process_state: ProcessState = ProcessState.DISCOVERING
    solution_proximity: float = 0.0
    stuck: bool = False

    # Compressed running reasoning for the active approach (written back to metadata)
    student_reasoning_compressed: str = ""

    # Misconceptions perceived this turn
    misconceptions: List[MisconceptionSignal] = Field(default_factory=list)

    # Affect
    affect: AffectiveState

    summary: str = ""

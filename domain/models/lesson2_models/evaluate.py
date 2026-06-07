from typing import List, Optional
from pydantic import BaseModel, Field

from domain.models.overall_models.message import Message
from domain.models.overall_models.common import ConceptType, ProblemRole
from domain.models.lesson2_models.common import Phase, DisengagementLevel, DistressLevel, ProcessState
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.ground import GroundOutput
from domain.models.lesson2_models.exercise import Problem, Approach


class Misconception(BaseModel):
    tag: Optional[str] = None
    description: str
    matches_known_weakness: Optional[str] = None
    concept_type: Optional[ConceptType] = None
    fixed: bool = False


class AffectiveState(BaseModel):
    frustration: float
    engagement: float
    confidence: float


class StuckSignal(BaseModel):
    stuck: bool
    attempts_on_same_error: int
    intervention_recommended: bool


class RiskSignal(BaseModel):
    gaming_likelihood: float
    disengagement: DisengagementLevel
    distress_level: DistressLevel
    answer_extraction_attempt: bool


class ApproachMatch(BaseModel):
    approach_id: Optional[int] = None
    similarity: float
    novel: bool = False
    description: Optional[str] = None


class ProblemSnapshot(BaseModel):
    problem_id: int
    question: str
    attachment_url: Optional[str] = None
    approach_list: List[Approach] = Field(default_factory=list)
    open_approach: bool = False
    recommended_problem_role: ProblemRole


class ApproachHistoryEntry(BaseModel):
    approach_id: Optional[int] = None
    started_at_turn: Optional[int] = None
    attempts_made: int = 0
    outcome: str = "active"


class PriorEvaluateOutput(BaseModel):
    phase: Phase
    progress_state: ProcessState
    mastery_demonstrated: bool
    summary: str


class EvaluateInput(BaseModel):
    current_problem: ProblemSnapshot
    problem_role: ProblemRole
    classify_output: ClassifyOutput
    ground_output: Optional[GroundOutput] = None
    is_submission: bool = False

    phase_history: List[Phase] = Field(default_factory=list)
    approach_history: List[ApproachHistoryEntry] = Field(default_factory=list)
    misconception_history: List[Misconception] = Field(default_factory=list)
    recent_messages: List[Message] = Field(default_factory=list)
    compressed_session_summary: str = ""
    attempts_on_current_approach: int = 0
    max_attempts_per_approach: int = 0
    approaches_tried: int = 0
    max_approached_per_problem: int = 0
    prior_evaluate_outputs: List[PriorEvaluateOutput] = Field(default_factory=list)


class EvaluateOutput(BaseModel):
    phase: Phase
    phase_confidence: float
    phase_skip_detected: bool = False
    skipped_phases: List[Phase] = Field(default_factory=list)

    affective: AffectiveState
    current_approach: ApproachMatch
    misconception: Optional[Misconception] = None
    problem_state: ProblemSnapshot
    mastery_demonstrated: bool
    stuck: StuckSignal
    risk: RiskSignal
    novel_valid_approach: bool = False

    progress_state: ProcessState

    @property
    def current_phase(self) -> Phase:
        return self.phase

    @property
    def affective_state(self) -> AffectiveState:
        return self.affective

    @property
    def approach_state(self) -> ApproachMatch:
        return self.current_approach

    @property
    def stuck_signal(self) -> StuckSignal:
        return self.stuck

    @property
    def risk_signal(self) -> RiskSignal:
        return self.risk

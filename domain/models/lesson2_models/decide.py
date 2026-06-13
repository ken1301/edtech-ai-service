from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from domain.models.overall_models.common import ProblemRole
from domain.models.lesson2_models.common import Phase, ResponseClass, Lesson2LayerUsage
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.evaluate import EvaluateOutput
from domain.models.lesson2_models.ground import GroundOutput


class DecideInput(BaseModel):
    session_id: Optional[str] = None

    # Upstream layer outputs
    classify_output: Optional[ClassifyOutput] = None
    ground_output: Optional[GroundOutput] = None
    evaluate_output: EvaluateOutput

    # Flow context (from session_metadata — source of truth)
    is_submission: bool = False
    result_status: Optional[bool] = None  # correctness from NestJS (submission only)
    phase: Phase
    problem_role: Optional[ProblemRole] = None
    problem_index: int = 0
    total_problems: int = 4
    attempts_made: int = 0
    max_attempts: int = 3
    current_progress: float = 0.0
    abuse_flags: List[str] = Field(default_factory=list)


class ToneArbiterOutput(BaseModel):
    tone: Literal["peer", "peer_soft", "empathetic", "firm"]
    depth: Literal["one_line", "short", "medium"]
    must_not_reveal: List[str] = Field(default_factory=list)


class ResponseDirective(BaseModel):
    response_class: ResponseClass
    tone_arbiter: ToneArbiterOutput
    advance: bool = False
    intervene: bool = False
    rationale: str = ""


class DecideOutput(BaseModel):
    directive: ResponseDirective

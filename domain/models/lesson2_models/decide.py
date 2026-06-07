from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from domain.models.overall_models.common import ProblemRole
from domain.models.lesson2_models.common import Phase, ResponseClass
from domain.models.lesson2_models.evaluate import AffectiveState


class ToneArbiterOutput(BaseModel):
    tone: Literal["peer", "peer_soft", "empathetic", "firm"]
    depth: Literal["one_line", "short", "medium"]
    must_not_reveal: List[str] = Field(default_factory=list)


DecideOutput = ToneArbiterOutput


class DecideInput(BaseModel):
    response_class: ResponseClass
    phase: Phase
    problem_role: ProblemRole
    affective: AffectiveState
    attempts_on_current_approach: int
    max_attempts_per_approach: int
    approaches_tried: int
    max_approached_per_problem: int
    critical_false_positive: bool = False


ToneDecideInput = DecideInput


class ResponseDirective(BaseModel):
    response_class: ResponseClass
    tone: Literal["peer", "peer_soft", "empathetic", "firm"]
    depth: Literal["one_line", "short", "medium"]
    must_not_reveal: List[str] = Field(default_factory=list)
    advance: bool = False
    advance_after_ack: bool = False
    critical_false_positive: bool = False
    offer_skip: bool = False
    references_problem_id: Optional[int] = None
    target_phase_to_probe: Optional[Phase] = None
    farming_callout: bool = False

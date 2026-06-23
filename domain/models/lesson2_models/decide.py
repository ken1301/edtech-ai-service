from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator

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
    problem_index: int = Field(default=0, ge=0, le=7)
    total_problems: int = Field(default=4, ge=1, le=8)
    attempts_made: int = Field(default=0, ge=0, le=20)
    max_attempts: int = Field(default=3, ge=1, le=20)
    current_progress: float = Field(default=0.0, ge=0.0, le=100.0)
    abuse_flags: List[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_semantics(self) -> "DecideInput":
        if self.problem_index >= self.total_problems:
            raise ValueError("problem_index must be less than total_problems")

        # Allow attempts_made > max_attempts so the pipeline can gracefully handle exceeded limits.
        # if self.attempts_made > self.max_attempts:
        #     raise ValueError("attempts_made must be less than or equal to max_attempts")

        if self.is_submission and self.result_status is None:
            raise ValueError("result_status is required when is_submission=True")

        if not self.is_submission and self.result_status is not None:
            raise ValueError("result_status is only valid for submission turns")

        return self


class ToneArbiterOutput(BaseModel):
    tone: Literal["peer", "peer_soft", "empathetic", "firm"]
    depth: Literal["one_line", "short", "medium"]
    must_not_reveal: List[str] = Field(default_factory=list, max_length=12)


class ResponseDirective(BaseModel):
    response_class: ResponseClass
    tone_arbiter: ToneArbiterOutput
    advance: bool = False
    intervene: bool = False
    rationale: str = Field(default="", max_length=4000)


class DecideOutput(BaseModel):
    directive: ResponseDirective

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

from domain.models.overall_models.message import Message
from domain.models.overall_models.common import ProblemRole
from domain.models.lesson2_models.common import Phase, ProcessState, Lesson2LayerUsage
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.evaluate import AffectiveState
from domain.models.lesson2_models.ground import ApproachVerdict
from domain.models.lesson2_models.decide import ResponseDirective


class ResponseInput(BaseModel):
    response_directive: ResponseDirective

    subject: str = Field(default="")
    topic: str = Field(default="")
    concept: str = Field(default="")

    # Problem context (never includes the raw final_answer — design rule #3)
    phase: Optional[Phase] = None
    problem_question: str = Field(default="", max_length=4000)
    problem_role: Optional[ProblemRole] = None
    problem_index: int = Field(default=0, ge=0, le=7)
    total_problems: int = Field(default=4, ge=1, le=8)
    current_progress: float = Field(default=0.0, ge=0.0, le=100.0)

    # Perception carried from Evaluate
    evaluate_summary: str = Field(default="", max_length=4000)
    affect: Optional[AffectiveState] = None
    student_reasoning: str = Field(default="", max_length=4000)
    process_state: Optional[ProcessState] = None
    solution_proximity: float = Field(default=0.0, ge=0.0, le=1.0)
    stuck: bool = False

    # Attempt context — lets the peer calibrate persistence vs. stepping back
    attempts_made: int = Field(default=0, ge=0, le=20)
    max_attempts: int = Field(default=3, ge=1, le=20)

    # Submission context — verdict only
    is_submission: bool = False
    ground_verdict: Optional[ApproachVerdict] = None
    matched_weakness: Optional[str] = None

    # Conversation
    classify: Optional[ClassifyOutput] = None
    recent_messages: List[Message] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_semantics(self) -> "ResponseInput":
        if self.problem_index >= self.total_problems:
            raise ValueError("problem_index must be less than total_problems")

        if self.attempts_made > self.max_attempts:
            raise ValueError("attempts_made must be less than or equal to max_attempts")

        if self.is_submission and self.ground_verdict is None:
            raise ValueError("ground_verdict is required when is_submission=True")

        if not self.is_submission and (self.ground_verdict is not None or self.matched_weakness is not None):
            raise ValueError("submission-only grounding fields are invalid for non-submission turns")

        return self


__all__ = ["ResponseInput", "Lesson2LayerUsage"]

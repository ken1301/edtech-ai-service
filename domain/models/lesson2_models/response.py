from typing import List, Optional
from pydantic import BaseModel, Field

from domain.models.overall_models.message import Message
from domain.models.overall_models.common import ProblemRole
from domain.models.lesson2_models.common import Phase, ProcessState, Lesson2LayerUsage
from domain.models.lesson2_models.classify import ClassifyOutput
from domain.models.lesson2_models.evaluate import AffectiveState
from domain.models.lesson2_models.ground import ApproachVerdict
from domain.models.lesson2_models.decide import ResponseDirective


class ResponseInput(BaseModel):
    response_directive: ResponseDirective

    # Problem context (never includes the raw final_answer — design rule #3)
    phase: Optional[Phase] = None
    problem_question: str = ""
    problem_role: Optional[ProblemRole] = None
    problem_index: int = 0
    total_problems: int = 4
    current_progress: float = 0.0

    # Perception carried from Evaluate
    evaluate_summary: str = ""
    affect: Optional[AffectiveState] = None
    student_reasoning: str = ""
    process_state: Optional[ProcessState] = None
    solution_proximity: float = 0.0
    stuck: bool = False

    # Attempt context — lets the peer calibrate persistence vs. stepping back
    attempts_made: int = 0
    max_attempts: int = 3

    # Submission context — verdict only
    is_submission: bool = False
    ground_verdict: Optional[ApproachVerdict] = None
    matched_weakness: Optional[str] = None

    # Conversation
    classify: Optional[ClassifyOutput] = None
    recent_messages: List[Message] = Field(default_factory=list)


__all__ = ["ResponseInput", "Lesson2LayerUsage"]

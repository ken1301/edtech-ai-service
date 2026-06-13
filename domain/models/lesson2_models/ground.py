from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

from domain.models.lesson2_models.exercise import Approach
from domain.models.lesson2_models.common import Lesson2LayerUsage  # noqa: F401  (re-export)


class ApproachVerdict(str, Enum):
    CORRECT = "CORRECT"
    WEAK = "WEAK"
    INCORRECT = "INCORRECT"
    NOT_AN_ANSWER = "NOT_AN_ANSWER"


class GroundInput(BaseModel):
    problem_question: str
    problem_final_answer: str
    open_approach: bool
    approach_list: List[Approach]
    student_reasoning: str
    student_submitted_answer: str
    result_status: bool

class GroundOutput(BaseModel):
    approach_verdict: ApproachVerdict

    matched_approach_id: Optional[int] = None
    matched_weakness: Optional[str] = None
    judge_confidence: float
    explanation: str
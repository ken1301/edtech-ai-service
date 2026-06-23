from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from domain.models.lesson2_models.exercise import Approach
from domain.models.lesson2_models.common import Lesson2LayerUsage  # noqa: F401  (re-export)


class ApproachVerdict(str, Enum):
    CORRECT = "CORRECT"
    WEAK = "WEAK"
    INCORRECT = "INCORRECT"
    NOT_AN_ANSWER = "NOT_AN_ANSWER"


class GroundInput(BaseModel):
    problem_question: str = Field(min_length=1, max_length=4000)
    problem_final_answer: str = Field(min_length=1, max_length=4000)
    open_approach: bool
    approach_list: List[Approach] = Field(min_length=1, max_length=12)
    student_reasoning: str = Field(default="", max_length=4000)
    student_submitted_answer: str = Field(default="", max_length=4000)

class GroundOutput(BaseModel):
    result_verdict: bool = Field(description="True if the student reached the correct final result or logical conclusion, false otherwise")
    approach_verdict: ApproachVerdict

    matched_approach_id: Optional[int] = Field(default=None, ge=0)
    matched_weakness: Optional[str] = Field(default=None, max_length=4000)
    judge_confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1, max_length=4000)